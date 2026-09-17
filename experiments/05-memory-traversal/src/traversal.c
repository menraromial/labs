#define _GNU_SOURCE

#include <errno.h>
#include <inttypes.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <time.h>

#if defined(__GNUC__) || defined(__clang__)
#define NOINLINE __attribute__((noinline))
#else
#define NOINLINE
#endif

#define GOLDEN UINT64_C(0x9e3779b97f4a7c15)

/* Entier de 128 bits (extension GCC et Clang), pour le produit de fast_range. */
__extension__ typedef unsigned __int128 u128;
#define LINE_ELEMENTS 8   /* une ligne de cache de 64 octets contient 8 éléments de 8 octets */

/* ------------------------------------------------------------------ indices */

/* Mélange sans mémoire : l'indice d'un accès ne dépend que de son rang, jamais
 * d'une valeur lue. Les accès aléatoires restent donc indépendants entre eux. */
static inline uint64_t mix(uint64_t salt, uint64_t j) {
    uint64_t x = salt + j * GOLDEN;
    x ^= x >> 31;
    x *= UINT64_C(0xbf58476d1ce4e5b9);
    x ^= x >> 29;
    return x;
}

/* Réduit x à [0, n) sans division : partie haute du produit 128 bits (Lemire). */
static inline uint64_t fast_range(uint64_t x, uint64_t n) {
    return (uint64_t)(((u128)x * n) >> 64);
}

/* ------------------------------------------------------------------ parcours */

/* Pas constant : l'élément suivant est `stride` éléments plus loin, modulo n.
 * stride = 1 est le parcours séquentiel. Précondition : stride < n. */
static NOINLINE uint64_t walk_stride(const uint64_t *data, uint64_t n, uint64_t stride,
                                     uint64_t start, uint64_t accesses) {
    uint64_t sum = 0, index = start;
    for (uint64_t j = 0; j < accesses; ++j) {
        sum += data[index];
        index += stride;
        if (index >= n) index -= n;
    }
    return sum;
}

/* Un élément tiré au hasard par accès. */
static NOINLINE uint64_t walk_random(const uint64_t *data, uint64_t n, uint64_t salt,
                                     uint64_t accesses) {
    uint64_t sum = 0;
    for (uint64_t j = 0; j < accesses; ++j) {
        sum += data[fast_range(mix(salt, j), n)];
    }
    return sum;
}

/* Deux éléments voisins par accès, dans une ligne tirée au hasard :
 * offset 3 : octets 24 à 39, dans la même ligne de cache ;
 * offset 7 : octets 56 à 71, à cheval sur la ligne suivante. */
static NOINLINE uint64_t walk_pair(const uint64_t *data, uint64_t lines, uint64_t offset,
                                   uint64_t salt, uint64_t accesses) {
    uint64_t sum = 0;
    for (uint64_t j = 0; j < accesses; ++j) {
        uint64_t base = fast_range(mix(salt, j), lines - 1) * LINE_ELEMENTS + offset;
        sum += data[base] + data[base + 1];
    }
    return sum;
}

/* ------------------------------------------------------------------ références */

/* Réimplémentations directes, avec division et produit explicite, pour vérifier
 * chaque résultat hors chronométrage. */
static uint64_t reference_stride(const uint64_t *data, uint64_t n, uint64_t stride,
                                 uint64_t start, uint64_t accesses) {
    uint64_t sum = 0;
    for (uint64_t j = 0; j < accesses; ++j) {
        u128 position = (u128)start + (u128)j * stride;
        sum += data[(uint64_t)(position % n)];
    }
    return sum;
}

static uint64_t reference_random(const uint64_t *data, uint64_t n, uint64_t salt,
                                 uint64_t accesses) {
    uint64_t sum = 0;
    for (uint64_t j = 0; j < accesses; ++j) {
        uint64_t x = salt + j * GOLDEN;
        x = (x ^ (x >> 31)) * UINT64_C(0xbf58476d1ce4e5b9);
        x ^= x >> 29;
        u128 wide = (u128)x * n;
        sum += data[(uint64_t)(wide >> 64)];
    }
    return sum;
}

static uint64_t reference_pair(const uint64_t *data, uint64_t lines, uint64_t offset,
                               uint64_t salt, uint64_t accesses) {
    uint64_t sum = 0;
    for (uint64_t j = 0; j < accesses; ++j) {
        uint64_t x = salt + j * GOLDEN;
        x = (x ^ (x >> 31)) * UINT64_C(0xbf58476d1ce4e5b9);
        x ^= x >> 29;
        uint64_t line = (uint64_t)(((u128)x * (lines - 1)) >> 64);
        sum += data[line * LINE_ELEMENTS + offset];
        sum += data[line * LINE_ELEMENTS + offset + 1];
    }
    return sum;
}

