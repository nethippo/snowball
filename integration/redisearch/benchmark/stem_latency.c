/* Benchmark the exported Snowball API in the exact built RediSearch .so.
 * Redis allocators are replaced only in this isolated benchmark process.
 * No RedisModule_OnLoad is called. After warmup, zero allocator calls are required.
 */
#define _POSIX_C_SOURCE 200809L
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define MAX_WORDS 512
#define TRIALS 9
#define MIN_CALLS 2000000
struct word { char text[64], expected[64]; int bytes, chars, changed; };
static struct word words[MAX_WORDS];
static unsigned long allocs;
static volatile uint64_t sink;
static void *bm_malloc(size_t n) { ++allocs; return malloc(n); }
static void *bm_calloc(size_t n, size_t s) { ++allocs; return calloc(n, s); }
static void *bm_realloc(void *p, size_t n) { ++allocs; return realloc(p, n); }
static void bm_free(void *p) { ++allocs; free(p); }
static uint64_t ns(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts)) abort();
    return (uint64_t)ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}
static void *symbol(void *handle, const char *name) {
    void *p = dlsym(handle, name);
    if (!p) { fprintf(stderr, "%s: %s\n", name, dlerror()); exit(2); }
    return p;
}
static uint32_t rng = 0x5eed1234;
static uint32_t next_random(void) {
    rng ^= rng << 13; rng ^= rng >> 17; rng ^= rng << 5;
    return rng;
}
int main(int argc, char **argv) {
    if (argc != 3) { fprintf(stderr, "usage: %s redisearch.so corpus.tsv\n", argv[0]); return 2; }
    void *h = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!h) { fprintf(stderr, "%s\n", dlerror()); return 2; }
    *(void *(**)(size_t))symbol(h, "RedisModule_Alloc") = bm_malloc;
    *(void *(**)(size_t, size_t))symbol(h, "RedisModule_Calloc") = bm_calloc;
    *(void *(**)(void *, size_t))symbol(h, "RedisModule_Realloc") = bm_realloc;
    *(void (**)(void *))symbol(h, "RedisModule_Free") = bm_free;
    void *(*create)(const char *, const char *) = symbol(h, "sb_stemmer_new");
    const unsigned char *(*stem)(void *, const unsigned char *, int) = symbol(h, "sb_stemmer_stem");
    int (*length)(void *) = symbol(h, "sb_stemmer_length");
    void (*destroy)(void *) = symbol(h, "sb_stemmer_delete");
    FILE *in = fopen(argv[2], "r");
    if (!in) { perror("corpus"); return 2; }
    int count = 0;
    while (count < MAX_WORDS && fscanf(in, "%63s %63s %d %d", words[count].text,
           words[count].expected, &words[count].chars, &words[count].changed) == 4) {
        words[count].bytes = (int)strlen(words[count].text);
        ++count;
    }
    fclose(in);
    void *s = create("korean", "UTF_8");
    if (!s || !count) return 2;
    for (int i = 0; i < count; ++i) {
        const unsigned char *out = stem(s, (unsigned char *)words[i].text, words[i].bytes);
        if (!out || strcmp((const char *)out, words[i].expected)) {
            fprintf(stderr, "wrong output: %s\n", words[i].text); return 3;
        }
    }
    printf("{\"clock\":\"CLOCK_MONOTONIC\",\"trials\":%d,\"verified_words\":%d,\"groups\":[", TRIALS, count);
    const char *names[] = {"all", "changed", "preserved", "length_1", "length_2", "length_3", "length_4", "length_5"};
    for (int group = 0; group < 8; ++group) {
        int order[MAX_WORDS], n = 0;
        for (int i = 0; i < count; ++i) {
            if (group == 1 && !words[i].changed) continue;
            if (group == 2 && words[i].changed) continue;
            if (group >= 3 && words[i].chars != group - 2) continue;
            order[n++] = i;
        }
        if (!n) abort();
        int cycles = (MIN_CALLS + n - 1) / n;
        uint64_t calls = (uint64_t)cycles * n;
        printf("%s{\"name\":\"%s\",\"words\":%d,\"calls_per_trial\":%llu,\"trials_ns_per_call\":[", group ? "," : "", names[group], n, (unsigned long long)calls);
        for (int trial = 0; trial < TRIALS; ++trial) {
            for (int i = n - 1; i > 0; --i) {
                int j = next_random() % (i + 1), tmp = order[i]; order[i] = order[j]; order[j] = tmp;
            }
            for (int warm = 0; warm < 500; ++warm)
                for (int i = 0; i < n; ++i)
                    if (!stem(s, (unsigned char *)words[order[i]].text, words[order[i]].bytes)) abort();
            unsigned long before_allocs = allocs;
            uint64_t sum = 0, start = ns();
            for (int round = 0; round < cycles; ++round) {
                for (int i = 0; i < n; ++i) {
                    struct word *w = &words[order[i]];
                    const unsigned char *out = stem(s, (unsigned char *)w->text, w->bytes);
                    if (!out) abort();
                    sum += (uint64_t)length(s) + out[0];
                }
            }
            uint64_t elapsed = ns() - start;
            sink = sum;
            if (allocs != before_allocs) { fprintf(stderr, "unexpected timed allocation\n"); return 4; }
            printf("%s%.6f", trial ? "," : "", (double)elapsed / calls);
        }
        printf("],\"timed_allocator_calls\":0}");
    }
    printf("],\"checksum\":%llu}\n", (unsigned long long)sink);
    destroy(s);
    dlclose(h);
    return 0;
}
