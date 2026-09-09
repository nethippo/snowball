# 한국어 단어 stemming과 문장 분석

두 진입점을 제공한다. Snowball은 검증된 어휘·활용형을 처리하는 작은 단어 stemmer이고, Python 어댑터는 Kiwi의 문맥 분석을 사용한다. **한국어 전체의 정확한 품사·원형 복원을 보장하는 구현은 아니다.** Redis 연동·글자 검색은 [후속 계획](../../docs/plan.md)이며 현재 코드에 포함하지 않는다.

## 1. 선택 의존성이 없는 Snowball 단어 모드

저장소 루트에서 실행한다. C 컴파일러, GNU make, Perl이 필요하다.

```sh
make -j4
printf '%s\n' '학생이' '사과를' '먹었다' '공부했다' '고양이' '걸었다' | ./stemwords -l korean
```

출력:

```text
학생
사과
먹다
공부하다
고양이
걸었다
```

C libstemmer에는 `korean`, `ko`, `kor`가 등록된다. UTF-8/NFC 단어를 전달하고 반환 문자열의 길이는 `sb_stemmer_length()`로 읽는다. 기존 buffer 수명/복사 계약은 그대로이다. 문장을 전달해 자동 분리하거나 단일 반환값에 여러 단어를 넣는 API는 아니다.

현재 규칙 버전 `ko-rule-v1`의 범위:

- 다음 24개 base의 받침에 맞는 주격·목적격 조사 경로: `학교 사과 나무 친구 바다 한국어 고양이 자동차 우유 강아지 아이 우리 저희 너희 책 학생 사람 사랑 서울 선생님 마을 집 밥 꽃`.
- 다음 13개 원형에 대응하는 **소스에 명시된 활용형**: `먹다 읽다 좋다 작다 하다 보다 주다 예쁘다 빠르다 돕다 모르다 공부하다 달리다`.
- `내가/제가/네가/누가`, `걸었다/들었다/나는`, 미등록 어휘·활용형, 다른 조사, 복합 조사, 정상 단어는 보존한다. 명사 목록 밖의 `철수가`도 이 모드에서는 그대로이다.
- 지원 목록은 [`algorithms/korean.sbl`](../../algorithms/korean.sbl)의 한글 주석으로 확인할 수 있다. 이 테이블은 전체 한국어 사전이나 POS 판별기의 대체물이 아니다.
- 직접 libstemmer 호출 시 Unicode 정규화는 호출자 책임이다. 기존 `stemwords`는 한 줄을 한 단어로 읽으며 기존 영문 소문자화 동작을 유지한다.

## 2. 선택 설치하는 형태소 분석 어댑터

Python 3.9 이상과 해당 플랫폼용 Kiwi 패키지가 필요하다. 프로젝트의 기본 Snowball 패키지 의존성은 바뀌지 않는다.

```sh
python3 -m venv /tmp/snowball-ko-venv
/tmp/snowball-ko-venv/bin/python -m pip install -r examples/korean/requirements.txt
/tmp/snowball-ko-venv/bin/python examples/korean/korean_analyzer.py '내가 한국어를 공부했다.' --words
```

```json
["나", "한국어", "공부하다"]
```

`--words`를 빼면 단어별 품사·규칙·분석 위치와 버전 정보를 포함한 JSON을 반환한다. 문장 인수가 없으면 UTF-8 stdin 전체를 하나의 입력으로 분석한다. 여러 문서는 API를 반복 호출하며 하나의 분석기를 재사용한다.

Python에서 `examples/korean`을 모듈 검색 경로에 추가한 뒤 사용할 수 있다.

```python
from korean_analyzer import KoreanAnalyzer

analyzer = KoreanAnalyzer()
result = analyzer.analyze("학생이 사과를 먹었다.")
words = [token["canonical"] for token in result["tokens"]]
# ['학생', '사과', '먹다']
```

### 처리 정책

| 항목 | 동작 |
| --- | --- |
| 문장 분리 | Unicode 공백·구두점·제어 문자와 `|+=<>~`를 경계로 나누고, 원래 문장 문맥을 유지해 한 번 분석 |
| 정규화 | UTF-8 검증 후 NFC. 영문/숫자/이모지·호환 자모 어절은 보존 |
| 명사·대명사 | 명사 연쇄 뒤 단일 JKS/JKO만 제거. Kiwi가 복원한 `나/저/너/누구` 사용 |
| 용언 | VV/VA 뒤 선어말어미들과 마지막 어미를 처리하고 `다`를 붙임. 명사/어근+XSV/XSA의 파생 용언도 재조합 |
| 부사 | `빨리/매우/조용히/함께` 유지. `빠르게`가 형용사+어미로 분석되면 `빠르다` |
| 보존 | 다른 조사·조사 연쇄, 보조 용언/서술격 등 미지원 POS 경로, OOV, 교정된 형태, 경계 침범/부분 분석 |
| 모호성 | top-3 후보 중 최상위 점수와 2.0 이내인 후보가 canonical/POS에 이견을 보이면 보존. `--ambiguity-margin`으로 조정 가능 |
| 분석기 오류 | 명시적인 오류. 다른 엔진이나 Snowball로 자동 전환하지 않음 |

