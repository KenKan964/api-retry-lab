"""Measured extension experiment: three sequential identical requests, fresh copies."""
import argparse,difflib,hashlib,json,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def delta(old,new):
 added=removed=0
 for line in difflib.ndiff(old.splitlines(),new.splitlines()):
  added+=line.startswith('+ ');removed+=line.startswith('- ')
 return {'added_physical_lines':added,'removed_physical_lines':removed}

def main(out):
 out.mkdir(exist_ok=False)
 original=(ROOT/'arl.py').read_text()
 updated=original.replace('def exercise(name,directory,',"CASES['sequential_three']=(1,[])\n\ndef exercise(name,directory,")
 point='  # Wait for controlled delay handler'
 updated=updated.replace(point,"  if name=='sequential_three':\n   for attempt in (2,3):\n    event('retry',attempt=attempt,max_attempts=3)\n    responses.append(send(port))\n"+point)
 assert updated!=original
 config=json.loads((ROOT/'benchmark/cases.json').read_text())
 before=json.dumps(config,indent=2)+'\n'
 config['sequential_three']={'arl_scenario':'sequential_three','requests':[{'amount':7} for _ in range(3)],'effects':1,'receipts':1,'statuses':[200,200,200],'replays':2,'findings':[]}
 after=json.dumps(config,indent=2)+'\n'
 report={'scenario':'three_same_key_requests','expected':{'effects':1,'statuses':[200,200,200],'replays':2},
         'human_work_seconds':None,'measure_kind':'executed scripted file changes and command counts; not human observations','arms':{}}
 with tempfile.TemporaryDirectory() as td:
  t=Path(td);(t/'arl.py').write_text(updated);shutil.copyfile(ROOT/'oracle.py',t/'oracle.py')
  (t/'cases.json').write_text(after);shutil.copyfile(ROOT/'benchmark/oss_baseline.py',t/'oss_baseline.py')
  commands={
   'arl':[sys.executable,str(t/'arl.py'),'run','--scenario','sequential_three','--out',str(t/'arl-out')],
   'oss':[sys.executable,str(t/'oss_baseline.py'),'--case','sequential_three','--recipes',str(t/'cases.json'),'--out',str(t/'oss-out')]}
  for arm,command in commands.items():
   r=subprocess.run(command,capture_output=True,text=True,timeout=10);assert r.returncode==0,(arm,r.stdout,r.stderr)
   result=json.loads((t/('arl-out/sequential_three/result.json' if arm=='arl' else 'oss-out/result.json')).read_text())
   assert (result['effect_count'] if arm=='arl' else result['effects'])==1
   observations=result['http'];assert [x['status'] for x in observations]==[200,200,200]
   assert sum(x.get('data' if arm=='arl' else 'body',{}).get('replayed',False) for x in observations)==2
   (out/(arm+'_extension_result.json')).write_text(json.dumps(result,indent=2)+'\n')
   report['arms'][arm]={'passed':True,'edited_files':1,'verification_command_invocations':1,
      'code_delta':delta(original,updated) if arm=='arl' else delta('',''),
      'configuration_delta':delta(before,after) if arm=='oss' else delta('',''),
      'environment_setup':{'python_runtimes_required':1,'pip_packages':0,'external_services':0,'install_commands_after_python':0},
      'manual_operations_measured':None}
 for arm,old,new in [('arl',original,updated),('oss',before,after)]:
  (out/(arm+'_addition.patch')).write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=arm+'_before',tofile=arm+'_after')))
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);main(p.parse_args().out)
