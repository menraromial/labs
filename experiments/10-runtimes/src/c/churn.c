#define _GNU_SOURCE

/* E2, partie 3 : allocation continue à ensemble vivant fixe, référence sans ramasse-miettes.
 * Un anneau de L objets ; chaque opération alloue un objet neuf et libère le plus ancien.
 * Remplissage non chronométré, puis NB lots de B opérations chronométrés un par un. */

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

struct object { uint64_t key, a, b; };

static void allowed_cpus(char *text, size_t size) {
    char line[256];
    snprintf(text, size, "inconnu");
    FILE *f = fopen("/proc/self/status", "r");
    while (f && fgets(line, sizeof line, f))
        if (sscanf(line, "Cpus_allowed_list: %63s", text) == 1) break;
    if (f) fclose(f);
    for (char *c = text; *c; ++c) if (*c == ',') *c = ';';
}

static uint64_t monotonic_ns(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (uint64_t)t.tv_sec * UINT64_C(1000000000) + (uint64_t)t.tv_nsec;
}

static long peak_rss_kib(void) {
    char line[256];
    long value = -1;
    FILE *f = fopen("/proc/self/status", "r");
    while (f && fgets(line, sizeof line, f))
        if (sscanf(line, "VmHWM: %ld kB", &value) == 1) break;
    if (f) fclose(f);
    return value;
}

static struct object *make(uint64_t i) {
    struct object *o = malloc(sizeof *o);
    if (!o) abort();
    o->key = i;
    o->a = 2 * i + 1;
    o->b = 3 * i + 2;
    return o;
}

int main(int argc, char **argv) {
    const char *output = NULL, *meta = NULL, *mode = "c";
    unsigned long run_id = 0, live_log2 = 20, batch_log2 = 13, batches = 1024;
    for (int i = 1; i + 1 < argc; i += 2) {
        if (!strcmp(argv[i], "--output")) output = argv[i + 1];
        else if (!strcmp(argv[i], "--meta")) meta = argv[i + 1];
        else if (!strcmp(argv[i], "--mode")) mode = argv[i + 1];
        else if (!strcmp(argv[i], "--run-id")) run_id = strtoul(argv[i + 1], NULL, 10);
        else if (!strcmp(argv[i], "--live-log2")) live_log2 = strtoul(argv[i + 1], NULL, 10);
        else if (!strcmp(argv[i], "--batch-log2")) batch_log2 = strtoul(argv[i + 1], NULL, 10);
        else if (!strcmp(argv[i], "--batches")) batches = strtoul(argv[i + 1], NULL, 10);
    }
    if (!output || !meta || run_id == 0) {
        fprintf(stderr, "usage : churn --output CSV --meta CSV --run-id N --mode M\n");
        return EXIT_FAILURE;
    }
    size_t live = (size_t)1 << live_log2, batch = (size_t)1 << batch_log2;
    struct object **ring = malloc(live * sizeof *ring);
    uint64_t *elapsed = malloc(batches * sizeof *elapsed);
    if (!ring || !elapsed) return EXIT_FAILURE;
    uint64_t i = 0;
    for (; i < live; ++i) ring[i] = make(i);

    uint64_t start = monotonic_ns();
    for (unsigned long k = 0; k < batches; ++k) {
        uint64_t t0 = monotonic_ns();
        for (size_t j = 0; j < batch; ++j, ++i) {
            size_t slot = i & (live - 1);
            free(ring[slot]);
            ring[slot] = make(i);
        }
        elapsed[k] = monotonic_ns() - t0;
    }
    uint64_t total = monotonic_ns() - start;
    uint64_t checksum = 0;
    for (size_t s = 0; s < live; ++s) checksum += ring[s]->key + ring[s]->a + ring[s]->b;

    FILE *out = fopen(output, "w");
    if (!out) return EXIT_FAILURE;
    fprintf(out, "run_id,mode,batch,operations,elapsed_ns\n");
    for (unsigned long k = 0; k < batches; ++k)
        fprintf(out, "%lu,%s,%lu,%zu,%" PRIu64 "\n", run_id, mode, k, batch, elapsed[k]);
    FILE *m = fopen(meta, "w");
    if (!m || fclose(out) != 0) return EXIT_FAILURE;
    fprintf(m, "run_id,mode,runtime,total_ns,operations,checksum,gc_count,gc_pause_ns,peak_rss_kib,cpus_allowed\n");
    char cpus_allowed[64];
    allowed_cpus(cpus_allowed, sizeof cpus_allowed);
    fprintf(m, "%lu,%s,glibc malloc,%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",0,0,%ld,%s\n", run_id, mode, total,
            (uint64_t)batches * batch, checksum, peak_rss_kib(), cpus_allowed);
    return fclose(m) == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
