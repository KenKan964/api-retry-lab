"""Independent stdlib reference. No ARL server, client, fixture or oracle imports."""
from __future__ import annotations
import argparse
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import queue
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import unittest


def serve(directory):
    directory = Path(directory)
    if (directory / 'owner.token').read_text() != os.environ.get('OSS_OWNER_TOKEN'):
        raise ValueError('not an owned fixture')
    path = directory / 'reference.sqlite'
    c = sqlite3.connect(path)
    c.executescript('CREATE TABLE receipts(key TEXT PRIMARY KEY, body TEXT);'
                    'CREATE TABLE applied(id TEXT, value INTEGER);')
    c.close()
    seq = 0
    mutex = threading.Lock()

    def record(kind, **fields):
        nonlocal seq
        with mutex:
            item = dict(seq=seq, event=kind, monotonic_ns=time.monotonic_ns(), **fields)
            with (directory / 'server.jsonl').open('a', encoding='utf-8') as f:
                f.write(json.dumps(item) + '\n')
            seq += 1

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, code, body):
            encoded = json.dumps(body).encode()
            self.send_response(code)
            self.send_header('Content-Length', str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
            record('response', status=code)

        def do_POST(self):
            if self.path != '/operations':
                return self.reply(404, {})
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            key = self.headers['Idempotency-Key']
            record('received', key=key, payload=payload)
            c = sqlite3.connect(path, timeout=5)
            try:
                c.execute('BEGIN IMMEDIATE')
                body = json.dumps(payload, sort_keys=True)
                prior = c.execute('SELECT body FROM receipts WHERE key=?', (key,)).fetchone()
                if prior and prior[0] != body:
                    c.rollback()
                    record('conflict', key=key)
                    return self.reply(409, {'conflict': True})
                replay = bool(prior) and self.headers.get('X-Defect') != 'duplicate'
                if not replay:
                    c.execute('INSERT INTO applied VALUES(?,?)',
                              (payload['operation_id'], payload['amount']))
                    c.execute('INSERT OR IGNORE INTO receipts VALUES(?,?)', (key, body))
                c.commit()
                record('commit', applied=not replay, key=key)
            finally:
                c.close()
            if self.headers.get('X-Drop') == 'after_commit':
                record('drop_after_commit')
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            self.reply(200, {'completed': True, 'replayed': replay})

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    print(json.dumps({'port': server.server_port}), flush=True)
    server.serve_forever()


def run_case(recipe, directory):
    """Owned process, real HTTP, direct persisted effect oracle, unittest checks."""
    directory = Path(directory)
    directory.mkdir()
    token = os.urandom(24).hex()
    (directory / 'owner.token').write_text(token)
    observations = []
    process = None
    error_file = (directory / 'stderr.log').open('w')
    started = time.perf_counter_ns()
    try:
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), '_server', str(directory)],
            stdout=subprocess.PIPE, stderr=error_file, text=True,
            env={**os.environ, 'OSS_OWNER_TOKEN': token})
        ready = queue.Queue()
        reader = threading.Thread(target=lambda: ready.put(process.stdout.readline()), daemon=True)
        reader.start()
        port = json.loads(ready.get(timeout=5))['port']
        for index, request in enumerate(recipe['requests']):
            connection = http.client.HTTPConnection('127.0.0.1', port, timeout=2)
            payload = {'operation_id': 'op-001', 'amount': request['amount']}
            headers = {'Idempotency-Key': 'key-001', 'Content-Type': 'application/json'}
            if request.get('drop'): headers['X-Drop'] = 'after_commit'
            if request.get('duplicate'): headers['X-Defect'] = 'duplicate'
            try:
                connection.request('POST', '/operations', json.dumps(payload), headers)
                response = connection.getresponse()
                item = {'status': response.status, 'body': json.loads(response.read())}
            except (OSError, http.client.HTTPException) as error:
                item = {'status': None, 'observation': 'UNKNOWN', 'error': type(error).__name__}
            finally:
                connection.close()
            observations.append(dict(attempt=index + 1, **item))
        connection = sqlite3.connect((directory / 'reference.sqlite').resolve().as_uri() + '?mode=ro', uri=True)
        effects = connection.execute('SELECT id,value FROM applied').fetchall()
        receipts = connection.execute('SELECT key,body FROM receipts').fetchall()
        connection.close()
        events = [json.loads(x) for x in (directory / 'server.jsonl').read_text().splitlines()]
        # Independent classification from observations and persisted facts.
        findings = []
        if len(effects) > 1: findings.append('DUPLICATE_EFFECT_DETECTED')
        if any(x['status'] == 409 for x in observations): findings.append('PAYLOAD_CONFLICT_DETECTED')
        if observations[-1]['status'] is None: findings.append('HOLD_UNKNOWN')
        check = unittest.TestCase()
        check.assertEqual(len(effects), recipe['effects'])
        check.assertEqual([x['status'] for x in observations], recipe['statuses'])
        check.assertEqual(sum(e['event']=='commit' and e['applied'] for e in events), len(effects))
        check.assertEqual(len(receipts), recipe['receipts'])
        check.assertEqual(findings, recipe['findings'])
        check.assertEqual(sum(x.get('body', {}).get('replayed', False) for x in observations), recipe['replays'])
        check.assertEqual([e['seq'] for e in events], list(range(len(events))))
        result = {'passed': True, 'effects': len(effects), 'receipts': len(receipts),
                  'http': observations, 'findings': findings, 'server_events': events,
                  'oracle_observer': 'reference_harness_sqlite', 'oracle_time': 'after_http_requests'}
    finally:
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try: process.wait(5)
                except subprocess.TimeoutExpired: process.kill(); process.wait(5)
            process.stdout.close()
        error_file.close()
    unittest.TestCase().assertEqual((directory / 'stderr.log').read_text(), '')
    result['runtime_ms'] = (time.perf_counter_ns() - started) / 1e6
    result['child_reaped'] = process.returncode is not None
    (directory / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '_server':
        serve(sys.argv[2]); return 0
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--recipes', type=Path, default=Path(__file__).with_name('cases.json'))
    args = parser.parse_args()
    recipes = json.loads(args.recipes.read_text())
    result = run_case(recipes[args.case], args.out)
    print(json.dumps({'passed': result['passed'], 'effects': result['effects']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