/* ------------------------------------------------------------------ plan */

enum pattern { PATTERN_STRIDE, PATTERN_RANDOM, PATTERN_PAIR };

struct measure {
    const char *label;
    enum pattern pattern;
    uint64_t parameter;        /* pas, ou décalage dans la ligne */
    uint64_t access_factor;    /* 2 pour le contrôle positif */
};

static const struct measure MEASURES[] = {
    {"stride_1", PATTERN_STRIDE, 1, 1},
    {"stride_1_bis", PATTERN_STRIDE, 1, 1},
    {"stride_1_double", PATTERN_STRIDE, 1, 2},
    {"stride_17", PATTERN_STRIDE, 17, 1},
    {"stride_513", PATTERN_STRIDE, 513, 1},
    {"stride_4097", PATTERN_STRIDE, 4097, 1},
    {"random", PATTERN_RANDOM, 0, 1},
    {"pair_same_line", PATTERN_PAIR, 3, 1},
    {"pair_split_line", PATTERN_PAIR, 7, 1},
};
#define MEASURE_COUNT (sizeof(MEASURES) / sizeof(MEASURES[0]))

struct sample {
    uint32_t round, position, measure, size_index;
    uint64_t start, salt, accesses, elapsed_ns, result;
    int cpu_before, cpu_after;
};

/* ------------------------------------------------------------------ utilitaires */

static uint64_t monotonic_ns(void) {
    struct timespec value;
    if (clock_gettime(CLOCK_MONOTONIC, &value) != 0) {
        perror("clock_gettime");
        exit(EXIT_FAILURE);
    }
    return (uint64_t)value.tv_sec * UINT64_C(1000000000) + (uint64_t)value.tv_nsec;
}

