import ast,json,tempfile,unittest
from pathlib import Path
from benchmark.oss_baseline import run_case
RECIPES=json.loads(Path('benchmark/cases.json').read_text())
class Baseline(unittest.TestCase):
 def test_independent_imports(self):
  tree=ast.parse(Path('benchmark/oss_baseline.py').read_text())
  names=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
  names += [a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names]
  self.assertFalse(set(n.split('.')[0] for n in names)&{'arl','oracle'})
def make(recipe):
 def test(self):
  with tempfile.TemporaryDirectory() as td:self.assertTrue(run_case(recipe,Path(td)/'case')['passed'])
 return test
for name,recipe in RECIPES.items():setattr(Baseline,'test_'+name,make(recipe))
