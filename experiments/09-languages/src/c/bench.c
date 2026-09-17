#define _GNU_SOURCE

/* E1, version C. Même plan de mesure, mêmes données et mêmes boucles « contrôlées »
 * que les versions Rust, Go et Python (voir README, section 4). */

#include <errno.h>
#include <inttypes.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define NOINLINE __attribute__((noinline))
#define K UINT64_C(0x9e3779b97f4a7c15)
#define TABLE_BITS 17
#define TABLE_SIZE (1u << TABLE_BITS)

/* ------------------------------------------------------------------ charges contrôlées */

static NOINLINE uint64_t hash_chain(const uint64_t *u, size_t n, uint64_t h) {
    for (size_t i = 0; i < n; ++i) h = (h ^ u[i]) * K;
    return h;
}

static NOINLINE double dot(const double *a, const double *b, size_t n) {
    double s = 0.0;
    for (size_t i = 0; i < n; ++i) s += a[i] * b[i];
    return s;
}

/* Table à adressage ouvert : clé + 1 stockée (0 = vide), sondage linéaire. */
static NOINLINE void count_table(const uint32_t *keys, size_t n, uint32_t *slot_keys, uint32_t *slot_counts) {
    for (size_t i = 0; i < n; ++i) {
        uint32_t stored = keys[i] + 1;
        uint32_t slot = (uint32_t)(((uint64_t)stored * K) >> (64 - TABLE_BITS));
        while (slot_keys[slot] != 0 && slot_keys[slot] != stored) slot = (slot + 1) & (TABLE_SIZE - 1);
        slot_keys[slot] = stored;
        slot_counts[slot] += 1;
    }
}

static uint64_t table_checksum(const uint32_t *slot_keys, const uint32_t *slot_counts) {
    uint64_t sum = 0;
    for (size_t s = 0; s < TABLE_SIZE; ++s)
        if (slot_keys[s] != 0) sum += (uint64_t)slot_counts[s] * ((uint64_t)slot_keys[s] * K);
    return sum;
}

/* ------------------------------------------------------------------ outils */

static uint64_t monotonic_ns(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (uint64_t)t.tv_sec * UINT64_C(1000000000) + (uint64_t)t.tv_nsec;
}

