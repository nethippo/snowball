"""Run integration checks against an owned source-built Redis subprocess (stdlib only).

This is a bounded test harness, not a production natural-language query API.
"""
import argparse
import json
from pathlib import Path
import re
import socket
import subprocess
import time


class RedisError(Exception):
    pass


class Redis:
    def __init__(self, port):
        self.socket = socket.create_connection(('127.0.0.1', port), timeout=10)
        self.stream = self.socket.makefile('rb')

    def read(self):
        line = self.stream.readline()
        if not line:
            raise EOFError('Redis closed connection')
        kind, value = line[:1], line[1:-2]
        if kind == b'-':
            raise RedisError(value.decode())
        if kind == b'+':
            return value.decode()
        if kind == b':':
            return int(value)
        if kind == b'$':
            size = int(value)
            if size < 0:
                return None
            value = self.stream.read(size)
            assert self.stream.read(2) == b'\r\n'
            return value.decode()
        if kind == b'*':
            return [self.read() for _ in range(int(value))]
        raise ValueError(line)

    def cmd(self, *args):
        chunks = [str(a).encode() for a in args]
        self.socket.sendall(b'*%d\r\n' % len(chunks) + b''.join(
            b'$%d\r\n' % len(c) + c + b'\r\n' for c in chunks))
        return self.read()

    def close(self):
        self.stream.close()
        self.socket.close()


def fields(value):
    return dict(zip(value[::2], value[1::2]))


def literal(word):
    return ''.join(c if c.isalnum() or c == '_' else '\\' + c for c in word)


