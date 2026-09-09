"""Sequential, persistent-connection Redis latency; never interpret it as stem-only latency."""
import json
from pathlib import Path
import random
import socket
import subprocess
import sys
import time

root = Path(sys.argv[1]).resolve()
# Use the stdlib RESP2 client from the existing integration harness.
sys.path.insert(0, str(root))
from ko_check import Redis

words = [line.split('\t')[0] for line in Path(sys.argv[2]).read_text().splitlines()]
port = 16391
with socket.socket() as probe:
    probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    probe.bind(('127.0.0.1', port))
run = root / 'ko-benchmark' / 'redis-run'
run.mkdir(exist_ok=True)
if (run / 'dump.rdb').exists():
    raise ValueError('existing benchmark dataset')
log = (run / 'redis.log').open('w')
proc = subprocess.Popen(['taskset', '-c', '2', str(root / 'src/redis-server'),
                        '--bind', '127.0.0.1', '--port', str(port), '--dir', str(run),
                        '--save', '', '--appendonly', 'no', '--loadmodule',
                        str(root / 'modules/redisearch/redisearch.so')],
                       cwd=run, stdout=log, stderr=subprocess.STDOUT)
client = None
result = {}
try:
    for _ in range(100):
        if proc.poll() is not None:
            raise RuntimeError('server exited; see redis.log')
        try:
            client = Redis(port)
            if client.cmd('PING') == 'PONG': break
        except OSError:
            time.sleep(.05)
    if client is None:
        raise TimeoutError('Redis not ready')
    info = dict(line.split(':', 1) for line in client.cmd('INFO', 'server').splitlines() if ':' in line)
    assert int(info['process_id']) == proc.pid
    result['server'] = info
    result['modules'] = client.cmd('MODULE', 'LIST')
    client.cmd('FT.CREATE', 'ko:bench', 'ON', 'HASH', 'PREFIX', 1, 'bench:',
               'LANGUAGE', 'korean', 'STOPWORDS', 0, 'SCHEMA', 'raw', 'TEXT')
    for i, word in enumerate(words):
        client.cmd('HSET', f'bench:{i}', 'raw', word)
    for word in words:
        assert client.cmd('FT.SEARCH', 'ko:bench', word, 'NOCONTENT', 'LIMIT', 0, 0,
                          'DIALECT', 2)[0] >= 1
    operations = [
        ('ping', lambda word: ('PING',)),
        ('search_count', lambda word: ('FT.SEARCH', 'ko:bench', word, 'NOCONTENT', 'LIMIT', 0, 0, 'DIALECT', 2)),
        ('search_return_raw', lambda word: ('FT.SEARCH', 'ko:bench', word, 'LIMIT', 0, 10, 'RETURN', 1, 'raw', 'DIALECT', 2)),
    ]
    result['groups'] = []
    rng = random.Random(20260909)
    cycles = 11
    for name, command in operations:
        # Prepare command strings outside the measured region.
        commands = [command(w) for w in words]
        for args in commands:
            client.cmd(*args)
        samples = []
        for _ in range(9):
            rng.shuffle(commands)
            start = time.perf_counter_ns()
            for _ in range(cycles):
                for args in commands:
                    value = client.cmd(*args)
            elapsed = time.perf_counter_ns() - start
            samples.append(elapsed / (cycles * len(commands)))
        result['groups'].append({'name': name, 'calls_per_trial': cycles * len(commands),
                                  'trials_ns_per_call': samples})
    result['example'] = client.cmd('FT.SEARCH', 'ko:bench', '학생이', 'RETURN', 1, 'raw', 'DIALECT', 2)
finally:
    if client:
        if proc.poll() is None:
            try: client.cmd('SHUTDOWN', 'NOSAVE')
            except EOFError: pass
        client.close()
    if proc.poll() is None:
        try: proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait(timeout=10)
    log.close()
Path(sys.argv[3]).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print('Redis RTT benchmark complete')
