#define _GNU_SOURCE

#include <errno.h>
#include <inttypes.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <time.h>

#include "kernels.h"

#if defined(__GNUC__) || defined(__clang__)
#define NOINLINE __attribute__((noinline))
#else
#define NOINLINE
#endif

#define BRANCH_N ((size_t)1 << 16)
#define DEPENDENCY_N ((size_t)1 << 16)
#define DEPENDENCY_CALLS UINT64_C(64)
#define SMALL_TARGET UINT64_C(1) << 20
#define THRESHOLD (UINT64_C(1) << 63)

/* ------------------------------------------------------------------ noyaux */

enum expectation { EXPECT_CHAIN, EXPECT_SPLIT, EXPECT_SUM, EXPECT_TWICE, EXPECT_SUM_IF, EXPECT_COUNT };

struct kernel {
    const char *name;
    kernel_fn fn;
    enum expectation expect;
    int writes_output;
};

static const struct kernel KERNELS[] = {
    {"chain_xor_mul", chain_xor_mul, EXPECT_CHAIN, 0},
    {"split_xor_mul", split_xor_mul, EXPECT_SPLIT, 0},
    {"sum_one", sum_one, EXPECT_SUM, 0},
    {"sum_four", sum_four, EXPECT_SUM, 0},
    {"sum_twice", sum_twice, EXPECT_TWICE, 0},
    {"sum_if", sum_if, EXPECT_SUM_IF, 0},
    {"filter_copy", filter_copy, EXPECT_COUNT, 1},
    {"filter_copy_mask", filter_copy_mask, EXPECT_COUNT, 1},
};
enum { K_CHAIN, K_SPLIT, K_SUM_ONE, K_SUM_FOUR, K_SUM_TWICE, K_SUM_IF, K_FILTER, K_FILTER_MASK };

/* ------------------------------------------------------------------ jeux de données */

/* Jeux des branchements : même taille, part exacte d'éléments >= seuil. */
struct dataset {
    const char *name;
    uint32_t per_mille;   /* part des éléments retenus, en millièmes */
    enum { ORDER_SHUFFLED, ORDER_SORTED, ORDER_ALTERNATING } order;
};

static const struct dataset BRANCH_SETS[] = {
    {"p000", 0, ORDER_SHUFFLED},   {"p100", 100, ORDER_SHUFFLED}, {"p250", 250, ORDER_SHUFFLED},
    {"p500", 500, ORDER_SHUFFLED}, {"p750", 750, ORDER_SHUFFLED}, {"p900", 900, ORDER_SHUFFLED},
    {"p1000", 1000, ORDER_SHUFFLED}, {"p500_sorted", 500, ORDER_SORTED},
    {"p500_alternating", 500, ORDER_ALTERNATING},
};
#define BRANCH_SET_COUNT (sizeof(BRANCH_SETS) / sizeof(BRANCH_SETS[0]))

static const size_t SMALL_SIZES[] = {1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128,
                                     192, 256, 384, 512, 768, 1024};
#define SMALL_SIZE_COUNT (sizeof(SMALL_SIZES) / sizeof(SMALL_SIZES[0]))

/* ------------------------------------------------------------------ plan */

enum part { PART_DEPENDENCY, PART_BRANCH, PART_SMALL };
static const char *const PART_NAMES[] = {"dependency", "branch", "small"};

struct measure {
    enum part part;
    uint32_t kernel;
    const char *label;
    uint32_t dataset;   /* indice dans BRANCH_SETS pour la partie branch */
    size_t n;
    uint64_t calls;
};

struct sample {
    uint32_t round;
    uint32_t position;
    uint32_t measure;
    uint64_t elapsed_ns;
    uint64_t result;
    uint64_t expected;
    int output_ok;
    int cpu_before;
    int cpu_after;
};

static size_t build_measures(struct measure *out) {
    size_t count = 0;
    static const struct { uint32_t kernel; const char *label; } dependency[] = {
        {K_CHAIN, "chain_xor_mul"}, {K_SPLIT, "split_xor_mul"}, {K_SUM_ONE, "sum_one"},
        {K_SUM_ONE, "sum_one_bis"}, {K_SUM_FOUR, "sum_four"}, {K_SUM_TWICE, "sum_twice"},
    };
    for (size_t i = 0; i < sizeof(dependency) / sizeof(dependency[0]); ++i) {
        out[count++] = (struct measure){PART_DEPENDENCY, dependency[i].kernel, dependency[i].label,
                                        0, DEPENDENCY_N, DEPENDENCY_CALLS};
    }
    static const uint32_t branch_kernels[] = {K_SUM_IF, K_FILTER, K_FILTER_MASK};
    for (size_t k = 0; k < 3; ++k) {
        for (uint32_t d = 0; d < BRANCH_SET_COUNT; ++d) {
            out[count++] = (struct measure){PART_BRANCH, branch_kernels[k],
                                            KERNELS[branch_kernels[k]].name, d, BRANCH_N, 1};
        }
    }
    for (size_t s = 0; s < SMALL_SIZE_COUNT; ++s) {
        out[count++] = (struct measure){PART_SMALL, K_SUM_ONE, "sum_one", 0, SMALL_SIZES[s],
                                        (SMALL_TARGET) / SMALL_SIZES[s]};
    }
    return count;
}

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
    value += UINT64_C(0x9e3779b97f4a7c15);
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