def terms(words):
    if not words:
        raise ValueError('empty natural-language query')
    return '@terms:(' + ' '.join(literal(w) for w in words) + ')'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('redis', type=Path)
    ap.add_argument('fixtures', type=Path)
    ap.add_argument('output', type=Path)
    ap.add_argument('--port', type=int, default=16389)
    args = ap.parse_args()
    root = args.redis.resolve()
    fixture = json.loads(args.fixtures.read_text())
    run = root / 'ko-run'
    run.mkdir(exist_ok=True)
    # Refuse to test a pre-existing service or silently re-use an old dataset.
    if (run / 'dump.rdb').exists():
        raise ValueError(f'use a fresh run directory; existing snapshot: {run}/dump.rdb')
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(('127.0.0.1', args.port))
    config = (root / 'redis-full.conf').read_text()
    module_line = 'loadmodule ./modules/redisearch/redisearch.so'
    if config.count(module_line) != 1:
        raise ValueError('unexpected bundled module configuration')
    config = config.replace(module_line, f'loadmodule {root}/modules/redisearch/redisearch.so')
    (run / 'redis.conf').write_text(config)
    result = {'fixture_version': fixture['analysis_version'], 'checks': [], 'queries': [],
              'commands': [], 'gram_queries': [], 'documents': fixture['documents']}
    process = None
    client = None
    log = (run / 'redis.log').open('w')

    def launch():
        nonlocal process, client
        process = subprocess.Popen([str(root / 'src/redis-server'),
            str(run / 'redis.conf'), '--bind', '127.0.0.1', '--port', str(args.port),
            '--dir', str(run), '--daemonize', 'no', '--save', '', '--appendonly', 'no',
            '--logfile', ''], cwd=root, stdout=log, stderr=subprocess.STDOUT)
        for _ in range(150):
            if process.poll() is not None:
                raise RuntimeError(f'Redis failed to start; see {run}/redis.log')
            try:
                client = Redis(args.port)
                if client.cmd('PING') == 'PONG':
                    info = dict(line.split(':', 1) for line in client.cmd('INFO', 'server').splitlines()
                                if ':' in line)
                    if int(info['process_id']) != process.pid:
                        raise RuntimeError('connected process does not match owned server')
                    return info
            except (OSError, RedisError):
                if client:
                    client.close()
                    client = None
                time.sleep(.1)
        raise TimeoutError('Redis readiness')

    def cmd(*args):
        try:
            value = client.cmd(*args)
        except RedisError as exc:
            value = {'error': str(exc)}
        result['commands'].append({'args': args, 'response': value})
        return value

    def check(name, actual, expected):
        result['checks'].append({'name': name, 'passed': actual == expected,
                                 'actual': actual, 'expected': expected})

    def wait_index(index, count):
        for _ in range(100):
            info = fields(client.cmd('FT.INFO', index))
            if int(info['num_docs']) == count and not int(info['indexing']):
                return
            time.sleep(.05)
        raise TimeoutError(f'{index} did not index {count} documents')

    def search(index, query, *options):
        return cmd('FT.SEARCH', index, query, *options, 'LIMIT', 0, 100,
                   'RETURN', 2, 'raw', 'canonical', 'DIALECT', 2)

    def ids(response):
        return sorted(response[1::2]) if isinstance(response, list) else response

    def shutdown():
        nonlocal client
        try:
            client.cmd('SHUTDOWN', 'NOSAVE')
        except EOFError:
            pass
        client.close()
        client = None
        process.wait(timeout=10)

    try:
        result['server'] = launch()
        result['modules'] = cmd('MODULE', 'LIST')
        result['prefix_config'] = cmd('CONFIG', 'GET', 'search-min-prefix')
        check('native index registration', cmd('FT.CREATE', 'ko:native', 'ON', 'HASH',
              'PREFIX', 1, 'native:', 'LANGUAGE', 'korean', 'STOPWORDS', 0,
              'SCHEMA', 'raw', 'TEXT'), 'OK')
        check('adapter index', cmd('FT.CREATE', 'ko:adapter', 'ON', 'HASH', 'PREFIX', 1,
              'adapter:', 'STOPWORDS', 0, 'SCHEMA', 'terms', 'TEXT', 'NOSTEM',
              'chars', 'TAG', 'bigrams', 'TAG'), 'OK')
        for doc in fixture['documents']:
            words = doc['canonical']
            hangul = [w for w in words if re.fullmatch('[가-힣]+', w)]
            chars = sorted(set(''.join(hangul)))
            bigrams = sorted({w[i:i+2] for w in hangul for i in range(len(w)-1)})
            cmd('HSET', 'native:' + doc['id'], 'raw', doc['text'])
            cmd('HSET', 'adapter:' + doc['id'], 'raw', doc['text'],
                'canonical', json.dumps(words, ensure_ascii=False), 'terms', ' '.join(words),
                'chars', ','.join(chars), 'bigrams', ','.join(bigrams))
        wait_index('ko:native', len(fixture['documents']))
        wait_index('ko:adapter', len(fixture['documents']))
        for q in fixture['queries']:
            native = search('ko:native', q['text'])
            expression = terms(q['canonical'])
            adapter = search('ko:adapter', expression)
            expected = sorted('adapter:' + d['id'] for d in fixture['documents']
                              if set(q['canonical']).issubset(d['canonical']))
            check('adapter: ' + q['text'], ids(adapter), expected)
            result['queries'].append({'query': q['text'], 'canonical': q['canonical'],
                'native': native, 'adapter_expression': expression, 'adapter': adapter,
                'native_explain': cmd('FT.EXPLAIN', 'ko:native', q['text'], 'DIALECT', 2)})
        check('native lemma sentence', ids(search('ko:native', '학생 사과 먹다')),
              ['native:d01'])
        check('native unlisted 먹는다 stays literal', ids(search('ko:native', '먹는다')),
              ['native:d02'])
        check('native supported 먹어요 stems symmetrically', ids(search('ko:native', '먹어요')),
              ['native:d01', 'native:d12'])
        check('native VERBATIM removes stem expansion', search('ko:native', '학생 사과 먹다',
              'VERBATIM'), [0])
        check('native ambiguous walk preserved', search('ko:native', '걷다'), [0])
        check('native ambiguous pronoun preserved', search('ko:native', '나 한국어 공부하다'), [0])
        check('native NFC only', ids(search('ko:native', '한국어 공부하다')), ['native:d03'])
        check('native exact syllable does not search substrings', search('ko:native', '국'), [0])
        check('native case-insensitive language', ids(search('ko:native', '먹다', 'LANGUAGE',
              'KOREAN')), ['native:d01', 'native:d12'])
        check('Redis does not expose libstemmer ko alias',
              'error' in search('ko:native', '먹다', 'LANGUAGE', 'ko'), True)
        # A short, exhaustive gram correctness check; no truncated candidate pages.
        for q in ['국', '국어', '한국어', '어국', '공부', '공부하다', '부하다']:
            query = '@chars:{' + q + '}' if len(q) == 1 else ' '.join(
                '@bigrams:{' + q[i:i+2] + '}' for i in range(len(q)-1))
            candidates = search('ko:adapter', query)
            final = []
            for key, data in zip(candidates[1::2], candidates[2::2]):
                if any(q in w for w in json.loads(fields(data)['canonical'])):
                    final.append(key)
            expected = sorted('adapter:' + d['id'] for d in fixture['documents']
                              if any(q in w for w in d['canonical']))
            check('gram substring: ' + q, sorted(final), expected)
            result['gram_queries'].append({'query': q, 'expression': query,
                                           'candidate_response': candidates, 'final_ids': sorted(final)})
        # Deliberate false-positive: bigrams from different words require verification.
        cmd('HSET', 'adapter:boundary', 'raw', '가나 다나다', 'canonical', '["가나", "다나다"]',
            'terms', '가나 다나다', 'chars', '가,나,다', 'bigrams', '가나,다나,나다')
        wait_index('ko:adapter', 17)
        candidate = search('ko:adapter', '@bigrams:{가나} @bigrams:{나다}')
        check('gram boundary candidate exists', ids(candidate), ['adapter:boundary'])
        check('gram boundary postfilter rejects', any('가나다' in w for w in ['가나', '다나다']), False)
        result['gram_boundary'] = candidate
        # Existing-language regression and update/delete lifecycle.
        cmd('FT.CREATE', 'en', 'PREFIX', 1, 'en:', 'LANGUAGE', 'english', 'SCHEMA', 'raw', 'TEXT')
        cmd('HSET', 'en:1', 'raw', 'running cats')
        wait_index('en', 1)
        check('English regression', ids(search('en', 'run cat')), ['en:1'])
        cmd('HSET', 'native:change', 'raw', '학생이 사과를 먹었다.')
        wait_index('ko:native', 17)
        check('write', 'native:change' in ids(search('ko:native', '먹다')), True)
        cmd('HSET', 'native:change', 'raw', '꽃이 예뻤다.')
        check('update removes previous stem', 'native:change' in ids(search('ko:native', '먹다')), False)
        check('update adds new stem', 'native:change' in ids(search('ko:native', '예쁘다')), True)
        cmd('DEL', 'native:change')
        check('delete removes stem', 'native:change' in ids(search('ko:native', '예쁘다')), False)
        before = ids(search('ko:native', '학생 사과 먹다'))
        check('RDB save', cmd('SAVE'), 'OK')
        shutdown()
        result['server_after_reload'] = launch()
        wait_index('ko:native', 16)
        check('RDB preserves Korean language and index', ids(search('ko:native', '학생 사과 먹다')), before)
        check('RDB preserves English language', ids(search('en', 'run cat')), ['en:1'])
        result['native_info'] = cmd('FT.INFO', 'ko:native')
        result['adapter_info'] = cmd('FT.INFO', 'ko:adapter')
    finally:
        if client and process and process.poll() is None:
            shutdown()
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        log.close()
        result['summary'] = {'passed': sum(c['passed'] for c in result['checks']),
                             'failed': sum(not c['passed'] for c in result['checks'])}
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result['summary']))
    for check_result in result['checks']:
        if not check_result['passed']:
            print(json.dumps(check_result, ensure_ascii=False))
    if result['summary']['failed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
