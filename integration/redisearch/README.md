# Korean Snowball + Redis Search 통합 검증

대상은 Redis `dce0c76d4fc34fa4c56f1003aafbd9f6364c8fb4`와 해당 manifest의
RediSearch v8.10.0 `294c88bca92b3e686d336dc165bcf68512d91ac5`이다.
Redis 버전은 개발 버전 `8.9.241`이며 운영 릴리스 인증을 의미하지 않는다.

`apply.py`는 이 저장소의 `algorithms/korean.sbl`을 RediSearch의 기존
`deps/stemmers` 확장 경로에 복사하고 `korean` 언어 enum/문자열 매핑을 추가한다.
CMake가 RediSearch에 고정된 Snowball compiler/runtime으로 C 코드와 registry를 생성한다.
기존 Snowball submodule 전체나 다른 언어를 교체하지 않는다.
Redis 명령의 언어 이름은 `korean`(대소문자 무관)만 추가하며,
`ko`/`kor`는 libstemmer 내부 별칭이다.

`prepare_fixtures.py`는 실제 Kiwi 어댑터로 문서와 질의를 분석한다.
`check.py`는 소스 빌드한 Redis를 독립 프로세스로 시작하고 PID를 확인한 뒤,
native 원문 인덱스와 Kiwi canonical `TEXT NOSTEM` 인덱스를 비교한다.
전처리는 Redis 외부에서 수행하며 Redis 모듈에 Kiwi가 들어가지는 않는다.
질의 조합과 gram 필드는 검증용 참조 구현이며 운영 query API가 아니다.

## 재현 순서

새 디렉터리만 사용한다. 아래 `SNOWBALL_REPO`, `REDIS_WORK`는 절대 경로로 지정한다.
기존 데이터가 있는 Redis에 실행하는 스크립트가 아니다. `check.py`는 기존 RDB/포트를 거부한다.

```sh
SNOWBALL_REPO=/absolute/path/to/snowball
REDIS_WORK=/absolute/path/to/new-redis-checkout

git clone https://github.com/redis/redis.git "$REDIS_WORK"
git -C "$REDIS_WORK" checkout --detach dce0c76d4fc34fa4c56f1003aafbd9f6364c8fb4
make -C "$REDIS_WORK" modules-update redisearch MODULES_UPDATE_SHALLOW=1
python3 "$SNOWBALL_REPO/integration/redisearch/apply.py" "$REDIS_WORK/modules/redisearch/src"

# Python 3.11/3.12 환경에 examples/korean/requirements.txt를 먼저 설치한다.
python "$SNOWBALL_REPO/integration/redisearch/prepare_fixtures.py" "$REDIS_WORK/ko-fixtures.json"
cp "$SNOWBALL_REPO/integration/redisearch/check.py" "$REDIS_WORK/ko-check.py"

docker build -f "$SNOWBALL_REPO/integration/redisearch/Dockerfile.build" \
    -t snowball-ko-toolchain "$SNOWBALL_REPO/integration/redisearch"
docker run -d --name snowball-ko-repro \
    --mount "type=bind,src=$REDIS_WORK,dst=/work" snowball-ko-toolchain sleep infinity
docker exec snowball-ko-repro git config --global --add safe.directory /work
docker exec snowball-ko-repro git config --global --add safe.directory /work/modules/redisearch/src
docker exec snowball-ko-repro make build redisearch LTO=0 \
    REDISEARCH_GENERATE_HEADERS=0 INLINE_LSE_ATOMICS=0 > build.log 2>&1
docker exec snowball-ko-repro python3 /work/ko-check.py /work \
    /work/ko-fixtures.json /work/ko-results.json
```

빌드용 Docker에는 호스트 포트를 게시하지 않는다. Linux ARM64에서 검증했다.
병렬 작업을 줄이려면 실행한 것처럼 `taskset -c 0-3 make ...`를 사용한다.
패키지 저장소는 설치 시점에 따라 변할 수 있으므로 bit-for-bit 재현을 보장하지 않는다.
빌드 실패/재시도 시 로그를 새 이름으로 보존하고, 같은 checkout에서 make/cargo를 동시에 실행하지 않는다.

## upstream 테스트

`apply.py`는 native Korean RLTest와 C++ 단위 테스트도 설치한다.
컨테이너에서 RediSearch 디렉터리로 이동하여 실행한다.

```sh
curl --proto '=https' --tlsv1.2 -LsSf https://astral.sh/uv/install.sh -o /tmp/uv-install.sh
sh /tmp/uv-install.sh
export PATH="/root/.cargo/bin:/root/.local/bin:/work/src:$PATH"
SKIP_VENV_PROFILE_ACTIVATION=1 bash .install/test_deps/install_python_deps.sh
REDISEARCH_GENERATE_HEADERS=0 INLINE_LSE_ATOMICS=0 \
    ./build.sh RUN_UNIT_TESTS ENABLE_ASSERT=1 > /work/ko-unit.log 2>&1
REJSON=0 REDISEARCH_GENERATE_HEADERS=0 INLINE_LSE_ATOMICS=0 \
    ./build.sh RUN_PYTEST ENABLE_ASSERT=1 TEST_TIMEOUT=20 \
    TEST='test_korean test_language:testHashIndexLanguage test_language:testHashIndexLanguageField test_language:testTagalogLanguage test_language:testMalayLanguage test_language:testLanguageInfo test_stemmer:testHashMinStemLen test:testStemming test:testNoStem' \
    > /work/ko-flow.log 2>&1
```

모든 upstream behavioral test나 Redis Cluster를 실행한다는 뜻은 아니다.
검증 범위·실제 관측 결과·로그는 [통합 보고서](../../docs/redis-integration-results.md)에 기록한다.

## 단어별 반환 시간

5음절 이하 187개 입력을 사용한 [benchmark 코드와 원시 측정값](benchmark/README.md),
[결과 보고서](../../docs/korean-stemming-benchmark.md)를 추가했다.
