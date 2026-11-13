"""Local-only HTTP retry laboratory. Python standard library."""
import argparse,concurrent.futures,hashlib,http.client,json,os,platform,re,socket,sqlite3,subprocess,sys,threading,time
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path

def db(path):
 c=sqlite3.connect(path,timeout=5);c.execute('CREATE TABLE IF NOT EXISTS keys(k TEXT PRIMARY KEY,p TEXT)');c.execute('CREATE TABLE IF NOT EXISTS effects(op TEXT,amount INTEGER)');c.commit();return c

def retry_after_seconds(value, cap=1):
 if not isinstance(value,str) or not re.fullmatch(r'[0-9]+',value):return None
 if len(value)>10:return None
 seconds=int(value)
 return seconds if seconds<=cap else None

def server(directory):
 if (Path(directory)/'owner.token').read_text()!=os.environ.get('ARL_CHILD_TOKEN'):raise ValueError('not owned')
 path=Path(directory)/'state.sqlite';db(path).close();lock=threading.Lock();seq=len((Path(directory)/'server.jsonl').read_text().splitlines()) if (Path(directory)/'server.jsonl').exists() else 0
 def log(event,**kw):
  nonlocal seq
  with lock:
   with (Path(directory)/'server.jsonl').open('a') as f:f.write(json.dumps(dict(seq=seq,event=event,monotonic_ns=time.monotonic_ns(),**kw))+'\n')
   seq+=1
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*a):pass
  def reply(self,status,data):
   raw=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Length',str(len(raw)))
   if status==429:self.send_header('Retry-After',self.headers.get('X-Retry-After','0'))
   self.end_headers()
   try:self.wfile.write(raw);log('response_sent',status=status)
   except OSError as e:log('response_write_error',error=type(e).__name__)
  def do_GET(self):
   if self.path=='/health':return self.reply(200,{'ready':True})
   if self.headers.get('X-No-Read')=='yes':return self.reply(503,{'unknown':True})
   c=db(path);rows=c.execute('SELECT op,amount FROM effects WHERE op=?',(self.path.rsplit('/',1)[-1],)).fetchall();c.close();log('readback',observer='client',count=len(rows));self.reply(200,{'count':len(rows)})
  def do_POST(self):
   if self.path!='/operations':return self.reply(404,{})
   try:
    p=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))));k=self.headers.get('Idempotency-Key','')
    if not re.fullmatch('[A-Za-z0-9_-]{1,64}',k) or set(p)!={'operation_id','amount'} or p['operation_id']!='op-001' or type(p['amount'])!=int:raise ValueError()
   except (ValueError,TypeError):return self.reply(400,{'invalid':True})
   fault=self.headers.get('X-Fault','none');mutant=self.headers.get('X-Mutant','none');log('received',key=k,payload=p,fault=fault)
   if fault=='before_apply':self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();log('dropped_before_apply');return
   if fault in ('503_before','429'):return self.reply(503 if fault=='503_before' else 429,{})
   if mutant=='false':return self.reply(200,{'completed':True})
   c=db(path);c.execute('BEGIN IMMEDIATE');canonical=json.dumps(p,sort_keys=True);old=c.execute('SELECT p FROM keys WHERE k=?',(k,)).fetchone()
   if old and old[0]!=canonical and mutant!='conflict':c.rollback();c.close();log('conflict');return self.reply(409,{'conflict':True})
   replay=bool(old) and mutant not in ('duplicate','conflict')
   if not replay:
    c.execute('INSERT INTO effects VALUES(?,?)',(p['operation_id'],p['amount']));c.execute('INSERT OR IGNORE INTO keys VALUES(?,?)',(k,canonical))
   c.commit();c.close();log('committed',key=k,replayed=replay)
   if fault=='after_apply_before_response':log('dropped_after_apply');self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
   if fault=='delay':log('delay_after_apply',seconds=.2);time.sleep(.2)
   if fault=='503_after':return self.reply(503,{})
   self.reply(200,{'completed':True,'replayed':replay})
 fault=os.environ.get('ARL_TEST_FAULT','')
 if fault=='check_timeout':time.sleep(30)
 blocker=None
 if fault=='port_init':
  blocker=socket.socket();blocker.bind(('127.0.0.1',0));blocker.listen();port=blocker.getsockname()[1]
 else:port=0
 srv=ThreadingHTTPServer(('127.0.0.1',port),Handler);print(json.dumps({'port':srv.server_port}),flush=True)
 if fault=='child_crash':os._exit(17)
 srv.serve_forever()

