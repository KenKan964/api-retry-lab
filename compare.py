"""F03: independent HTTP/SQLite baseline vs ARL, same four synthetic contracts."""
import argparse
import ast
import json
from pathlib import Path
import platform
import random
import statistics
import time
import unittest
import arl
from oracle import audit
from benchmark.oss_baseline import run_case


def run(out, repeats):
    out.mkdir(exist_ok=False)
    recipes=json.loads(Path('benchmark/cases.json').read_text())
    checks=unittest.TestCase(); records=[]; rng=random.Random(1001)
    source=Path('benchmark/oss_baseline.py').read_text()
    imports=[n.module or '' for n in ast.walk(ast.parse(source)) if isinstance(n,ast.ImportFrom)]
    imports += [a.name for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Import) for a in n.names]
    checks.assertFalse(any(n.split('.')[0] in {'arl','oracle'} for n in imports))
    for iteration in range(repeats):
        for name, recipe in recipes.items():
            modes=['arl','oss'];rng.shuffle(modes)
            for mode in modes:
                directory=out/f'{iteration:02d}_{name}_{mode}'
                started=time.perf_counter_ns()
                if mode=='oss':
                    result=run_case(recipe,directory)
                    count=result['effects']; statuses=[r['status'] for r in result['http']]
                    findings=result['findings']
                else:
                    result=arl.exercise(recipe['arl_scenario'],directory)
                    checks.assertTrue(result['passed'])
                    checks.assertTrue(audit(directory,result,recipe['effects'])['passed'])
                    count=result['effect_count'];statuses=[r['status'] for r in result['http']]
                    findings=result['findings']
                    checks.assertEqual(sum(r.get('data',{}).get('replayed',False) for r in result['http']),recipe['replays'])
                elapsed=(time.perf_counter_ns()-started)/1e6
                checks.assertEqual(count,recipe['effects']);checks.assertEqual(statuses,recipe['statuses']);checks.assertEqual(findings,recipe['findings'])
                (directory/'result.json').write_text(json.dumps(result,indent=2)+'\n')
                records.append(dict(iteration=iteration,case=name,mode=mode,runtime_ms=elapsed,effects=count,statuses=statuses,findings=findings,passed=True))
    result={'schema_version':'arl-f03-v1','python':platform.python_version(),'platform':platform.platform(),
            'repeats':repeats,'seed':1001,'independent_import_check':True,'executions':len(records),
            'all_passed':True,'records':records,'human_work_seconds':None,
            'median_ms':{m:statistics.median(r['runtime_ms'] for r in records if r['mode']==m) for m in ['arl','oss']},
            'limits':['runtime includes spawn, HTTP, SQLite, diagnosis, cleanup; excludes final common result write',
                      'baseline writes its result internally; evidence overhead is not perfectly identical',
                      'four selected contracts only; no general false-positive/negative rate claim']}
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['executions','all_passed','median_ms']}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--repeats',type=int,default=10);a=p.parse_args()
    if a.repeats<1:p.error('repeats must be positive')
    run(a.out,a.repeats)
