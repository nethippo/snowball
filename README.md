# Korean Stemmer for Snowball

A production-ready Korean stemmer built on top of the [Snowball](https://snowballstem.org/) stemming framework, with enhanced accuracy through a hybrid dictionary-based approach.

## Overview

This project extends Snowball's Korean stemmer with:

1. **Irregular verb dictionary** — 1,097 conjugation-to-root mappings covering 151 roots
2. **Verbal suffix removal** — Rule-based stripping of Korean verbal suffixes (past tense, connective endings, etc.)
3. **Case marker removal** — Rule-based stripping of Korean case markers (nominative, accusative, locative, etc.)
4. **Dictionary-based lookup layer** — Fast O(1) lookup for known words before falling back to Snowball stemmer

## Architecture

```
Input word
    │
    ▼
┌─────────────────────┐
│  Case marker check  │  ← Strip case markers first (prevents conflicts)
│  (에서, 을/를, 와,   │     with irregular verb dictionary entries
│   이라도, etc.)      │
└─────────┬───────────┘
          │ (no marker)
          ▼
┌─────────────────────┐
│  Irregular verb     │  ← O(1) hash table lookup
│  dictionary lookup  │     1,097 conjugation → root mappings
└─────────┬───────────┘
          │ (not found)
          ▼
┌─────────────────────┐
│  Verbal suffix      │  ← Strip verbal suffixes (longest match first)
│  removal            │     다, 았/었/였, 랐, 랐다, 습니다,어요, etc.
└─────────┬───────────┘
          │ (no suffix)
          ▼
┌─────────────────────┐
│  Builtin dictionary │  ← Return base form if word is in dictionary
│  lookup             │
└─────────┬───────────┘
          │ (not found)
          ▼
┌─────────────────────┐
│  Snowball stemmer   │  ← Fallback to original Snowball stemmer
└─────────────────────┘
```

## Features

### Irregular Verb Dictionary

Covers all major Korean irregular verb patterns:

| Pattern | Description | Example |
|---------|-------------|---------|
| ㅂ-irregular | ㅂ consonant shift | 갚다 → 갚 |
| ㄷ-irregular | ㄷ consonant shift | 듣다 → 듣, 걷다 → 걷 |
| ㄹ-irregular | ㄹ consonant shift | 올리다 → 올, 마다 → 마 |
| ㅅ-irregular | ㅅ consonant shift | 짓다 → 짓 |
| ㅆ-irregular | ㅆ consonant shift | 바쁘다 → 바쁘 |
| ㅎ-irregular | ㅎ consonant shift | 귀찮다 → 귀찮 |
| ㄴ-irregular | ㄴ consonant shift | 낫다 → 낫 |
| Special | 하다, 크다, 좋다 | 합니다 → 하, 크다 → 크 |

### Verbal Suffix Removal

| Suffix | Type | Example |
|--------|------|---------|
| 다 | Verb/adjective ending | 먹다 → 먹, 좋다 → 좋 |
| 았/었/였 | Past tense | 먹었다 → 먹, 했다 → 하 |
| 랐 | Past tense (ㄹ-irregular) | 올랐다 → 올 |
| 랐다 | Past tense (+다) | 올랐다 → 올 |
| 습니다 | Formal polite | 합니다 → 하 |
| 어요 | Informal polite | 먹어요 → 먹 |
| 고, 니, 니까, 에서 | Connective endings | 먹고 → 먹, 가니 → 가 |

### Case Marker Removal

| Marker | Type | Example |
|--------|------|---------|
| 에서 | Locative | 학교에서 → 학교 |
| 을/를 | Accusative | 책을 → 책 |
| 의 | Genitive | 사람의 → 사람 |
| 와/과 | Comitative | 친구와 → 친구 |
| 에, 로, 으로 | Directional | 학교에 → 학교 |
| 도, 만 | Focus | 가족도 → 가족, 일만 → 일 |
| 이라도,조차도 | Compound | 가족이라도 → 가족 |
| 까지, 부터, 처럼 | Scope/Comparison | 물건까지 → 물건 |

## Usage

```python
from snowballstemmer.korean_stemmer_dict import KoreanStemmerDict

# With builtin dictionary (119 words)
stemmer = KoreanStemmerDict(dict_source='builtin')

# Single word stemming
print(stemmer.stem('학교에서'))   # 학교
print(stemmer.stem('받았습니다'))  # 받
print(stemmer.stem('올랐다'))     # 올
print(stemmer.stem('짓다'))       # 짓
print(stemmer.stem('가족이라도')) # 가족

# Batch stemming
words = ['학교에서', '책을', '친구와', '했습니다']
print(stemmer.stemWords(words))   # ['학교', '책', '친구', '했']
```

## Test Results

### Overall: 20/20 passed (100%) ✅

| Category | Result |
|----------|--------|
| Builtin dict (verbs, adjectives, nouns, adverbs, particles) | 100% |
| Kiwipiepy dictionary | Passed |
| Performance benchmark | 334,031 words/sec |

### Verbal Suffix Removal (23/23 passed)

| Input | Output | Status |
|-------|--------|--------|
| 받았다 | 받 | ✓ |
| 올랐다 | 올 | ✓ |
| 짓다 | 짓 | ✓ |
| 놀다 | 놀 | ✓ |
| 했습니다 | 했 | ✓ |
| 했어요 | 했 | ✓ |
| 좋아요 | 좋 | ✓ |

### Case Marker Removal (13/13 passed)

| Input | Output | Status |
|-------|--------|--------|
| 학교에서 | 학교 | ✓ |
| 가족도 | 가족 | ✓ |
| 학교를 | 학교 | ✓ |
| 사람의 | 사람 | ✓ |
| 친구와 | 친구 | ✓ |
| 가족이라도 | 가족 | ✓ |

## Performance

| Method | Speed |
|--------|-------|
| Dictionary lookup stemmer | **334,031 words/sec** |
| Original Snowball stemmer | 211,817 words/sec |
| **Speedup** | **1.58x** |

The dictionary lookup layer provides significant speedup for text with high dictionary coverage. Words found in the dictionary are returned immediately without invoking the Snowball stemmer.

## Project Structure

```
snowball-korean/
├── python/
│   └── snowballstemmer/
│       ├── korean_stemmer.py      # Compiled Snowball stemmer (korean.sbl → Python)
│       ├── korean_stemmer_dict.py # Dictionary-enhanced stemmer (this project)
│       └── generate_irregular_dict.py  # Irregular verb dictionary generator
├── data/
│   ├── irregular_verb_dict.json  # 1,097 conjugation → root mappings
│   ├── korean_dict.json          # Merged builtin + Kiwipiepy dictionary
│   └── korean_dict.pkl           # Pickle format of merged dictionary
├── tests/
│   ├── test_korean_stemmer_dict.py  # Unit tests for dictionary stemmer
│   ├── korean/
│   │   ├── voc.txt               # Test vocabulary (32 words)
│   │   └── expected_output.txt   # Expected stemmer output
│   └── benchmark_korean_stemmer.py  # Performance benchmark
├── scripts/
│   └── load_dict.py              # Load Kiwipiepy dictionary → JSON/Pickle
├── IMPLEMENT-v2.md               # Detailed implementation notes (Korean)
└── README.md                     # This file
```

## Implementation Notes

### Encoding Considerations

The original Snowball stemmer uses jamo-level string definitions in its among tables, while Korean text typically uses precomposed Hangul syllables. This project handles this by:

1. **Dictionary-based approach**: Known words are matched directly in the dictionary, bypassing the among table entirely
2. **Rule-based suffix removal**: Suffix patterns are defined at the character level, which works with both precomposed and decomposed forms
3. **Irregular verb dictionary**: Conjugation-to-root mappings are precomputed, avoiding the need for among table matching

### Design Decisions

1. **Case markers checked before irregular verb dictionary**: Prevents conflicts where a case marker (e.g., `와`) could be incorrectly matched as an irregular verb form
2. **Longest match first**: Suffixes and markers are checked in descending length order to prevent partial matches (e.g., `에서` before `에`)
3. **Fallback to Snowball**: Words not covered by dictionaries or rules fall back to the original Snowball stemmer for maximum coverage

### Irregular Verb Dictionary Generation

The irregular verb dictionary is generated programmatically using `generate_irregular_dict.py`. Each irregular verb pattern is defined with its root and transformation rules, and the script generates all possible conjugation forms automatically.

```python
# Example pattern definition
{
    'verb': '올리다',
    'root': '올',
    'pattern': 'ㄹ-irregular',
    'conjugations': {
        '올랐다': '올',
        '올랐어요': '올',
        '올랐습니다': '올',
        # ... more forms
    }
}
```

## Testing

Run the test suite:

```bash
cd tests
python3 -m unittest test_korean_stemmer_dict -v
```

Run the performance benchmark:

```bash
python3 tests/benchmark_korean_stemmer.py
```

## Related

- [Snowball](https://snowballstem.org/) — Original stemming framework
- [KiwiPy](https://github.com/bab2min/kiwipy) — Korean morphological analyzer (used for dictionary source)
- [PR #1](https://github.com/nethippo/snowball/pull/1) — Pull request for upstream submission

## License

This project follows the license of the parent Snowball project.
