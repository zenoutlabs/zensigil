"""Repeatable local throughput evidence, not a cross-language performance claim."""
import argparse
import json
import platform
import statistics
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from zensigil import __version__, run

CASES = {
    'closure_map': ('let factor = 3\nemit map(range(100), fn (n) => n * factor)', [list(range(0, 300, 3))]),
    'group_counts': ('emit count_by(range(100), fn (n) => choose n % 2 == 0 then "even" otherwise "odd")', [{'even': 50, 'odd': 50}]),
    'typed_sum': ('let numbers: list<integer> = range(100)\nemit sum(numbers)', [4950]),
}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--iterations',type=int,default=25)
    args=parser.parse_args()
    if not 1 <= args.iterations <= 1000:parser.error('iterations must be 1 through 1000')
    rows=[]
    for name,(source,expected) in CASES.items():
        timings=[]
        for _ in range(args.iterations):
            start=time.perf_counter();result=run(source);elapsed=time.perf_counter()-start
            if not result['ok'] or result['values']!=expected:raise RuntimeError((name,result))
            timings.append(elapsed*1000)
        rows.append({'name':name,'median_ms':round(statistics.median(timings),3),'min_ms':round(min(timings),3),
                     'max_ms':round(max(timings),3),'steps':result['stats']['steps']})
    print(json.dumps({'version':__version__,'python':platform.python_version(),'platform':platform.platform(),
                      'iterations':args.iterations,'includes':'parse, check and run','workloads':rows},indent=2))
if __name__=='__main__':main()