# Independent expectations: effect count and actual HTTP observations, not diagnosis text.
CASES={
 'normal':(1,[]),'sequential':(1,[]),'parallel':(1,[]),'payload_conflict':(1,['PAYLOAD_CONFLICT_DETECTED']),
 'missing_key':(0,[]),'empty_key':(0,[]),'before_send':(0,['HOLD_UNKNOWN']), 'before_apply':(0,['HOLD_UNKNOWN']),
 'response_lost_after_commit':(1,['HOLD_UNKNOWN']), 'safe_replay':(1,['SAFE_REPLAY']),
 'unsafe_retry':(2,['DUPLICATE_EFFECT_DETECTED','UNSAFE_RETRY_DETECTED']), 'timeout':(1,['HOLD_UNKNOWN']),
 '503_before':(1,[]),'503_after':(1,['HOLD_UNKNOWN']),'429_valid':(1,[]),'429_invalid':(0,['HOLD_UNKNOWN']),
 'connection_refused':(0,['HOLD_UNKNOWN']),'restart_replay':(1,['SAFE_REPLAY']), 'restart_conflict':(1,['PAYLOAD_CONFLICT_DETECTED']),
 'duplicate_mutant':(2,['DUPLICATE_EFFECT_DETECTED']), 'false_mutant':(0,['FALSE_COMPLETION_DETECTED']),
 'readback_unavailable':(1,['HOLD_UNKNOWN']), 'payload_mutant':(2,['DUPLICATE_EFFECT_DETECTED'])}