static int compare_u64(const void *left, const void *right) {
    uint64_t a = *(const uint64_t *)left, b = *(const uint64_t *)right;
    return (a > b) - (a < b);
}

/* Références écrites dans le harnais, indépendantes du code des noyaux. */
static uint64_t reference(enum expectation expect, const uint64_t *data, size_t n) {
    uint64_t value = 0;
    for (size_t i = 0; i < n; ++i) {
        switch (expect) {
        case EXPECT_CHAIN: value = (value ^ data[i]) * KERNEL_MULTIPLIER; break;
        case EXPECT_SPLIT: value ^= data[i] * KERNEL_MULTIPLIER; break;
        case EXPECT_SUM: value += data[i]; break;
        case EXPECT_TWICE: value += 2 * data[i]; break;
        case EXPECT_SUM_IF: value += data[i] >= THRESHOLD ? data[i] : 0; break;
        case EXPECT_COUNT: value += data[i] >= THRESHOLD; break;
        }
    }
    return value;
}

/* Le tampon de sortie d'un filtre doit contenir, dans l'ordre, les éléments retenus. */
static int output_matches(const uint64_t *data, size_t n, const uint64_t *output, uint64_t kept) {
    uint64_t index = 0;
    for (size_t i = 0; i < n; ++i) {
        if (data[i] >= THRESHOLD) {
            if (index >= kept || output[index] != data[i]) return 0;
            ++index;
        }
    }
    return index == kept;
}

/* Multiensemble d'un jeu de branchement : exactement round(p n) éléments >= seuil. */
static void fill_branch_values(uint64_t *data, size_t n, uint32_t per_mille, uint64_t seed) {
    size_t kept = (n * per_mille + 500) / 1000;
    for (size_t i = 0; i < n; ++i) {
        uint64_t value = splitmix64(seed + i) >> 1;   /* dans [0, 2^63) */
        data[i] = i < kept ? value | THRESHOLD : value;
    }
}

static void shuffle(uint64_t *data, size_t n, uint64_t *state) {
    for (size_t i = n; i > 1; --i) {
        size_t other = (size_t)(random_next(state) % i);
        uint64_t temporary = data[i - 1];
        data[i - 1] = data[other];
        data[other] = temporary;
    }
}

/* Ordonne un jeu : mélange (renouvelé avant chaque échantillon), tri, ou alternance
 * stricte d'un élément non retenu et d'un élément retenu. */
static void arrange(uint64_t *data, size_t n, int order, uint64_t *state, uint64_t *scratch) {
    if (order == ORDER_SHUFFLED) {
        shuffle(data, n, state);
    } else if (order == ORDER_SORTED) {
        qsort(data, n, sizeof(*data), compare_u64);
    } else {
        size_t low = 0, high = 0;
        memcpy(scratch, data, n * sizeof(*data));
        qsort(scratch, n, sizeof(*scratch), compare_u64);   /* moitié basse puis haute */
        for (size_t i = 0; i < n; ++i) {
            data[i] = (i % 2 == 0) ? scratch[low++] : scratch[n / 2 + high++];
        }
    }
}

/* ------------------------------------------------------------------ mesure */

/* Intervalle chronométré : deux lectures d'horloge, boucle d'appels indirects. */
static NOINLINE struct sample measure(const struct measure *m, const uint64_t *data,
                                      uint64_t *output) {
    struct sample sample = {0};
    kernel_fn fn = KERNELS[m->kernel].fn;
    uint64_t accumulated = 0;
    sample.cpu_before = sched_getcpu();
    uint64_t before = monotonic_ns();
    for (uint64_t call = 0; call < m->calls; ++call) {
        accumulated += fn(data, m->n, THRESHOLD, output);
    }
    uint64_t after = monotonic_ns();
    sample.cpu_after = sched_getcpu();
    sample.elapsed_ns = after - before;
    sample.result = accumulated;
    return sample;
}

