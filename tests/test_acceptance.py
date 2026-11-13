import json,subprocess,sys,tempfile,unittest
from pathlib import Path
import arl
from oracle import audit
EXPECTED=json.loads(Path("tests/expected.json").read_text())
class Acceptance(unittest.TestCase):pass
def make(name):
 def test(self):
  with tempfile.TemporaryDirectory() as td:
   r=arl.exercise(name,Path(td)/'case');self.assertTrue(r['passed'],r);self.assertTrue(audit(Path(td)/'case',r,EXPECTED[name])['passed'])
 return test
for n in arl.CASES:setattr(Acceptance,'test_'+n,make(n))
class Output(unittest.TestCase):
 def test_existing(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'keep';p.write_text('keep');r=subprocess.run([sys.executable,'arl.py','demo','--out',td],capture_output=True,text=True)
   self.assertEqual(r.returncode,2);self.assertEqual(p.read_text(),'keep')

class NegativeControl(unittest.TestCase):
 def test_forged_count(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td)/'case';r=arl.exercise('normal',d);r['effect_count']=2
   self.assertFalse(audit(d,r,1)['passed'])
 def test_false_expected(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td)/'case';r=arl.exercise('duplicate_mutant',d)
   self.assertFalse(audit(d,r,1)['passed'])