def exercise(name,directory,*,retry_after=None,test_fault=None,check_timeout=5):
 directory.mkdir();token=os.urandom(24).hex();(directory/'owner.token').write_text(token);events=[];procs=[];stderr_files=[];event_lock=threading.Lock()
 def event(kind,**kw):
  with event_lock:events.append(dict(seq=len(events),event=kind,monotonic_ns=time.monotonic_ns(),**kw))
 def start():
  err=(directory/f'stderr-{len(procs)}.log').open('w');stderr_files.append(err)
  executable=str(directory/'missing-test-python') if test_fault=='spawn' else sys.executable
  p=subprocess.Popen([executable,str(Path(__file__).resolve()),'_server',str(directory)],stdout=subprocess.PIPE,stderr=err,text=True,env={**os.environ,'ARL_CHILD_TOKEN':token,'ARL_TEST_FAULT':test_fault or ''});procs.append(p);event('child_spawned',pid=p.pid)
  # Bounded readiness via reader thread, never arbitrary PID termination.
  import queue
  q=queue.Queue();threading.Thread(target=lambda:q.put(p.stdout.readline()),daemon=True).start()
  line=q.get(timeout=check_timeout);event('startup_response',line=line)
  port=json.loads(line)['port'];event('server_started',pid=p.pid,port=port);return p,port
 def send(port,key='key-001',amount=7,fault='none',mutant='none',get=False,ra='0'):
  c=http.client.HTTPConnection('127.0.0.1',port,timeout=.08 if fault=='delay' else 2)
  headers={'Content-Type':'application/json','X-Fault':fault,'X-Mutant':mutant,'X-Retry-After':ra}
  if key is not None:headers['Idempotency-Key']=key
  if get=='blocked':headers['X-No-Read']='yes'
  try:
   c.request('GET' if get else 'POST','/operations/op-001' if get else '/operations',None if get else json.dumps({'operation_id':'op-001','amount':amount}),headers)
   r=c.getresponse();data=json.loads(r.read());v={'status':r.status,'data':data,'retry_after':r.getheader('Retry-After')}
  except (OSError,http.client.HTTPException) as e:v={'status':None,'observation':'UNKNOWN','error':type(e).__name__}
  finally:c.close()
  event('http_observation',key=key,**v);return v
 try:
  p,port=start();responses=[]
  if test_fault=='child_crash':p.wait(5);raise RuntimeError('child exited abnormally')
  if name=='before_send':event('before_send_failure')
  elif name=='connection_refused':
   p.terminate();p.wait(5);responses.append(send(port))
  elif name=='parallel':
   gate=threading.Barrier(4)
   def job(_):gate.wait();return send(port)
   with concurrent.futures.ThreadPoolExecutor(4) as pool:responses=list(pool.map(job,range(4)))
  elif name in ('missing_key','empty_key'):responses=[send(port,key=None if name=='missing_key' else '')]
  else:
   fault={'before_apply':'before_apply','response_lost_after_commit':'after_apply_before_response','safe_replay':'after_apply_before_response','unsafe_retry':'after_apply_before_response','timeout':'delay','503_before':'503_before','503_after':'503_after','429_valid':'429','429_invalid':'429','readback_unavailable':'after_apply_before_response'}.get(name,'none')
   mutant={'duplicate_mutant':'duplicate','false_mutant':'false','payload_mutant':'conflict'}.get(name,'none')
   responses.append(send(port,fault=fault,mutant=mutant,ra=retry_after if retry_after is not None else ('999999' if name=='429_invalid' else '0')))
   if name=='safe_replay':responses.append(send(port,get=True))
   if name.startswith('restart_'):p.terminate();p.wait(5);p,port=start()
   retry_allowed=True
   if name in ('429_valid','429_invalid'):
    seconds=retry_after_seconds(responses[-1]['retry_after'])
    retry_allowed=seconds is not None
    t=time.monotonic()
    if retry_allowed:time.sleep(seconds)
    event('retry_after_decision',header=responses[-1]['retry_after'],requested_seconds=seconds,cap_seconds=1,decision='RETRY' if retry_allowed else 'HOLD_UNKNOWN',elapsed_seconds=time.monotonic()-t)
   if retry_allowed and name in ('sequential','payload_conflict','safe_replay','unsafe_retry','503_before','429_valid','restart_replay','restart_conflict','duplicate_mutant','payload_mutant'):
    if name=='unsafe_retry':event('unsafe_retry',prior='UNKNOWN',new_key='key-002')
    event('retry',attempt=2,max_attempts=2)
    responses.append(send(port,key='key-002' if name=='unsafe_retry' else 'key-001',amount=8 if name in ('payload_conflict','restart_conflict','payload_mutant') else 7,mutant=mutant))
   if name=='readback_unavailable':responses.append(send(port,get='blocked'))
  # Wait for controlled delay handler to finish before taking independent DB oracle.
  if name=='timeout':time.sleep(.25)
  c=db(directory/'state.sqlite');effects=c.execute('SELECT op,amount FROM effects').fetchall();c.close()
  findings=[]
  if len(effects)>1:findings.append('DUPLICATE_EFFECT_DETECTED')
  if any(r['status']==409 for r in responses):findings.append('PAYLOAD_CONFLICT_DETECTED')
  if any(r['status']==200 and r['data'].get('completed') for r in responses) and not effects:findings.append('FALSE_COMPLETION_DETECTED')
  if any(e['event']=='unsafe_retry' for e in events):findings.append('UNSAFE_RETRY_DETECTED')
  if name in ('safe_replay','restart_replay') and responses[-1].get('data',{}).get('replayed'):findings.append('SAFE_REPLAY')
  if not responses or responses[-1]['status'] is None or responses[-1]['status'] in (429,503):findings.append('HOLD_UNKNOWN')
  expected_count,expected_codes=CASES[name]
  if name in ('429_valid','429_invalid') and retry_after is not None:
   expected_count=1 if retry_allowed and name=='429_valid' else 0
   expected_codes=[] if expected_count else ['HOLD_UNKNOWN']
  checks={'effect_count':len(effects)==expected_count,'diagnosis':sorted(findings)==sorted(expected_codes)}
  if name=='normal':checks['success_response']=responses[0]['status']==200
  if name=='parallel':checks['responses']=all(r['status']==200 for r in responses)
  if name in ('missing_key','empty_key'):checks['rejection']=responses[0]['status']==400
  if name in ('payload_conflict','restart_conflict'):checks['conflict']=responses[-1]['status']==409
  if name in ('response_lost_after_commit','safe_replay','timeout','readback_unavailable'):checks['unknown']=responses[0]['status'] is None
  if name in ('sequential','safe_replay','restart_replay'):checks['replayed']=responses[-1]['data'].get('replayed') is True
  return dict(schema_version='arl-report-v1',scenario=name,mode='lab',passed=all(checks.values()),checks=checks,findings=findings,effects=effects,effect_count=len(effects),expected_effect_count=expected_count,expected_findings=expected_codes,http=responses,retries=sum(e['event']=='retry' for e in events),oracle={'observer':'test_harness_direct_sqlite','time':'after_requests','does_not_resolve_client_unknown':True},trace=events)
 finally:
  for p in procs:
   if p.poll() is None:
    p.terminate()
    try:p.wait(5)
    except subprocess.TimeoutExpired:p.kill();p.wait(5)
   event('child_reaped',pid=p.pid,returncode=p.returncode,alive=p.poll() is None)
   p.stdout.close()
  for f in stderr_files:f.close()
  (directory/'trace.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))

def error_json(error,**details):
 value=dict(schema_version='arl-summary-v1',status='INVALID_TEST',exit_code=2,error=error,**details)
 print(json.dumps(value));return 2

def main():
 if len(sys.argv)==3 and sys.argv[1]=='_server':
  try:server(sys.argv[2]);return 0
  except Exception as exc:return error_json('server_start_failed',exception=repr(exc))
 class Parser(argparse.ArgumentParser):
  def error(self,message):error_json('invalid_arguments');raise SystemExit(2)
 ap=Parser();ap.add_argument('command',choices=['demo','run','list']);ap.add_argument('--scenario',choices=CASES);ap.add_argument('--out',type=Path)
 ap.add_argument('--retry-after',help='Synthetic 429 header; only with 429_valid')
 ap.add_argument('--test-fault',choices=['spawn','port_init','child_crash','check_timeout','output_write'],help=argparse.SUPPRESS)
 args=ap.parse_args()
 if args.command=='list':print('\n'.join(CASES));return 0
 if not args.out or args.command=='run' and not args.scenario:return error_json('invalid_arguments')
 if args.retry_after is not None and (args.command!='run' or args.scenario!='429_valid'):return error_json('invalid_retry_after_scope')
 try:args.out.mkdir(exist_ok=False)
 except OSError as exc:return error_json('output_unavailable',exception=type(exc).__name__)
 results=[]
 try:
  for name in ([args.scenario] if args.command=='run' else CASES):
   case_dir=args.out/name
   try:
    r=exercise(name,case_dir,retry_after=args.retry_after,test_fault=args.test_fault,check_timeout=.2 if args.test_fault=='check_timeout' else 5)
    from oracle import audit
    r['independent_oracle']=audit(case_dir,r,r['expected_effect_count'])
    r['passed']=r['passed'] and r['independent_oracle']['passed']
   except Exception as exc:r={'schema_version':'arl-report-v1','scenario':name,'passed':False,'findings':['INVALID_TEST'],'exit_code':2,'exception':repr(exc)}
   if args.test_fault=='output_write':raise OSError('injected report write failure')
   (case_dir/'result.json').write_text(json.dumps(r,indent=2)+'\n');results.append(r)
  code=2 if any('INVALID_TEST' in r['findings'] for r in results) else int(not all(r['passed'] for r in results))
  summary={'schema_version':'arl-summary-v1','environment':{'python':platform.python_version(),'platform':platform.platform()},'exit_code':code,'total':len(results),'passed':sum(r['passed'] for r in results),'results':results}
  (args.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({'total':len(results),'passed':summary['passed'],'exit_code':code}));return code
 except (OSError,ValueError) as exc:return error_json('report_write_failed',exception=repr(exc))
if __name__=='__main__':raise SystemExit(main())