static uint64_t splitmix64(uint64_t value) {
    value += GOLDEN;
    value = (value ^ (value >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
    value = (value ^ (value >> 27)) * UINT64_C(0x94d049bb133111eb);
    return value ^ (value >> 31);
}

static uint64_t random_next(uint64_t *state) {
    *state ^= *state >> 12;
    *state ^= *state << 25;
    *state ^= *state >> 27;
    return *state * UINT64_C(2685821657736338717);
}

static uint64_t parse_u64(const char *text, const char *option) {
    char *end = NULL;
    errno = 0;
    unsigned long long value = strtoull(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || text[0] == '-') {
        fprintf(stderr, "invalid value for %s: %s\n", option, text);
        exit(EXIT_FAILURE);
    }
    return (uint64_t)value;
}

static uint64_t effective_stride(uint64_t stride, uint64_t n) {
    uint64_t reduced = stride % n;
    return reduced ? reduced : 1;
}

static uint64_t run_measure(const struct measure *m, const uint64_t *data, uint64_t n,
                            uint64_t start, uint64_t salt, uint64_t accesses, int reference) {
    switch (m->pattern) {
    case PATTERN_STRIDE:
        return reference ? reference_stride(data, n, effective_stride(m->parameter, n), start, accesses)
                         : walk_stride(data, n, effective_stride(m->parameter, n), start, accesses);
    case PATTERN_RANDOM:
        return reference ? reference_random(data, n, salt, accesses)
                         : walk_random(data, n, salt, accesses);
    case PATTERN_PAIR:
        return reference ? reference_pair(data, n / LINE_ELEMENTS, m->parameter, salt, accesses)
                         : walk_pair(data, n / LINE_ELEMENTS, m->parameter, salt, accesses);
    }
    return 0;
}

static int self_test(void) {
    static uint64_t data[4096];
    for (size_t i = 0; i < 4096; ++i) data[i] = splitmix64(i);
    const uint64_t sizes[] = {16, 64, 512, 4096};
    for (size_t s = 0; s < 4; ++s) {
        for (size_t k = 0; k < MEASURE_COUNT; ++k) {
            for (uint64_t start = 0; start < sizes[s]; start += sizes[s] / 4) {
                uint64_t salt = splitmix64(start + k), accesses = 5000;
                if (run_measure(&MEASURES[k], data, sizes[s], start, salt, accesses, 0) !=
                    run_measure(&MEASURES[k], data, sizes[s], start, salt, accesses, 1)) {
                    fprintf(stderr, "self-test: %s differs for n=%" PRIu64 "\n", MEASURES[k].label, sizes[s]);
                    return EXIT_FAILURE;
                }
            }
        }
    }
    puts("self-test: OK");
    return EXIT_SUCCESS;
}

/* Taille de la mémoire anonyme adossée à des pages géantes, lue dans /proc. */
static long anon_huge_pages_kb(void) {
    FILE *file = fopen("/proc/self/smaps_rollup", "r");
    char line[256];
    long value = -1;
    if (file == NULL) return -1;
    while (fgets(line, sizeof(line), file) != NULL) {
        if (sscanf(line, "AnonHugePages: %ld kB", &value) == 1) break;
    }
    fclose(file);
    return value;
}

static void read_frequency(int cpu, char *buffer, size_t length) {
    char path[128];
    snprintf(path, sizeof(path), "/sys/devices/system/cpu/cpu%d/cpufreq/scaling_cur_freq", cpu);
    FILE *file = fopen(path, "r");
    if (file == NULL || fgets(buffer, (int)length, file) == NULL) buffer[0] = '\0';
    if (file != NULL) fclose(file);
    buffer[strcspn(buffer, "\n")] = '\0';
}

int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "--self-test") == 0) return self_test();

    const char *output_path = NULL, *meta_path = NULL, *core = "inconnu";
    uint64_t run_id = 0, seed = UINT64_C(20260918), rounds = 9, warmup_rounds = 1;
    uint64_t min_log2 = 12, max_log2 = 28, accesses_log2 = 20;
    for (int i = 1; i + 1 < argc; i += 2) {
        if (strcmp(argv[i], "--output") == 0) output_path = argv[i + 1];
        else if (strcmp(argv[i], "--meta") == 0) meta_path = argv[i + 1];
        else if (strcmp(argv[i], "--core") == 0) core = argv[i + 1];
        else if (strcmp(argv[i], "--run-id") == 0) run_id = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--seed") == 0) seed = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--rounds") == 0) rounds = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--warmup-rounds") == 0) warmup_rounds = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--min-log2") == 0) min_log2 = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--max-log2") == 0) max_log2 = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--accesses-log2") == 0) accesses_log2 = parse_u64(argv[i + 1], argv[i]);
        else {
            fprintf(stderr, "unknown option %s\n", argv[i]);
            return EXIT_FAILURE;
        }
    }
    if (argc % 2 == 0 || output_path == NULL || meta_path == NULL || run_id == 0 || rounds == 0 ||
        warmup_rounds >= rounds || min_log2 < 10 || min_log2 > max_log2 || max_log2 > 32 ||
        accesses_log2 > 30) {
        fprintf(stderr, "usage: %s --self-test | --output FILE --meta FILE --run-id N [--core LABEL] "
                        "[--seed N] [--rounds N] [--warmup-rounds N] [--min-log2 N] [--max-log2 N] "
                        "[--accesses-log2 N]\n", argv[0]);
        return EXIT_FAILURE;
    }

    /* Tailles en octets : 2^k et 3 × 2^(k-1), par demi-octave. Toutes multiples de 64. */
    uint64_t sizes[64];
    size_t size_count = 0;
    for (uint64_t k = min_log2; k <= max_log2; ++k) {
        sizes[size_count++] = UINT64_C(1) << k;
        if (k < max_log2) sizes[size_count++] = UINT64_C(3) << (k - 1);
    }
    uint64_t max_bytes = sizes[size_count - 1];
    uint64_t base_accesses = UINT64_C(1) << accesses_log2;

    /* Un seul tableau, aligné sur une page ; les petites tailles en utilisent le début.
     * MADV_NOHUGEPAGE ne concerne que ce processus : pages de 4 Kio, réglage global inchangé. */
    uint64_t *data = aligned_alloc(4096, max_bytes);
    size_t sample_count = MEASURE_COUNT * size_count * (size_t)rounds;
    struct sample *samples = calloc(sample_count, sizeof(*samples));
    if (data == NULL || samples == NULL) {
        perror("allocation");
        return EXIT_FAILURE;
    }
    int advice = madvise(data, max_bytes, MADV_NOHUGEPAGE);
    for (uint64_t i = 0; i < max_bytes / 8; ++i) data[i] = splitmix64(seed + i);   /* touche toutes les pages */

    /* Plan : dans chaque tour, les couples (parcours, taille) sont permutés ;
     * départ et graine du mélange tirés pour chaque échantillon. */
    uint64_t state = seed ^ (run_id * GOLDEN);
    if (state == 0) state = 1;
    size_t per_round = MEASURE_COUNT * size_count;
    for (uint32_t round = 0; round < rounds; ++round) {
        struct sample *slice = samples + (size_t)round * per_round;
        for (size_t j = 0; j < per_round; ++j) {
            slice[j] = (struct sample){.round = round, .measure = (uint32_t)(j % MEASURE_COUNT),
                                       .size_index = (uint32_t)(j / MEASURE_COUNT)};
        }
        for (size_t j = per_round; j > 1; --j) {
            size_t other = (size_t)(random_next(&state) % j);
            struct sample temporary = slice[j - 1];
            slice[j - 1] = slice[other];
            slice[other] = temporary;
        }
        for (size_t j = 0; j < per_round; ++j) {
            uint64_t n = sizes[slice[j].size_index] / 8;
            slice[j].position = (uint32_t)j;
            slice[j].start = random_next(&state) % n;
            slice[j].salt = random_next(&state);
            slice[j].accesses = base_accesses * MEASURES[slice[j].measure].access_factor;
        }
    }

    long huge_kb = anon_huge_pages_kb();
    int first_cpu = sched_getcpu();
    char frequency_before[32], frequency_after[32];
    read_frequency(first_cpu, frequency_before, sizeof(frequency_before));
    struct rusage usage_before, usage_after;
    getrusage(RUSAGE_SELF, &usage_before);

    for (size_t i = 0; i < sample_count; ++i) {
        struct sample *s = &samples[i];
        const struct measure *m = &MEASURES[s->measure];
        uint64_t n = sizes[s->size_index] / 8;
        s->cpu_before = sched_getcpu();
        uint64_t before = monotonic_ns();
        uint64_t result = run_measure(m, data, n, s->start, s->salt, s->accesses, 0);
        uint64_t after = monotonic_ns();
        s->cpu_after = sched_getcpu();
        s->elapsed_ns = after - before;
        s->result = result;
    }

    getrusage(RUSAGE_SELF, &usage_after);
    read_frequency(first_cpu, frequency_after, sizeof(frequency_after));

    /* Vérification de chaque résultat par la référence, après toutes les mesures. */
    FILE *file = fopen(output_path, "w");
    if (file == NULL) {
        perror(output_path);
        return EXIT_FAILURE;
    }
    fprintf(file, "run_id,core,seed,sample,round,phase,position,label,bytes,accesses,start,salt,"
                  "elapsed_ns,cpu_before,cpu_after,result,expected\n");
    int invalid = 0;
    for (size_t i = 0; i < sample_count; ++i) {
        const struct sample *s = &samples[i];
        const struct measure *m = &MEASURES[s->measure];
        uint64_t n = sizes[s->size_index] / 8;
        uint64_t expected = run_measure(m, data, n, s->start, s->salt, s->accesses, 1);
        invalid += s->result != expected;
        fprintf(file,
                "%" PRIu64 ",%s,%" PRIu64 ",%zu,%" PRIu32 ",%s,%" PRIu32 ",%s,%" PRIu64 ",%" PRIu64
                ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%d,%d,%" PRIu64 ",%" PRIu64 "\n",
                run_id, core, seed, i, s->round, s->round < warmup_rounds ? "warmup" : "measure",
                s->position, m->label, sizes[s->size_index], s->accesses, s->start, s->salt,
                s->elapsed_ns, s->cpu_before, s->cpu_after, s->result, expected);
    }
    int status = fclose(file) == 0 ? EXIT_SUCCESS : EXIT_FAILURE;

    FILE *meta = fopen(meta_path, "w");
    if (meta == NULL) {
        perror(meta_path);
        return EXIT_FAILURE;
    }
    fprintf(meta, "run_id,core,first_cpu,madvise_nohugepage,anon_huge_pages_kb,frequency_before_khz,"
                  "frequency_after_khz,minor_faults,major_faults,voluntary_switches,"
                  "involuntary_switches,invalid_samples\n");
    fprintf(meta, "%" PRIu64 ",%s,%d,%d,%ld,%s,%s,%ld,%ld,%ld,%ld,%d\n", run_id, core, first_cpu,
            advice == 0, huge_kb, frequency_before, frequency_after,
            usage_after.ru_minflt - usage_before.ru_minflt, usage_after.ru_majflt - usage_before.ru_majflt,
            usage_after.ru_nvcsw - usage_before.ru_nvcsw, usage_after.ru_nivcsw - usage_before.ru_nivcsw,
            invalid);
    if (fclose(meta) != 0) status = EXIT_FAILURE;
    free(samples);
    free(data);
    if (invalid != 0) {
        fprintf(stderr, "%d résultats inexacts : les mesures ne sont pas valides\n", invalid);
        return EXIT_FAILURE;
    }
    return status;
}
