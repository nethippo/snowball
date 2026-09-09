# Redis Search 연동 및 검증 후속 계획

- 작성일: 2026-09-09
- 상태: **후속 작업으로 분리 — 현재 구현·실행하지 않음**
- 사용자 승인 범위: 현재는 Korean Snowball과 형태소 분석 어댑터만 구현한다.
- 선행 구현: [한국어 설계](design.md), [사용 방법](../examples/korean/README.md).
- 이 문서의 Redis 명령과 검색 출력은 향후 검증 예시이며 실행 결과가 아니다.

## 진행 순서와 선행 조건

1. 대상 Redis/RediSearch 릴리스·소스 SHA, 자체 빌드 가능 여부, 배포 형태를 확정한다.
2. **외부 전처리 경로**: Python 어댑터의 `tokens[].canonical`을 저장·검색에 같은 버전으로 사용한다. Snowball 단어 모드의 출력도 별도 인덱스/분석 버전으로 비교한다. 두 모드를 무표시로 혼용하지 않는다.
3. **Snowball native 경로**: Redis가 실제 포함하는 Snowball을 이번 Korean 코드로 빌드하고 Korean 언어 enum/문자열 매핑을 추가한다. 외부 전처리 테스트 통과가 native 통합의 성공을 의미하지 않는다.
4. 개발용 Redis 인스턴스에만 테스트 데이터를 넣고 원형 검색부터 확인한다. 서비스 버전/포트/로드된 모듈을 확인하여 다른 Redis 인스턴스를 시험하는 실수를 막는다.
5. 이후 글자 검색용 필드·query builder·후검증 코드를 구현하고 정답 비교 및 성능 측정을 수행한다.

현재 어댑터는 단어·POS·원문 span·분석 버전만 반환한다. `redis_fields`, n-gram 생성, Redis 의존성, 접속 코드는 아직 구현하지 않았다.

## 1. Redis Search와 Snowball 사이의 실제 경계

