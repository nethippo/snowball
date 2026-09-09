# 작업 기록

최신 상태: **한국어 Snowball(A) + 형태소 분석 어댑터(B) 구현 및 로컬 검증 완료**.
Redis 연동·테스트는 사용자 지시에 따라 [후속 계획](plan.md)으로 분리했다.
아래 첫 기록은 구현 승인 이전의 검토 이력이며, 실제 변경·검증 결과는 두 번째 기록에 있다.

## 2026-09-09 — 한국어 stemming 및 Redis Search 설계 검토

### 요청과 수행 범위

한국어 문장 분리, 명사·대명사의 주격/목적격 조사 제거, 동사·형용사 등의 원형 복원, Redis Search의 한글 글자별 검색을 검토했다. 요청에 따라 구현 코드는 수정하지 않고 `docs/design.md`와 이 작업 기록만 작성했다. 상태는 **설계 검토 완료 / 구현 승인 대기**이다.

### 확인한 기준과 근거

- 작업 경로: `/Users/gimbonghwan/projects/snowball`
- 기준 커밋: `5f0b93ea7353433231dd645a08a865156d27ae49` — `Support compiling with MSVC -clatest option`
- 시작 시 `git status --short`에 변경이 없었다. 기존 `docs/`와 요청된 두 문서는 없었다.
- 저장소와 상위 경로의 `AGENTS.md`를 확인했으며 적용할 파일은 발견하지 못했다.
- `README.rst`, `CONTRIBUTING.rst`, `include/libstemmer.h`, `libstemmer/libstemmer_c.in`, `libstemmer/modules.txt`, `GNUmakefile`, `examples/stemwords.c`, Tamil/Turkish 알고리즘, UTF-8 runtime, CI 구성을 읽었다.
- 한국어 등록이 없고 기존 ABI가 단일 입력 단어 → 단일 문자열인 것을 확인했다. 테스트 기본 경로인 `../snowball-data`는 없다.
- Redis Search 스킬과 Redis 공식 stemming·명령·질의·설정·extension 문서, upstream tokenizer/stemmer/query expander, Kiwi 공개 문서, Unicode 정규화 규격을 검토했다. 외부 근거 링크는 [설계서](design.md)에 해당 주장과 함께 기록했다.
- 쉘의 GitHub raw 조회는 DNS 제한으로 실패했다. 웹 도구로 문서와 관련 소스를 확인했다. upstream `master`/온라인 문서는 특정 배포 바이너리의 검증 결과가 아니므로 실제 연동 시 릴리스와 SHA를 고정해야 한다.

### 주요 검토 결과

| 항목 | 결론 |
| --- | --- |
| 한국어 Snowball 추가 | 가능. `korean.sbl` 및 `korean,ko,kor` 등록을 계획하되 단어 단위의 제한된 규칙으로 정의한다. |
| 문장·품사 처리 | 기존 libstemmer 기능과 분리한 어댑터가 필요하다. 공백 분리 후에도 문맥과 원문 위치를 보존해야 한다. |
| 조사 제거 | 주격·목적격으로 분석된 경로만 제거한다. `고양이/국가/사과/마을` 같은 단어 보호와 대명사 기저형 복원이 필요하다. |
| 활용형 원형 복원 | 규칙만으로 전부 해결할 수 없다. `걸었다/들었다`의 문맥 모호성을 포함해 형태소 분석·사전·재조합을 사용한다. |
| 부사 | 독립 부사는 유지한다. `빠르게` 같은 용언의 부사형과 `빨리/매우` 같은 부사를 구분한다. |
| Redis 반환 방식 | stem 반환값을 공백으로 연결해도 복수 토큰으로 다시 분리되지 않는다. 별도 TEXT/TAG 필드에 직렬화한다. |
| 글자별 검색 | 기본은 완성형 한글 음절. unigram/bigram으로 후보를 만들고 긴 부분 검색의 연속성·동일 단어 여부를 확인한다. |
| native Redis 통합 | Snowball 변경만으로 자동 반영되지 않는다. 언어 등록·빌드·색인/질의 양쪽 변경이 필요해 후속 선택 범위로 분리했다. |

### 작성한 계획

`docs/design.md`에 다음 내용을 포함했다.

