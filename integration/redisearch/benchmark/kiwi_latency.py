"""Measure warmed single-word calls to the complete optional Kiwi adapter."""
import json
from pathlib import Path
import random
import sys
import time

root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root / 'examples/korean'))
from korean_analyzer import KoreanAnalyzer

words = [s.split('\t')[0] for s in Path(sys.argv[1]).read_text().splitlines()]
start = time.perf_counter_ns()
analyzer = KoreanAnalyzer()
construction_ns = time.perf_counter_ns() - start
start = time.perf_counter_ns()
analyzer.analyze(words[0])
first_call_ns = time.perf_counter_ns() - start
for _ in range(2):
    for word in words:
        analyzer.analyze(word)
records = []
rng = random.Random(20260909)
for label, pool in [('all', words)] + [(f'length_{n}', [w for w in words if len(w) == n]) for n in range(1, 6)]:
    cycles = max(1, (1000 + len(pool) - 1) // len(pool))
    samples = []
    for trial in range(9):
        order = list(pool)
        rng.shuffle(order)
        checksum = 0
        start = time.perf_counter_ns()
        for _ in range(cycles):
            for word in order:
                result = analyzer.analyze(word)
                checksum += len(result['tokens'])
        elapsed = time.perf_counter_ns() - start
        assert checksum == cycles * len(pool)
        samples.append(elapsed / checksum)
    records.append({'name': label, 'words': len(pool), 'calls_per_trial': len(pool) * cycles,
                    'trials_ns_per_call': samples})
result = {'engine': analyzer.metadata, 'analysis_version': analyzer.analysis_version,
          'construction_ns': construction_ns, 'first_call_ns': first_call_ns,
          'groups': records,
          'examples': {w: [t['canonical'] for t in analyzer.analyze(w)['tokens']]
                       for w in ['학생이', '먹었다', '먹는다', '걸었다', '들었다']}}
Path(sys.argv[2]).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print('Kiwi adapter benchmark complete')