static uint64_t splitmix64(uint64_t *state) {
    uint64_t z = (*state += K);
    z = (z ^ (z >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
    z = (z ^ (z >> 27)) * UINT64_C(0x94d049bb133111eb);
    return z ^ (z >> 31);
}

static uint64_t xorshift(uint64_t *state) {
    *state ^= *state >> 12;
    *state ^= *state << 25;
    *state ^= *state >> 27;
    return *state * UINT64_C(2685821657736338717);
}

static uint64_t parse_u64(const char *text) {
    char *end = NULL;
    errno = 0;
    unsigned long long value = strtoull(text, &end, 10);
    if (errno || end == text || *end) {
        fprintf(stderr, "entier invalide : %s\n", text);
        exit(EXIT_FAILURE);
    }
    return value;
}

static long peak_rss_kib(void) {
    char line[256];
    long value = -1;
    FILE *f = fopen("/proc/self/status", "r");
    if (!f) return -1;
    while (fgets(line, sizeof line, f))
        if (sscanf(line, "VmHWM: %ld kB", &value) == 1) break;
    fclose(f);
    return value;
}

enum workload { W_HASH, W_DOT, W_COUNT };
struct measure { const char *workload, *variant; enum workload kind; int passes; };

int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "--noop") == 0) return 0;

    const char *input = NULL, *output = NULL, *meta_path = NULL, *generate = NULL, *build = "c";
    uint64_t run_id = 0, seed = 20260922, rounds = 11, warmup = 1, scale = 0, count = 0;
    for (int i = 1; i + 1 < argc; i += 2) {
        const char *o = argv[i], *v = argv[i + 1];
        if (!strcmp(o, "--input")) input = v;
        else if (!strcmp(o, "--output")) output = v;
        else if (!strcmp(o, "--meta")) meta_path = v;
        else if (!strcmp(o, "--generate")) generate = v;
        else if (!strcmp(o, "--build")) build = v;
        else if (!strcmp(o, "--run-id")) run_id = parse_u64(v);
        else if (!strcmp(o, "--seed")) seed = parse_u64(v);
        else if (!strcmp(o, "--rounds")) rounds = parse_u64(v);
        else if (!strcmp(o, "--warmup-rounds")) warmup = parse_u64(v);
        else if (!strcmp(o, "--scale-log2")) scale = parse_u64(v);
        else if (!strcmp(o, "--count")) count = parse_u64(v);
        else {
            fprintf(stderr, "option inconnue : %s\n", o);
            return EXIT_FAILURE;
        }
    }

    /* Données d'entrée communes : count entiers de 64 bits (SplitMix64), petit-boutistes. */
    if (generate) {
        FILE *f = fopen(generate, "wb");
        uint64_t state = seed;
        for (uint64_t i = 0; f && i < count; ++i) {
            uint64_t x = splitmix64(&state);
            if (fwrite(&x, sizeof x, 1, f) != 1) return EXIT_FAILURE;
        }
        return f && fclose(f) == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
    }
    if (!input || !output || !meta_path || run_id == 0 || warmup >= rounds || scale > 12) {
        fprintf(stderr, "usage : bench --noop | --generate FICHIER --count N --seed S | --input FICHIER "
                        "--output CSV --meta CSV --run-id N --build NOM [--seed S] [--rounds N] "
                        "[--warmup-rounds N] [--scale-log2 S]\n");
        return EXIT_FAILURE;
    }

    size_t n_hash = (size_t)1 << (20 - scale), n_dot = n_hash, n_count = (size_t)1 << (22 - scale);
    size_t n_total = n_count > 2 * n_dot ? n_count : 2 * n_dot;
    uint64_t *u = malloc(n_total * sizeof *u);
    double *a = malloc(n_dot * sizeof *a), *b = malloc(n_dot * sizeof *b);
    uint32_t *keys = malloc(n_count * sizeof *keys);
    uint32_t *slot_keys = calloc(TABLE_SIZE, sizeof *slot_keys), *slot_counts = calloc(TABLE_SIZE, sizeof *slot_counts);
    FILE *f = fopen(input, "rb");
    if (!u || !a || !b || !keys || !slot_keys || !slot_counts || !f || fread(u, sizeof *u, n_total, f) != n_total) {
        fprintf(stderr, "lecture de %s impossible\n", input);
        return EXIT_FAILURE;
    }
    fclose(f);

    /* Dérivations, identiques dans les quatre langages. */
    uint64_t keys_sum = 0;
    for (size_t i = 0; i < n_dot; ++i) {
        a[i] = (double)(u[i] >> 11) * 0x1.0p-53;
        b[i] = (double)(u[n_dot + i] >> 11) * 0x1.0p-53;
    }
    for (size_t i = 0; i < n_count; ++i) {
        keys[i] = (uint32_t)(((u[i] >> 48) * ((u[i] >> 32) & 0xFFFF)) >> 16);
        keys_sum += keys[i];
    }

    const struct measure measures[] = {
        {"hash_chain", "control", W_HASH, 1},
        {"hash_chain", "control_bis", W_HASH, 1},
        {"hash_chain", "control_double", W_HASH, 2},
        {"dot", "control", W_DOT, 1},
        {"count", "control", W_COUNT, 1},
    };
    size_t m = sizeof measures / sizeof measures[0];
    size_t total = m * rounds;
    size_t *order = malloc(total * sizeof *order);
    uint64_t *elapsed = malloc(total * sizeof *elapsed), *result = malloc(total * sizeof *result);
    int *cpu_before = malloc(total * sizeof *cpu_before), *cpu_after = malloc(total * sizeof *cpu_after);
    uint64_t state = seed ^ (run_id * K);
    if (state == 0) state = 1;
    for (size_t r = 0; r < rounds; ++r) {
        size_t *slice = order + r * m;
        for (size_t j = 0; j < m; ++j) slice[j] = j;
        for (size_t j = m; j > 1; --j) {
            size_t other = (size_t)(xorshift(&state) % j), t = slice[j - 1];
            slice[j - 1] = slice[other];
            slice[other] = t;
        }
    }

    int first_cpu = sched_getcpu();
    for (size_t s = 0; s < total; ++s) {
        const struct measure *me = &measures[order[s]];
        if (me->kind == W_COUNT) {   /* table remise à zéro hors chronométrage */
            memset(slot_keys, 0, TABLE_SIZE * sizeof *slot_keys);
            memset(slot_counts, 0, TABLE_SIZE * sizeof *slot_counts);
        }
        cpu_before[s] = sched_getcpu();
        uint64_t t0 = monotonic_ns(), r = 0;
        switch (me->kind) {
        case W_HASH:
            r = hash_chain(u, n_hash, 0);
            if (me->passes == 2) r = hash_chain(u, n_hash, r);
            break;
        case W_DOT: {
            double d = dot(a, b, n_dot);
            memcpy(&r, &d, sizeof r);
            break;
        }
        case W_COUNT:
            count_table(keys, n_count, slot_keys, slot_counts);
            break;
        }
        uint64_t t1 = monotonic_ns();
        cpu_after[s] = sched_getcpu();
        if (me->kind == W_COUNT) r = table_checksum(slot_keys, slot_counts);
        elapsed[s] = t1 - t0;
        result[s] = r;
    }

    FILE *out = fopen(output, "w");
    if (!out) return EXIT_FAILURE;
    fprintf(out, "run_id,build,seed,sample,round,phase,position,workload,variant,elements,passes,elapsed_ns,result,"
                 "gc_delta,cpu_before,cpu_after\n");
    for (size_t s = 0; s < total; ++s) {
        const struct measure *me = &measures[order[s]];
        size_t elements = me->kind == W_HASH ? n_hash : me->kind == W_DOT ? n_dot : n_count;
        fprintf(out, "%" PRIu64 ",%s,%" PRIu64 ",%zu,%zu,%s,%zu,%s,%s,%zu,%d,%" PRIu64 ",%016" PRIx64 ",0,%d,%d\n",
                run_id, build, seed, s, s / m, s / m < warmup ? "warmup" : "measure", s % m, me->workload,
                me->variant, elements, me->passes, elapsed[s], result[s], cpu_before[s], cpu_after[s]);
    }
    FILE *meta = fopen(meta_path, "w");
    if (!meta || fclose(out) != 0) return EXIT_FAILURE;
    fprintf(meta, "run_id,build,runtime,first_cpu,peak_rss_kib,keys_sum,gc_total,jit,gil\n");
    fprintf(meta, "%" PRIu64 ",%s,%s,%d,%ld,%" PRIu64 ",0,none,none\n", run_id, build, __VERSION__, first_cpu,
            peak_rss_kib(), keys_sum);
    return fclose(meta) == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
