# 1–5음절 단어의 반환 시간 측정

[측정 보고서](../../../docs/korean-stemming-benchmark.md).
핵심 알고리즘과 어댑터의 동작은 변경하지 않고 측정 코드를 추가했다.

`corpus.tsv`는 기존 `tests/korean/data/korean/{voc,output}.txt` 중 5음절 이하를 골랐다.
열은 입력, 예상 출력, 입력 음절 수, 변환 여부(0/1)다.
Native는 `stem_latency.c`에서 **기존 모듈 바이너리의 export된 API**를 직접 호출한다.
측정 프로세스의 allocator 포인터만 libc에 연결하고 timed allocation 0회를 검사한다.
실제 Redis 명령과 Kiwi 어댑터는 각각 다른 harness로 측정하며 결과를 혼동하지 않는다.

## Native 재현

기존 통합 checkout이 `/private/tmp/snowball-redis-integration`이고 Docker 컨테이너 이름이
`snowball-ko-build`인 현재 환경의 예이다. 파일 복사에는 저장소 root에서 실행한다.

```sh
mkdir -p /private/tmp/snowball-redis-integration/ko-benchmark
cp integration/redisearch/benchmark/stem_latency.c integration/redisearch/benchmark/corpus.tsv \
  /private/tmp/snowball-redis-integration/ko-benchmark/
docker start snowball-ko-build
docker exec snowball-ko-build gcc -std=c11 -O3 -Wall -Wextra \
  /work/ko-benchmark/stem_latency.c -ldl -o /work/ko-benchmark/stem_latency
docker exec snowball-ko-build taskset -c 0 /work/ko-benchmark/stem_latency \
  /work/modules/redisearch/redisearch.so /work/ko-benchmark/corpus.tsv \
  > native-new.json
```

다른 모듈은 symbol/allocator 계약이 다를 수 있다. 현재의 검증 SHA에서만 사용한다.
파일 로딩·정답 검증·warmup은 timed region 밖이다.
각 집합을 약 200만 회씩 9회 측정하며 다른 benchmark/build와 동시에 실행하지 않는다.

## Kiwi와 Redis 재현

```sh
# 기존 Kiwi 0.23.1 / model 0.23.0 설치 환경
PYTHONDONTWRITEBYTECODE=1 /private/tmp/snowball-korean-venv/bin/python \
  integration/redisearch/benchmark/kiwi_latency.py \
  integration/redisearch/benchmark/corpus.tsv kiwi-new.json

cp integration/redisearch/check.py /private/tmp/snowball-redis-integration/ko_check.py
cp integration/redisearch/benchmark/redis_latency.py \
  /private/tmp/snowball-redis-integration/ko-benchmark/
docker exec snowball-ko-build env PYTHONDONTWRITEBYTECODE=1 taskset -c 1 python3 \
  /work/ko-benchmark/redis_latency.py /work /work/ko-benchmark/corpus.tsv /work/ko-benchmark/redis-new.json
docker stop snowball-ko-build
```

Redis harness는 컨테이너 loopback 16391을 사용한다. 다른 listener가 있으면 실행을 거부하고,
새 subprocess의 PID를 확인한 뒤 테스트하며 자신이 시작한 Redis만 종료한다.
Native 결과의 범위는 `sb_stemmer_stem + sb_stemmer_length + checksum`이다.
개별 요청 percentile 측정은 하지 않았으며 9개의 batch 평균과 그 평균을 보고한다.
