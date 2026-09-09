"""Apply the Korean integration to the verified RediSearch v8.10.0 source."""
import argparse
from pathlib import Path
import shutil
import subprocess

PIN = '294c88bca92b3e686d336dc165bcf68512d91ac5'
ROOT = Path(__file__).resolve().parents[2]


def replace_once(path, old, new):
    data = path.read_bytes()
    if new in data:
        return
    if data.count(old) != 1:
        raise ValueError(f'unexpected source layout: {path}')
    path.write_bytes(data.replace(old, new))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('redisearch', type=Path)
    args = parser.parse_args()
    target = args.redisearch.resolve()
    actual = subprocess.check_output(['git', '-C', str(target), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != PIN:
        raise ValueError(f'expected {PIN}, got {actual}')
    # Use upstream's existing custom-Snowball CMake path, preserving its pinned
    # compiler/runtime and every other language algorithm.
    shutil.copyfile(ROOT / 'algorithms/korean.sbl', target / 'deps/stemmers/algorithms/korean.sbl')
    replace_once(target / 'deps/stemmers/modules.txt',
                 b'tagalog         UTF_8                   tagalog,tl,tgl',
                 b'tagalog         UTF_8                   tagalog,tl,tgl\nkorean          UTF_8                   korean,ko,kor')
    replace_once(target / 'src/language.h', b'  RS_LANG_MALAY,\r\n',
                 b'  RS_LANG_MALAY,\r\n  RS_LANG_KOREAN,\r\n')
    replace_once(target / 'src/language.c', b'  { "lithuanian", RS_LANG_LITHUANIAN },',
                 b'  { "korean",    RS_LANG_KOREAN },\n  { "lithuanian", RS_LANG_LITHUANIAN },')
    replace_once(target / 'src/language.c', b'    case  RS_LANG_LITHUANIAN:',
                 b'    case  RS_LANG_KOREAN:     ret = "korean";     break;\n    case  RS_LANG_LITHUANIAN:')
    shutil.copyfile(ROOT / 'integration/redisearch/test_korean.py', target / 'tests/pytests/test_korean.py')
    unit = target / 'tests/cpptests/test_cpp_tokenizer.cpp'
    if 'testKoreanLanguage' not in unit.read_text():
        with unit.open('a') as stream:
            stream.write((ROOT / 'integration/redisearch/korean-unit.inc').read_text())
    print(f'Applied Korean Snowball algorithm and Redis language registration to {target}')


if __name__ == '__main__':
    main()