1. 요구사항별 가능 여부와 Snowball/형태소 분석/Redis의 역할 구분.
2. 조사 범위, 품사별 원형·보존 정책, 축약·불규칙·대명사 및 오변환 반례.
3. Unicode 정규화, 공백·구분 문자, 원문 byte span과 문맥 유지 방식.
4. 단일 stem 및 문장 결과 목록의 반환 계약과 구체적 JSON 예시.
5. Redis TEXT/TAG 스키마, 색인·질의 예시, wildcard 대안, 초성 검색의 선택 범위.
6. gram 오탐 후검증, 페이지 처리, 최종 건수, 원문 하이라이트와 성능 비용.
7. 단계별 변경 예정 파일, 말뭉치 준비, 검증 명령, 정확도·성능 수용 기준.
8. 분석 버전 고정, 재색인·전환·롤백, 권장 구현 승인 범위와 제외 범위.

### 검증 범위와 제한

- 이번 검증은 로컬 소스 및 공개 문서에 대한 정적 검토와 문서 일관성 확인이다.
- 구현 코드, 알고리즘 등록, 빌드/CI 설정, 의존성은 변경하지 않았다.
- 빌드, stemmer 단위 테스트, 형태소 분석기 실행, Redis 명령 실행, 성능 측정을 수행하지 않았다. 문서 예제는 기대 동작이며 통과한 테스트 결과가 아니다.
- 실행 중인 Redis나 배포 환경에 접속하지 않았다. Redis 버전, 서비스 형태, 문서 규모, QPS, latency 예산은 미확정이며 승인 이후 구현 단계에서 확인할 항목이다.
- 최종 문서 검증을 통과했다: 두 파일의 존재, Markdown 코드 블록 균형, 문서 내부 상대 링크, JSON 구문, 예시의 UTF-8 byte span, 줄 끝 공백/개행을 확인했다.
- Redis 예시의 unigram/bigram 목록과 긴 검색어의 오탐 반례를 간단한 계산으로 확인했다. 이는 Redis 통합 실행 검증과 구분한다.
- `git diff --check`를 통과했다. 추적 중인 파일의 변경은 없고, 미추적 파일은 `docs/design.md`, `docs/works.md` 두 개뿐임을 확인했다. 설계서의 Python/JavaScript 개별 언어 테스트 target도 `GNUmakefile`에서 확인했다.

### 산출물과 다음 단계

- [설계 계획서](design.md)
- [작업 기록](works.md)
- 권장 구현안: **A 제한적 Snowball 한국어 지원 + B 독립 형태소 분석 어댑터 + C 외부 전처리 기반 Redis 글자 검색**.
- 다음 단계: 사용자의 계획 승인 후 계약·평가 데이터를 확정하고 순차적으로 구현한다. Redis native 통합, 운영 배포, 커밋 및 push는 이번 작업에서 수행하지 않는다.

## 2026-09-09 — 승인된 A+B 구현 및 Redis 후속 계획 분리

### 확정된 범위

사용자가 제한적 Snowball 한국어 지원과 형태소 분석 어댑터의 구현을 승인했다. Redis 연동·테스트는 이번 구현에서 제외하고 `docs/plan.md`로 옮겼다. 커밋·push·운영 배포는 수행하지 않았다.

### 구현 결과

| 파일/구성 | 변경과 목적 |
| --- | --- |
| `algorithms/korean.sbl` | 24개 명사/대명사 base의 올바른 주격·목적격 조사 경로와 13개 용언의 명시적 활용형. 미등록/알려진 모호한 입력을 보존하는 `ko-rule-v1` 구현 |
| `libstemmer/modules.txt` | `korean UTF_8 korean,ko,kor` 등록. 기존 ABI와 CLI의 한 줄=한 단어 계약 유지 |
| `examples/korean/korean_analyzer.py` | 실제 Kiwi 문맥 분석, 완전한 품사 경로 검사, 사전형 재조합, 독립 부사 유지, OOV/모호성/미지원 경로 보존, 원문 UTF-8 byte span 및 NFC 형태소 위치, JSON CLI/API |
| `examples/korean/requirements.txt` | 별도 설치 Kiwi 0.23.1 및 모델 패키지 0.23.0 고정. 기본 libstemmer/Python 패키지에 필수 의존성을 추가하지 않음 |
| `examples/korean/README.md`, `README.rst` | 지원 어휘, 제한, 사용자 명사 사전, 설치·실행·테스트 방법과 반환 계약 |
| `tests/korean/` | 수작업 어휘 190쌍 및 C alias/고정점/비변환, Unicode/반환 계약, 실제 Kiwi 문장·사용자 사전·CLI 통합 테스트 |
| `GNUmakefile` | `check_korean`, `check_korean_adapter` 추가. 로컬 Korean 데이터로 C/Python/JS 비교 및 선택 분석기 테스트 |
| `.github/workflows/ci.yml`, `coverage.yml` | 공식 데이터 checkout에 Korean이 없을 때 로컬 회귀 데이터를 조건부 복사. 외부 Korean 데이터가 있으면 유지 |
| `.github/workflows/korean.yml` | Linux/Python 3.11 및 macOS/Python 3.12의 선택 어댑터 CI 추가. 원격 CI는 아직 실행하지 않음 |
| `docs/design.md`, `docs/plan.md` | A+B의 실제 범위·제한 반영, Redis 외부 전처리/native 연동·글자 검색·테스트·재색인 계획 분리 |

