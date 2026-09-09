"""Prepare real Kiwi outputs outside the Redis process for reproducible comparisons."""
import json
from pathlib import Path
import sys
import unicodedata

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'examples/korean'))
from korean_analyzer import KoreanAnalyzer

analyzer = KoreanAnalyzer()
sentences = [
    '학생이 사과를 먹었다.', '학생이 사과를 먹는다.',
    '내가 한국어를 공부했다.', '길을 걸었다.', '전화를 걸었다.',
    '소리를 들었다.', '짐을 들었다.', '꽃이 예뻤다.', '빠르게 달렸다.',
    '빨리 매우 조용히 함께', '고양이가 책을 읽었다.',
    '학생이，사과를/먹었다.', unicodedata.normalize('NFD', '한국어를 공부했다.'),
    '학교에서 책만 읽었다.', '나는 책을 읽었다.', '쀍쀍이가 좋았다.',
]
queries = ['학생 사과 먹다', '학생이 사과를 먹었다.', '먹는다',
           '한국어 공부하다', '내가 한국어를 공부했다.', '나 한국어 공부하다',
           '길을 걸었다.', '길 걷다', '전화 걸다', '소리 듣다', '짐 들다',
           '꽃 예쁘다', '빠르다 달리다', '빨리', '고양이 책 읽다',
           '학생이，사과를/먹었다.', '학교 책 읽다', '학교에서 책만 읽었다.',
           '쀍쀍이가 좋았다.', '국', '국어']

def analyze(text):
    result = analyzer.analyze(text)
    return {'text': text, 'canonical': [t['canonical'] for t in result['tokens']],
            'tokens': result['tokens']}

result = {'analysis_version': analyzer.analysis_version, 'metadata': analyzer.metadata,
          'documents': [dict(id=f'd{i:02}', **analyze(s)) for i, s in enumerate(sentences, 1)],
          'queries': [analyze(s) for s in queries]}
Path(sys.argv[1]).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(f"Prepared {len(sentences)} documents and {len(queries)} queries using {analyzer.analysis_version}")
