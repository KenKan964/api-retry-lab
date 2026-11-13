"""Independent post-run oracle: direct DB and raw HTTP/log evidence, no diagnosis imports."""
import json,sqlite3

def audit(directory, result, expected_count):
 c=sqlite3.connect((directory/'state.sqlite').resolve().as_uri()+'?mode=ro',uri=True)
 rows=c.execute('SELECT op,amount FROM effects').fetchall();c.close()
 server=[json.loads(x) for x in (directory/'server.jsonl').read_text().splitlines()] if (directory/'server.jsonl').exists() else []
 commits=sum(e['event']=='committed' and not e['replayed'] for e in server)
 checks={'db_count':len(rows)==expected_count,'report_matches_db':result['effect_count']==len(rows),
 'commit_log_matches_db':commits==len(rows),'server_sequence':all(e['seq']==i for i,e in enumerate(server)),
 'client_sequence':all(e['seq']==i for i,e in enumerate(result['trace'])),
 'stderr_empty':all(not p.read_text() for p in directory.glob('stderr-*.log'))}
 return {'passed':all(checks.values()),'checks':checks,'count':len(rows)}