공식 지원 언어 목록에는 현재 `korean`이 없다. 한국어 UTF-8 토큰을 저장·검색하는 것과 한국어 형태 분석을 지원하는 것은 별개이다. 외부 전처리 방식에서는 `LANGUAGE korean`을 지정하지 않고 지원되는 기본 언어와 `NOSTEM` 필드를 사용한다. [Redis stemming](https://redis.io/docs/latest/develop/ai/search-and-query/advanced-concepts/stemming/)

조회한 upstream 구현의 흐름은 다음과 같다. 온라인 `master`는 이동하는 참조이며 사용 중인 Redis 바이너리의 버전은 확인하지 않았다.

1. `src/tokenize.c`의 `simpleTokenizer_Next()`가 먼저 `toksep()`으로 단어를 나눈다. 이어 각 단어에 대해 `Stem()`을 한 번 호출하고 반환 문자열/길이를 `t->stem`, `t->stemLen`에 넣는다. [tokenize.c](https://github.com/RediSearch/RediSearch/blob/master/src/tokenize.c)
2. `src/stemmer.c`는 `sb_stemmer_stem()` 결과를 하나의 stem으로 감싼다. Redis 내부 `STEM_PREFIX`는 래퍼가 붙이므로 한국어 Snowball 결과에 직접 `+`를 넣지 않는다. [stemmer.c](https://github.com/RediSearch/RediSearch/blob/master/src/stemmer.c)
3. `src/ext/default.c`의 `StemmerExpander()`에도 언어 선택과 stem 질의 확장 로직이 있다. 색인과 질의 양쪽을 맞춰야 한다. [default.c](https://github.com/RediSearch/RediSearch/blob/master/src/ext/default.c)

따라서 `sb_stemmer_stem()`에서 `"한국어 한 국 어"`, JSON 배열, 쉼표 연결 문자열을 반환해도 **각 항목이 자동으로 재토큰화되지는 않는다**. 이 API에는 복수 token/position 반환 계약이 없다. 반대로 Redis에 저장할 TEXT 필드에 전처리 결과 `"한국어 한 국 어"`를 넣으면 필드 tokenizer가 공백을 보고 나눌 수 있다. 두 호출 위치를 구분해야 한다.

공개 extension 문서는 query expander와 scorer를 설명한다. query expander만 추가하여 문서의 색인 토큰까지 생성했다고 간주할 수 없다. 일반적인 사용자 tokenizer/복수 stem 플러그인 슬롯이 있다고 가정하지 않는다. [Redis extensions](https://redis.io/docs/latest/develop/ai/search-and-query/administration/extensions/)

## 2. C: 글자별 검색 반환·색인 계획

### 2.1 기본 검색 의미

기본의 한 글자는 **NFC 현대 한글 음절**이다. `한국어`는 `한/국/어`이다. 기본 부분 검색은 **canonical 한 단어 안의 연속 부분 문자열**로 정의한다. 어절 경계를 넘는 문자열, 초성 `ㅎㄱㅇ`, 낱자 `ㄱ`, IME 입력 중인 미완성 음절은 후속 옵션이다.

기본 gram은 조사·어미 처리 후 canonical에서 생성한다. 따라서 제거된 `를`이나 `었다`까지 검색하는 기능은 아니다. 화면에 보이는 원문 부분 검색이 필요하면 원문 어절에서 생성한 별도 `surface_chars/surface_bigrams` 필드를 선택적으로 추가한다. canonical gram과 표면형 gram을 한 필드에 섞지 않는다.

| 검색 의미 | `한국어`의 저장 형태 | 질의 방법 | 제약 |
| --- | --- | --- | --- |
| 원형 단어 검색 | `ko_terms TEXT NOSTEM`: `한국어` | `@ko_terms:한국어` | 부분 음절 `국`은 완전한 단어 토큰과 다르다. |
| 한 음절 포함 | `ko_chars TAG`: `한,국,어` | `@ko_chars:{국}` | 흔한 한 글자는 후보가 많다. |
| 두 음절 연속 포함 | `ko_bigrams TAG`: `한국,국어` | `@ko_bigrams:{국어}` | 같은 canonical 내부에서 생성한 gram만 사용한다. |
| 3음절 이상 연속 포함 | 같은 bigram 필드 | `한국어` → `@ko_bigrams:{한국} @ko_bigrams:{국어}` | 후보 검색이며 순서·동일 단어·반복 횟수 확인이 추가로 필요하다. |
| 접두/접미/중간 패턴 대안 | 원형 TEXT, 선택적으로 `WITHSUFFIXTRIE` | `한국*`, `*국어`, `*국어*` | wildcard 최소 길이와 확장 한도, 비용을 확인한다. |
| 초성 검색(선택) | 별도 초성 문자열·gram | `ㅎㄱㅇ` | Unicode 분해/호환 자모 정규화 및 별도 검색 모드 필요 |

prefix/infix/suffix 검색에는 기본 최소 길이 2의 제약이 있고, 일반적인 한 글자 exact token 검색의 제한과는 다르다. `search-min-prefix`(구 버전 `MINPREFIX`)와 확장 상한을 실제 배포 환경에서 확인한다. 한 글자 검색만을 위해 서버 전역 설정을 낮추는 방식은 기본안으로 선택하지 않는다. [질의 문법](https://redis.io/docs/latest/develop/ai/search-and-query/advanced-concepts/query_syntax/), [설정](https://redis.io/docs/latest/develop/ai/search-and-query/administration/configuration/)

### 2.2 전처리 출력과 명령 예시

`한국어를 공부했다.`의 목표 canonical은 `한국어`, `공부하다`이다. 아래는 HASH를 이용한 향후 검증용 예시다. 원문과 canonical 단어 배열의 JSON 문자열은 반환·후검증용으로 보관하고 gram을 단어 사이에서 만들지 않는다.

```text
FT.CREATE idx:ko:v1 ON HASH PREFIX 1 ko:doc: STOPWORDS 0 SCHEMA ko_terms TEXT NOSTEM ko_chars TAG SEPARATOR , ko_bigrams TAG SEPARATOR , analysis_version TAG

HSET ko:doc:1 raw "한국어를 공부했다." canonical_tokens "[\"한국어\",\"공부하다\"]" ko_terms "한국어 공부하다" ko_chars "한,국,어,공,부,하,다" ko_bigrams "한국,국어,공부,부하,하다" analysis_version "ko-morph-v1"

FT.SEARCH idx:ko:v1 '@ko_terms:한국어' RETURN 1 raw DIALECT 2
FT.SEARCH idx:ko:v1 '@ko_chars:{국}' RETURN 1 raw DIALECT 2
FT.SEARCH idx:ko:v1 '@ko_bigrams:{국어}' RETURN 1 raw DIALECT 2
FT.SEARCH idx:ko:v1 '@ko_bigrams:{한국} @ko_bigrams:{국어}' RETURN 2 raw canonical_tokens DIALECT 2
```

TEXT는 미리 정규화한 단어를 ASCII 공백으로 연결한다. `NOSTEM`은 추가 stemming을 막지만 Redis tokenizer 전체를 끄는 옵션은 아니다. TAG는 여기서 완성형 한글만을 쉼표로 직렬화하므로 구분 문자 충돌이 없다. 임의 문자까지 확대할 때는 안전한 encoding 또는 JSON 배열 TAG 설계를 사용한다. `STOPWORDS 0`은 예시 인덱스의 불용어 제거를 해제하기 위한 선택이다. [FT.CREATE](https://redis.io/docs/latest/commands/ft.create/)

### 2.3 정확도·위치·비용

- unigram의 AND인 `국 AND 어`는 `국어`와 같은 의미가 아니다. 다른 단어에 각 글자가 있어도 통과한다. bigram AND도 긴 검색어에서는 후보 생성일 뿐이다. 예를 들어 `가나 다나다`에는 `가나`, `나다`가 있지만 단어 내부에 `가나다`는 없다.
- 길이 3 이상은 `any(query in canonical_word for canonical_word in words)`에 해당하는 검사를 거친다. 원형 부분 검색 모드에서는 검색 문자열 자체를 다시 활용 복원하지 않고 NFC/escape만 적용한다. 일반 단어 검색 모드와 구분한다.
- 검증은 임의의 첫 N개 후보만 확인하고 끝내지 않는다. 정렬이 안정적인 후보 페이지를 계속 읽어 요청 수량을 채우거나 소진한다. 작업량 상한/시간 제한에 도달하면 불완전 결과임을 표시한다. Redis 후보 수를 최종 정확 일치 수로 표시하지 않는다. 정확한 전체 건수가 필요하면 모든 후보 검증 또는 추가 인덱스가 필요하다.
- `raw` 원문을 반환한다. 인공적으로 만든 `ko_terms`에서 얻은 HIGHLIGHT 위치를 원문에 그대로 적용하지 않는다. 별도 span 매핑으로 강조한다. 자연어 phrase 검색 역시 변환된 토큰 순서와 원문 구문 일치가 다름을 표시한다.
- 길이 L의 한글 단어는 최대 L unigram, max(L−1,0) bigram을 생성한다. 문서별 TAG 중복 제거 전 토큰 수 기준 O(L)이며 실제 인덱스 메모리 배수는 측정해야 한다. 모든 길이의 substring을 미리 만드는 O(L²) 방식은 기본안에서 제외한다.
- TAG gram은 문서 내 빈도·위치를 보존하지 않으므로 기본 의미 검색의 점수에 섞지 않는다. 원형 TEXT 검색과 부분 검색을 별도 모드로 제공한다. 함께 보여줄 때의 우선순위는 원형 일치 우선으로 명시한다.
- 3-gram 추가는 후보 수가 너무 큰 경우의 최적화 선택지다. unigram TEXT에 순서·중복을 보존하고 phrase 검색하는 대안도 있으나 어절 경계를 별도로 표현하지 않으면 경계를 넘는 오탐이 생겨 기본안으로 선택하지 않는다.

## 3. D: Redis native 통합을 선택할 경우

외부 전처리와 달리 모듈 안에서 `LANGUAGE korean`을 처리하려면 별도 Redis 저장소/빌드 작업이 필요하다.

1. 대상 Redis/RediSearch 릴리스, 소스 SHA와 배포 제품을 확정하고 실제 vendored Snowball 버전·빌드 경로를 확인한다. 이 프로젝트를 수정하는 것만으로 기존 모듈 바이너리가 바뀌지 않는다.
2. Korean 생성 코드를 Redis가 사용하는 Snowball에 반영하고 언어 enum/문자열 파싱/`RSLanguage_ToSnowballStemmer()` 매핑 및 언어 허용 검증을 수정한다. `src/language.c/.h`와 관련 테스트는 대상 버전에서 재확인한다.
3. 문서 tokenizer와 질의 expander의 처리·최소 stem 길이·UTF-8 길이 단위를 함께 검사한다. byte 길이 조건과 음절 길이를 혼동하지 않는다.
4. 단일 stem 통합은 원형 변환만 해결한다. 글자별 검색까지 내부 생성하려면 복수 토큰 방출, position increment, 원문 offset, field 구분, 질의 분석에 대한 별도 설계·변경이 필요하다.
5. 문맥 형태소 분석기를 모듈 안에 넣으면 모델 로딩·스레드 안전성·최악 실행 시간·메모리·배포 의존성이 추가된다. 단일 단어 콜백에 사전만 붙여 전체 문맥 분석과 같다고 보지 않는다.
6. 기존 인덱스는 새 규칙으로 재색인한다. 롤링 배포 중 분석 버전 혼합을 막고 이전 인덱스/분석 버전으로 되돌릴 수 있게 한다. 관리형 환경의 커스텀 바이너리/extension 지원은 해당 상품에서 확인한다.

native 통합 역시 후속 범위이다. 대상 저장소와 변경 범위를 확정한 후 진행한다.


## 검증 시나리오와 완료 기준

| 경로 | 검증 | 완료 증거 |
| --- | --- | --- |
| Snowball native | `korean/ko/kor`의 libstemmer 호출, Redis에서 허용할 언어 이름, 문서/질의 stem 대칭성 | 실제 모듈 빌드 SHA, 언어 허용·미지원 오류, `학생이 ↔ 학생`, `먹었다 ↔ 먹다`의 검색 결과 |
| 외부 문장 분석 | 원문과 canonical 저장, 어댑터 버전 고정, 질의 전처리 | `공부했다 ↔ 공부하다`, 문맥별 `걸었다/들었다`, 불확실한 단어 보존 결과 |
| 글자 검색 | 1음절 exact TAG, 2음절 gram, 긴 문자열 후보 후검증 | `국`, `국어`, `한국어`, 역순·단어 경계·반복 글자 반례를 직접 substring 정답과 비교 |
| 질의 안전성 | 구분 문자, 빈 질의, 사용자 연산자 escape, 지원 길이 | literal 검색과 고급 DSL 검색을 구분한 회귀 테스트 |
| 페이지·건수 | 첫 페이지 뒤의 실제 일치, 후보 상한·시간 제한 | 실제 일치 수와 후보 수 구분, 불완전 결과의 표시, 정확한 건수 요구에 대한 동작 |
| 원문 강조 | NFC/NFD, 축약형, 인공 토큰 위치 | Redis `HIGHLIGHT` 위치를 원문에 오용하지 않고 span 매핑 검증 |
| 성능 | canonical TEXT만의 baseline 대비 gram 필드 추가 | 문서 수·길이·QPS와 p50/p95/p99, 후보 수, 처리량, RSS/인덱스 크기/갱신 비용 |
| 회귀·배포 | 기존 언어, 새 쓰기·수정·삭제, 재색인, alias 전환 | 문서/질의 분석 버전 혼합 없음, 이전 버전 롤백 |

예상 산출물은 독립 Redis 예제·테스트, 버전이 고정된 개발용 실행 설정, 측정 보고서이다. 실제 Redis 접속·모듈 수정·데이터 색인은 후속 작업이 승인되면 수행한다.

## 분석 버전과 전환

엔진·모델·사전·정규화/규칙을 `analysis_version`으로 고정한다. 새 버전은 v2 문서 키 또는 파생 필드와 새 인덱스에 재색인하며, 새 쓰기·삭제도 동기화한다. 기존 v1 필드를 제자리에서 덮어쓰지 않는다. 인덱스 alias와 질의 분석 버전을 같은 배포 설정으로 전환하고 v1 롤백 경로를 유지한다.

## 후속 결정 사항

문서/질의 규모와 지연 예산, 원형 기준 또는 원문 기준의 글자 검색, 초성 검색 필요 여부, native 통합의 실제 필요성을 확정한다. 다른 조사 전체 제거와 파생 부사 확장은 한국어 처리 정책의 별도 변경이며 Redis 테스트를 위해 임의로 활성화하지 않는다.
