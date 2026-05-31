# 한국어 Stemmer (Snowball 기반)

[Snowball](https://snowballstem.org/) stemming 프레임워크를 기반으로 구축된 프로덕션 레벨 한국어 stemmer. 사전 기반 하이브리드 접근 방식으로 정확도를 대폭 개선했습니다.

## 개요

이 프로젝트는 Snowball의 한국어 stemmer에 다음 기능을 추가합니다:

1. **불규칙 용언 사전** — 1,097개 활용형 → 어근 매핑 (151개 어근 커버리지)
2. **용언 접미사 제거** — 규칙 기반 한국어 용언 접미사 제거 (과거형, 연결 어미 등)
3. **격 조사 제거** — 규칙 기반 한국어 격 조사 제거 (주격, 목적격, 부사격 등)
4. **사전 기반 lookup 레이어** — 사전 등재어는 O(1) 즉시 반환, 미등재어는 Snowball stemmer로 폴백

## 아키텍처

```
입력 단어
    │
    ▼
┌─────────────────────┐
│  격 조사 제거       │  ← 불규칙 사전 충돌 방지를 위해 가장 먼저 검사
│  (에서, 을/를, 와,   │     (예: '와'가 조사 vs 불규칙 활용형 충돌)
│   이라도, 등)        │
└─────────┬───────────┘
          │ (조사 아님)
          ▼
┌─────────────────────┐
│  불규칙 용언 사전    │  ← O(1) 해시 테이블 lookup
│  lookup             │     1,097개 활용형 → 어근 매핑
└─────────┬───────────┘
          │ (사전 없음)
          ▼
┌─────────────────────┐
│  용언 접미사 제거    │  ← 긴 접미사부터 매칭 (최장 일치)
│                     │     다, 았/었/였, 랐, 랐다, 습니다,어요, 등
└─────────┬───────────┘
          │ (접미사 없음)
          ▼
┌─────────────────────┐
│  내장 사전 lookup   │  ← 사전 등재어는 원형 즉시 반환
└─────────┬───────────┘
          │ (사전 없음)
          ▼
┌─────────────────────┐
│  Snowball stemmer   │  ← 폴백: 기존 Snowball stemmer 처리
└─────────────────────┘
```

## 주요 기능

### 불규칙 용언 사전

주요 한국어 불규칙 용언 패턴 전체 커버리지:

| 패턴 | 설명 | 예시 |
|------|------|------|
| ㅂ-불규칙 | ㅂ consonant shift | 갚다 → 갚 |
| ㄷ-불규칙 | ㄷ consonant shift | 듣다 → 듣, 걷다 → 걷 |
| ㄹ-불규칙 | ㄹ consonant shift | 올리다 → 올, 마다 → 마 |
| ㅅ-불규칙 | ㅅ consonant shift | 짓다 → 짓 |
| ㅆ-불규칙 | ㅆ consonant shift | 바쁘다 → 바쁘 |
| ㅎ-불규칙 | ㅎ consonant shift | 귀찮다 → 귀찮 |
| ㄴ-불규칙 | ㄴ consonant shift | 낫다 → 낫 |
| 특수 | 하다, 크다, 좋다 | 합니다 → 하, 크다 → 크 |

### 용언 접미사 제거

| 접미사 | 유형 | 예시 |
|--------|------|------|
| 다 | 동사/형용사 종결 | 먹다 → 먹, 좋다 → 좋 |
| 았/었/였 | 과거 시제 | 먹었다 → 먹, 했다 → 하 |
| 랐 | 과거 시제 (ㄹ-불규칙) | 올랐다 → 올 |
| 랐다 | 과거 시제 (+다) | 올랐다 → 올 |
| 습니다 | 겸양체 | 합니다 → 하 |
| 어요 | 해요체 | 먹어요 → 먹 |
| 고, 니, 니까, 에서 | 연결 어미 | 먹고 → 먹, 가니 → 가 |

### 격 조사 제거

| 조사 | 유형 | 예시 |
|------|------|------|
| 에서 | 장소를 나타내는 조사 | 학교에서 → 학교 |
| 을/를 | 목적격을 나타내는 조사 | 책을 → 책 |
| 의 | 소유를 나타내는 조사 | 사람의 → 사람 |
| 와/과 | 동시를 나타내는 조사 | 친구와 → 친구 |
| 에, 로, 으로 | 방향/장소를 나타내는 조사 | 학교에 → 학교 |
| 도, 만 | 강조 조사 | 가족도 → 가족, 일만 → 일 |
| 이라도,조차도 | 복합 격 조사 | 가족이라도 → 가족 |
| 까지, 부터, 처럼 | 범위/비교 조사 | 물건까지 → 물건 |

## 사용법

```python
from snowballstemmer.korean_stemmer_dict import KoreanStemmerDict

# 내장 사전 (119개 단어)으로 초기화
stemmer = KoreanStemmerDict(dict_source='builtin')

# 단일 단어 stem
print(stemmer.stem('학교에서'))   # 학교
print(stemmer.stem('받았습니다'))  # 받
print(stemmer.stem('올랐다'))     # 올
print(stemmer.stem('짓다'))       # 짓
print(stemmer.stem('가족이라도')) # 가족

# 배치 stem
words = ['학교에서', '책을', '친구와', '했습니다']
print(stemmer.stemWords(words))   # ['학교', '책', '친구', '했']
```

## 테스트 결과

### 전체: 20/20 통과 (100%) ✅

| 항목 | 결과 |
|------|------|
| 내장 사전 (동사/형용사/명사/부사/조사) | 100% |
| kiwipiepy 사전 | 통과 |
| 성능 벤치마크 | 334,031 words/sec |

### 용언 접미사 제거 (23/23 통과)

| 입력 | 출력 | 상태 |
|------|------|------|
| 받았다 | 받 | ✓ |
| 올랐다 | 올 | ✓ |
| 짓다 | 짓 | ✓ |
| 놀다 | 놀 | ✓ |
| 했습니다 | 했 | ✓ |
| 했어요 | 했 | ✓ |
| 좋아요 | 좋 | ✓ |

### 격 조사 제거 (13/13 통과)

| 입력 | 출력 | 상태 |
|------|------|------|
| 학교에서 | 학교 | ✓ |
| 가족도 | 가족 | ✓ |
| 학교를 | 학교 | ✓ |
| 사람의 | 사람 | ✓ |
| 친구와 | 친구 | ✓ |
| 가족이라도 | 가족 | ✓ |

## 성능

| 방법 | 속도 |
|------|------|
| 사전 lookup stemmer | **334,031 words/sec** |
| 기존 Snowball stemmer | 211,817 words/sec |
| **속도 향상** | **1.58x** |

사전 등재어가 높은 텍스트에서 사전 lookup 레이어가 상당한 속도 향상을 제공합니다. 사전에 등재된 단어는 Snowball stemmer를 호출하지 않고 즉시 반환됩니다.

## 프로젝트 구조

```
snowball-korean/
├── python/
│   └── snowballstemmer/
│       ├── korean_stemmer.py      # 컴파일된 Snowball stemmer (korean.sbl → Python)
│       ├── korean_stemmer_dict.py # 사전 기반 stemmer (본 프로젝트)
│       └── generate_irregular_dict.py  # 불규칙 용언 사전 생성 스크립트
├── data/
│   ├── irregular_verb_dict.json  # 1,097개 활용형 → 어근 매핑
│   ├── korean_dict.json          # 병합된 내장 + kiwipiepy 사전
│   └── korean_dict.pkl           # 병합된 사전 pickle 형식
├── tests/
│   ├── test_korean_stemmer_dict.py  # 사전 stemmer 단위 테스트
│   ├── korean/
│   │   ├── voc.txt               # 테스트 어휘 (32개 단어)
│   │   └── expected_output.txt   # 기대 stemmer 출력
│   └── benchmark_korean_stemmer.py  # 성능 벤치마크
├── scripts/
│   └── load_dict.py              # kiwipiepy 사전 → JSON/Pickle 변환
├── IMPLEMENT-v2.md               # 상세 구현 노트
├── README.md                     # English documentation
└── README-ko.md                  # 이 파일
```

## 구현 노트

### 인코딩 고려사항

원본 Snowball stemmer는 among 테이블에서 jamo-level stringdef를 사용하지만, 한국어 텍스트는 일반적으로 합성 Hangul 음절을 사용합니다. 이 프로젝트는 다음 방식으로 이를 처리합니다:

1. **사전 기반 접근**: 사전 등재어는 사전에서 직접 매칭하여 among 테이블을 우회
2. **규칙 기반 접미사 제거**: 접미사 패턴을 문자 수준에서 정의하여 합성/분해 형태 모두 처리
3. **불규칙 용언 사전**: 활용형 → 어근 매핑을 사전 계산하여 among 테이블 매칭 불필요

### 설계 결정

1. **불규칙 사전보다 격 조사 먼저 검사**: 격 조사(`와` 등)가 불규칙 활용형으로 잘못 매칭되는 충돌 방지
2. **긴 매칭 우선**: 접미사/조사를 길이 내림차순으로 검사하여 부분 매칭 방지 (예: `에서`가 `에`보다 먼저)
3. **Snowball로 폴백**: 사전/규칙으로 커버되지 않는 단어는 기존 Snowball stemmer로 처리하여 최대 커버리지 확보

### 불규칙 용언 사전 생성

불규칙 용언 사전은 `generate_irregular_dict.py`로 프로그램적으로 생성됩니다. 각 불규칙 용언 패턴은 어근과 변환 규칙으로 정의되며, 스크립트가 모든 가능한 활용형을 자동 생성합니다.

```python
# 패턴 정의 예시
{
    'verb': '올리다',
    'root': '올',
    'pattern': 'ㄹ-불규칙',
    'conjugations': {
        '올랐다': '올',
        '올랐어요': '올',
        '올랐습니다': '올',
        # ... 더 많은 활용형
    }
}
```

## 테스트 실행

테스트 스위트 실행:

```bash
cd tests
python3 -m unittest test_korean_stemmer_dict -v
```

성능 벤치마크 실행:

```bash
python3 tests/benchmark_korean_stemmer.py
```

## 관련 링크

- [Snowball](https://snowballstem.org/) — 원본 stemming 프레임워크
- [KiwiPy](https://github.com/bab2min/kiwipy) — 한국어 형태소 분석기 (사전 소스)
- [PR #1](https://github.com/nethippo/snowball/pull/1) — upstream 제출용 Pull Request

## 라이선스

이 프로젝트는 부모 Snowball 프로젝트의 라이선스를 따릅니다.