static int self_test(void) {
    const size_t sizes[] = {0, 1, 2, 3, 5, 8, 63, 64, 1001};
    uint64_t data[1001], output[1001];
    for (size_t j = 0; j < sizeof(sizes) / sizeof(sizes[0]); ++j) {
        size_t n = sizes[j];
        for (uint32_t per_mille = 0; per_mille <= 1000; per_mille += 250) {
            uint64_t state = n * 7919 + per_mille + 1;
            fill_branch_values(data, n, per_mille, UINT64_C(20260917) + per_mille);
            shuffle(data, n, &state);
            for (uint32_t k = 0; k < sizeof(KERNELS) / sizeof(KERNELS[0]); ++k) {
                uint64_t got = KERNELS[k].fn(data, n, THRESHOLD, output);
                uint64_t expected = reference(KERNELS[k].expect, data, n);
                int ok = got == expected && (!KERNELS[k].writes_output || output_matches(data, n, output, got));
                if (!ok) {
                    fprintf(stderr, "self-test (%s): %s differs for n=%zu, p=%u\n",
                            kernel_build, KERNELS[k].name, n, per_mille);
                    return EXIT_FAILURE;
                }
            }
        }
    }
    printf("self-test (%s): OK\n", kernel_build);
    return EXIT_SUCCESS;
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

    const char *output_path = NULL, *meta_path = NULL;
    uint64_t run_id = 0, seed = UINT64_C(20260917), rounds = 21, warmup_rounds = 1, scale = 0;
    for (int i = 1; i + 1 < argc; i += 2) {
        if (strcmp(argv[i], "--output") == 0) output_path = argv[i + 1];
        else if (strcmp(argv[i], "--meta") == 0) meta_path = argv[i + 1];
        else if (strcmp(argv[i], "--run-id") == 0) run_id = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--seed") == 0) seed = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--rounds") == 0) rounds = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--warmup-rounds") == 0) warmup_rounds = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--calls-shift") == 0) scale = parse_u64(argv[i + 1], argv[i]);
        else {
            fprintf(stderr, "unknown option %s\n", argv[i]);
            return EXIT_FAILURE;
        }
    }
    if (argc % 2 == 0 || output_path == NULL || meta_path == NULL || run_id == 0 || rounds == 0 ||
        warmup_rounds >= rounds || rounds > 10000 || scale > 16) {
        fprintf(stderr, "usage: %s --self-test | --output FILE --meta FILE --run-id N [--seed N] "
                        "[--rounds N] [--warmup-rounds N] [--calls-shift N]\n", argv[0]);
        return EXIT_FAILURE;
    }

    struct measure measures[64];
    size_t measure_count = build_measures(measures);
    for (size_t i = 0; i < measure_count; ++i) {
        /* --calls-shift réduit le nombre d'appels, pour les vérifications rapides. */
        uint64_t reduced = measures[i].calls >> scale;
        measures[i].calls = reduced ? reduced : 1;
    }

    /* Données, toutes initialisées avant la première mesure. */
    uint64_t *uniform = aligned_alloc(4096, 4096 * ((DEPENDENCY_N * 8 + 4095) / 4096));
    uint64_t *output = aligned_alloc(4096, 4096 * ((BRANCH_N * 8 + 4095) / 4096));
    uint64_t *scratch = malloc(BRANCH_N * sizeof(uint64_t));
    uint64_t *branch[BRANCH_SET_COUNT];
    size_t sample_count = measure_count * (size_t)rounds;
    struct sample *samples = calloc(sample_count, sizeof(*samples));
    uint32_t *order = malloc(measure_count * sizeof(*order));
    if (uniform == NULL || output == NULL || scratch == NULL || samples == NULL || order == NULL) {
        perror("allocation");
        return EXIT_FAILURE;
    }
    for (size_t i = 0; i < DEPENDENCY_N; ++i) uniform[i] = splitmix64(seed + i);
    memset(output, 0, BRANCH_N * sizeof(uint64_t));
    uint64_t random_state = seed ^ (run_id * UINT64_C(0x9e3779b97f4a7c15));
    if (random_state == 0) random_state = 1;
    for (size_t d = 0; d < BRANCH_SET_COUNT; ++d) {
        branch[d] = aligned_alloc(4096, 4096 * ((BRANCH_N * 8 + 4095) / 4096));
        if (branch[d] == NULL) return EXIT_FAILURE;
        fill_branch_values(branch[d], BRANCH_N, BRANCH_SETS[d].per_mille, seed * 31 + d);
        arrange(branch[d], BRANCH_N, (int)BRANCH_SETS[d].order, &random_state, scratch);
    }
    uint64_t small_expected[SMALL_SIZE_COUNT];
    for (size_t s = 0; s < SMALL_SIZE_COUNT; ++s) {
        small_expected[s] = reference(EXPECT_SUM, uniform, SMALL_SIZES[s]);
    }

    int first_cpu = sched_getcpu();
    char frequency_before[32], frequency_after[32];
    read_frequency(first_cpu, frequency_before, sizeof(frequency_before));
    struct rusage usage_before, usage_after;
    getrusage(RUSAGE_SELF, &usage_before);

    size_t cursor = 0;
    for (uint32_t round = 0; round < rounds; ++round) {
        for (uint32_t i = 0; i < measure_count; ++i) order[i] = i;
        for (size_t i = measure_count; i > 1; --i) {
            size_t other = (size_t)(random_next(&random_state) % i);
            uint32_t temporary = order[i - 1];
            order[i - 1] = order[other];
            order[other] = temporary;
        }
        for (uint32_t position = 0; position < measure_count; ++position) {
            const struct measure *m = &measures[order[position]];
            const uint64_t *data = uniform;
            uint64_t expected;
            if (m->part == PART_BRANCH) {
                const struct dataset *set = &BRANCH_SETS[m->dataset];
                /* Nouvel ordre aléatoire avant chaque échantillon mélangé, hors mesure :
                 * le prédicteur ne peut pas apprendre une séquence répétée. */
                if (set->order == ORDER_SHUFFLED) shuffle(branch[m->dataset], BRANCH_N, &random_state);
                data = branch[m->dataset];
                expected = reference(KERNELS[m->kernel].expect, data, m->n);
            } else if (m->part == PART_SMALL) {
                size_t s = 0;
                while (SMALL_SIZES[s] != m->n) ++s;
                expected = small_expected[s];
            } else {
                expected = reference(KERNELS[m->kernel].expect, data, m->n);
            }
            struct sample sample = measure(m, data, output);
            sample.round = round;
            sample.position = position;
            sample.measure = order[position];
            sample.expected = expected * m->calls;
            sample.output_ok = !KERNELS[m->kernel].writes_output ||
                               output_matches(data, m->n, output, sample.result / m->calls);
            samples[cursor++] = sample;
        }
    }

    getrusage(RUSAGE_SELF, &usage_after);
    read_frequency(first_cpu, frequency_after, sizeof(frequency_after));

    FILE *file = fopen(output_path, "w");
    if (file == NULL) {
        perror(output_path);
        return EXIT_FAILURE;
    }
    fprintf(file, "run_id,build,seed,sample,round,phase,position,part,label,dataset,n,calls,"
                  "elapsed_ns,cpu_before,cpu_after,result,expected,output_ok\n");
    int invalid = 0;
    for (size_t i = 0; i < sample_count; ++i) {
        const struct sample *s = &samples[i];
        const struct measure *m = &measures[s->measure];
        invalid += s->result != s->expected || !s->output_ok;
        fprintf(file,
                "%" PRIu64 ",%s,%" PRIu64 ",%zu,%" PRIu32 ",%s,%" PRIu32 ",%s,%s,%s,%zu,%" PRIu64
                ",%" PRIu64 ",%d,%d,%" PRIu64 ",%" PRIu64 ",%d\n",
                run_id, kernel_build, seed, i, s->round, s->round < warmup_rounds ? "warmup" : "measure",
                s->position, PART_NAMES[m->part], m->label,
                m->part == PART_BRANCH ? BRANCH_SETS[m->dataset].name : "uniform", m->n, m->calls,
                s->elapsed_ns, s->cpu_before, s->cpu_after, s->result, s->expected, s->output_ok);
    }
    int status = fclose(file) == 0 ? EXIT_SUCCESS : EXIT_FAILURE;

    FILE *meta = fopen(meta_path, "w");
    if (meta == NULL) {
        perror(meta_path);
        return EXIT_FAILURE;
    }
    fprintf(meta, "run_id,build,compiler,first_cpu,frequency_before_khz,frequency_after_khz,"
                  "minor_faults,voluntary_switches,involuntary_switches,invalid_samples\n");
    fprintf(meta, "%" PRIu64 ",%s,\"%s\",%d,%s,%s,%ld,%ld,%ld,%d\n", run_id, kernel_build,
            kernel_compiler, first_cpu, frequency_before, frequency_after,
            usage_after.ru_minflt - usage_before.ru_minflt,
            usage_after.ru_nvcsw - usage_before.ru_nvcsw,
            usage_after.ru_nivcsw - usage_before.ru_nivcsw, invalid);
    if (fclose(meta) != 0) status = EXIT_FAILURE;

    if (invalid != 0) {
        fprintf(stderr, "%d échantillons invalides : les mesures ne sont pas valides\n", invalid);
        return EXIT_FAILURE;
    }
    return status;
}