점수는 확률이 아니다. 높은 점수의 오분석도 가능하다. 특히 `하늘을 나는 새`에서 Kiwi가 `나/VV`를 내놓는 사례를 확인했으므로 일부 ㄹ 탈락 모호 경로는 `나다`로 잘못 복원하지 않고 `나는`을 보존한다. 이 버전에서 모든 불규칙을 지원했다고 보지 않는다. 동일하게 미지원 `VX` 분석 경로는 `주다` 등을 억지로 생성하지 않는다.

반환 형식:

- `surface`: 원문 어절. `normalized`: 해당 어절의 NFC 형태.
- `canonical`: 정책 적용 결과. 불확실하면 NFC 어절 그대로.
- `lemma`: 확인한 원형. 미지원/불확실한 보존에는 `null`.
- `pos`: `NOUN/PRONOUN/VERB/ADJECTIVE/ADVERB/UNKNOWN`.
- `status`: 형태 변화 여부인 `normalized/preserved`. `preserved`는 실패와 같지 않으며 정상 명사·부사도 포함한다. `rule`이 처리/보존 이유를 설명한다.
- `start_byte/end_byte`: **원문 UTF-8**의 반열린 어절 범위. `eojeol_id`는 순서이며 반복 단어도 유지한다.
- `normalized_start/normalized_end`, `morphemes[].start/end`: **NFC 텍스트 문자 위치**. 축약형의 형태소 범위는 겹칠 수 있다. 원문 byte offset과 혼용하지 않는다.
- `analysis_version/metadata`: 엔진·모델·사용자 사전 hash·Unicode 버전·처리 정책·옵션. 버전 문자열을 고정 상수로 예상하지 말고 실제 반환값을 저장한다.

한글 어절 안에 독립 용언이 여러 개 들어가는 경로는 현재 통째로 보존한다. URL/이메일/제품코드는 구두점에서 분리하며 이를 보호하는 검색용 tokenizer는 별도 범위이다. 기본 입력 상한은 100,000 문자이며 초과 입력은 잘라내지 않고 오류를 반환한다. 인스턴스는 순차 worker별로 사용한다.

### 사용자 명사 사전

```json
[
  {"word": "쀍쀍이", "tag": "NNP"}
]
```

파일을 `--user-dictionary dictionary.json` 또는 `KoreanAnalyzer(user_dictionary=...)`로 전달한다. NFC 한글만으로 이루어진 중복 없는 `NNG/NNP` 항목을 받는다. 사전 추가는 분석 결과를 바꾸므로 hash가 반환 버전에 포함된다. 임의 점수 조정·동사 사전 추가는 이 예제에서 지원하지 않는다.

### 의존성·배포

`kiwipiepy==0.23.1`, `kiwipiepy-model==0.23.0`, `cong` 모델을 고정했다. 버전이 다르면 오류로 알려준다. 최초 모델 로딩 비용이 있으므로 요청마다 새 인스턴스를 만들지 않는다. 핵심 패키지/모델은 고정하지만 numpy/tqdm 등 전이 의존성의 전체 잠금 파일은 제공하지 않는다.

Kiwi와 모델은 Snowball 배포물에 포함하지 않는다. 사용하는 엔진·모델·사전의 배포 조건은 각각 확인해야 한다. [Kiwi 프로젝트의 LGPL v3 안내](https://github.com/bab2min/Kiwi), [사용한 API 문서](https://bab2min.github.io/kiwipiepy/v0.23.1/kr/).

## 3. 검증

저장소 루트에서 실행한다. Node.js는 JavaScript 생성 결과 확인에 필요하다.

```sh
# 외부 말뭉치나 Kiwi 없이: 190개 어휘의 C/Python/JS 출력과 계약 테스트
make check_korean

# 실제 Kiwi 엔진까지 포함
make check_korean_adapter python=/tmp/snowball-ko-venv/bin/python
```

단일 타깃을 직접 실행할 때 Python/JS 코드를 먼저 생성해야 한다.

```sh
make python js
make check_utf8_korean check_python_korean check_js_korean STEMMING_DATA=tests/korean/data
```

전체 언어 회귀에는 별도 공식 `snowball-data`가 필요하다. 해당 checkout에 Korean 데이터가 아직 없으면 `tests/korean/data/korean`을 그 checkout의 `korean`으로 복사한 뒤 `make check STEMMING_DATA=<경로>`를 실행한다. 기존 CI에도 동일한 조건부 보완을 추가했다. 작은 로컬 데이터는 회귀 검증용이며 일반 문장 품질 평가용 말뭉치가 아니다.

실행 결과는 [작업 기록](../../docs/works.md)에, Redis 관련 다음 단계는 [후속 계획](../../docs/plan.md)에 정리한다.