모델에는 `cong`를 명시했다. 실제 조사 과정에서 구형 `knlm` 파일은 선택한 모델 패키지에 없음을 확인했다. 외부 엔진·모델 파일은 저장소에 넣지 않고 임시 가상환경에 설치했다.

### 실제 검증 결과

| 검증 | 결과 |
| --- | --- |
| `make -j4` | 전체 C 빌드 통과 |
| `make check_korean_adapter python=/private/tmp/snowball-korean-venv/bin/python` | C/Python/JavaScript의 Korean 190개 어휘 출력 일치, 계약 및 실제 Kiwi 테스트 통과 |
| 최종 `python -m unittest discover -s tests/korean -v` | **23개 테스트 통과**. Unicode 구분 문자 NFC 정규화 회귀 포함. 실제 문장 골든 케이스는 18개 subtest |
| `make -j4 check STEMMING_DATA=/private/tmp/snowball-korean-data` | compiler/stemtest 및 **59개 언어·인코딩 조합**의 공식 어휘 회귀 통과 |
| `make cxx` 및 `make check_cxx_korean STEMMING_DATA=tests/korean/data` | C++ 생성·빌드 및 동일 190개 어휘 검증 통과 |
| `make dist_libstemmer_c` 및 별도 임시 경로의 tarball 빌드 | `libstemmer_c-3.1.1.tar.gz` 생성·재빌드와 `ko` alias smoke 통과 |
| 문서·변경 범위 | Markdown 링크/JSON, UTF-8, 공백 오류, Git 변경 목록 확인. Redis 코드·의존성·접속 없음 |

공식 `snowball-data`는 임시 경로에 읽기용으로 내려받았다. 기준 SHA는 `a0ec0d0a2839ec885878868de20fcb63209d92b0`이며 로컬 Korean 데이터만 그 임시 checkout에 추가했다. 소스·runtime·compiler의 기존 알고리즘 구현을 바꾸지 않았다.

실제 출력으로 확인한 대표 사례:

```text
단어 모드: 학생이 → 학생, 공부했다 → 공부하다, 고양이 → 고양이, 걸었다 → 걸었다
문장 모드: 내가 한국어를 공부했다. → 나 / 한국어 / 공부하다
문장 모드: 길을 걸었다. 전화를 걸었다. → 길 / 걷다 / 전화 / 걸다
문장 모드: 소리를 들었다. 짐을 들었다. → 소리 / 듣다 / 짐 / 들다
```

### 측정과 남은 제약

- macOS ARM, Python 3.11.14의 별도 프로세스에서 짧은 4개 문장을 100회 순차 분석한 소규모 측정: 초기화+첫 분석 약 **601 ms**, warm p50 **0.262 ms**, p95 **0.457 ms**, p99 **0.550 ms**. 최대 RSS 약 **434 MiB**. 캐시 영향을 포함하며 운영 성능 또는 다른 장비의 보장 수치가 아니다.
- 생성된 Korean C 소스는 약 17.9 KB였다. 큰 외부 사전/모델을 C 라이브러리에 편입하지 않았다.
- `나는/사는/파는`류의 일부 ㄹ 탈락 분석은 엔진이 잘못된 원형을 제시할 수 있어 보존한다. 여러 독립 용언을 포함한 한 어절, 미지원 보조 용언·다른 조사 경로도 보존한다. 형태소별 정확한 원문 grapheme 역매핑은 제공하지 않는다.
- 190개 어휘와 18개 문장은 지원 범위의 회귀 데이터이다. 일반 한국어의 99% precision/coverage, 대규모 처리, 다른 운영체제에서의 실제 결과는 아직 측정하지 않았다. 원격 CI의 통과도 주장하지 않는다.
- Redis 필드 직렬화·n-gram·질의 builder·접속·native 모듈 수정은 구현하지 않았다. 후속 작업의 대상 버전, 테스트 순서와 수용 기준은 [docs/plan.md](plan.md)에 보관했다.
