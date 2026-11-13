import hashlib,json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
import arl
ROOT=Path(__file__).resolve().parents[1]

def preserve(name,data):
 if os.environ.get('ARL_EVIDENCE'):
  p=Path(os.environ['ARL_EVIDENCE']);p.mkdir(parents=True,exist_ok=True)
  (p/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

class RetryAfter(unittest.TestCase):pass

def retry_test(value,seconds):
 def test(self):
  with tempfile.TemporaryDirectory() as td:
   out=Path(td)/'run';t=time.monotonic()
   r=subprocess.run([sys.executable,str(ROOT/'arl.py'),'run','--scenario','429_valid','--retry-after='+value,'--out',str(out)],capture_output=True,text=True,timeout=10)
   total=time.monotonic()-t;result=json.loads((out/'429_valid/result.json').read_text())
   decision=next(x for x in result['trace'] if x['event']=='retry_after_decision')
   preserve('F01_'+hashlib.sha256(value.encode()).hexdigest()[:12],dict(value=value,total_seconds=total,exit_code=r.returncode,result=result))
   self.assertEqual(r.returncode,0,r.stderr);self.assertTrue(result['independent_oracle']['passed'])
   self.assertEqual(result['retries'],int(seconds is not None));self.assertLess(total,10)
   self.assertEqual(decision['requested_seconds'],seconds)
   if seconds is not None:
    self.assertGreaterEqual(decision['elapsed_seconds'],seconds);self.assertLess(decision['elapsed_seconds'],seconds+3);self.assertEqual(result['effect_count'],1)
   else:
    self.assertEqual(result['findings'],['HOLD_UNKNOWN']);self.assertEqual(result['effect_count'],0)
 return test
for name,value,expected in [('positive','1',1),('zero','0',0),('excess','2',None),('negative','-1',None),('empty','',None),('text','oops',None),('date','Wed, 21 Oct 2037 07:28:00 GMT',None)]:
 setattr(RetryAfter,'test_'+name,retry_test(value,expected))

class Failures(unittest.TestCase):pass

def fault_test(fault):
 def test(self):
  with tempfile.TemporaryDirectory() as td:
   out=Path(td)/'run'
   r=subprocess.run([sys.executable,str(ROOT/'arl.py'),'run','--scenario','normal','--test-fault',fault,'--out',str(out)],capture_output=True,text=True,timeout=10)
   reported=json.loads(r.stdout);self.assertEqual(r.returncode,2);self.assertEqual(reported['exit_code'],2)
   trace=[json.loads(x) for x in (out/'normal/trace.jsonl').read_text().splitlines()]
   spawned=[x['pid'] for x in trace if x['event']=='child_spawned'];reaped=[x for x in trace if x['event']=='child_reaped']
   self.assertEqual(spawned,[x['pid'] for x in reaped]);self.assertTrue(all(not x['alive'] for x in reaped))
   preserve('F02_'+fault,dict(exit_code=r.returncode,stdout=reported,trace=trace,all_owned_children_reaped=True))
 return test
for f in ['port_init','spawn','child_crash','check_timeout','output_write']:setattr(Failures,'test_'+f,fault_test(f))
class Rejects(unittest.TestCase):
 def test_output_parent_missing(self):
  with tempfile.TemporaryDirectory() as td:
   r=subprocess.run([sys.executable,str(ROOT/'arl.py'),'demo','--out',str(Path(td)/'absent/run')],capture_output=True,text=True)
   self.assertEqual(r.returncode,2);self.assertEqual(json.loads(r.stdout)['exit_code'],2)
 def test_existing_preserved(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'marker';p.write_bytes(b'unchanged');before=hashlib.sha256(p.read_bytes()).hexdigest()
   r=subprocess.run([sys.executable,str(ROOT/'arl.py'),'demo','--out',td],capture_output=True,text=True)
   self.assertEqual(r.returncode,2);self.assertEqual(json.loads(r.stdout)['exit_code'],2);self.assertEqual(p.read_bytes(),b'unchanged')
   preserve('F02_existing_output',dict(exit_code=r.returncode,report=json.loads(r.stdout),before_sha256=before,after_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 def test_internal_start_without_ownership(self):
  with tempfile.TemporaryDirectory() as td:
   r=subprocess.run([sys.executable,str(ROOT/'arl.py'),'_server',td],capture_output=True,text=True)
   self.assertEqual(r.returncode,2);self.assertEqual(json.loads(r.stdout)['exit_code'],2)
