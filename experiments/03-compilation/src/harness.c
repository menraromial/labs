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

enum expectation { EXPECT_SUM, EXPECT_TWICE, EXPECT_ZERO, EXPECT_INDICES };

struct label {
    const char *name;
    kernel_fn fn;
    enum expectation expect;
};

/* sum_array et sum_array_bis appellent la même fonction : contrôle A/A. */
static const struct label LABELS[] = {
    {"sum_array", sum_array, EXPECT_SUM},
    {"sum_array_bis", sum_array, EXPECT_SUM},
    {"sum_array_twice", sum_array_twice, EXPECT_TWICE},
    {"sum_discarded", sum_discarded, EXPECT_ZERO},
    {"sum_indices", sum_indices, EXPECT_INDICES},
};
#define LABEL_COUNT (sizeof(LABELS) / sizeof(LABELS[0]))

struct sample {
    uint32_t round;
    uint32_t position;
    uint32_t label;
    uint32_t size_index;
    uint64_t calls;
    uint64_t elapsed_ns;
    uint64_t result;
    int cpu_before;
    int cpu_after;
};

struct options {
    const char *output;
    const char *meta;
    uint64_t run_id;
    uint64_t seed;
    uint64_t rounds;
    uint64_t warmup_rounds;
    uint64_t min_log2;
    uint64_t max_log2;
    uint64_t step_log2;
    uint64_t target_log2;
};

static uint64_t monotonic_ns(void) {
    struct timespec value;
    if (clock_gettime(CLOCK_MONOTONIC, &value) != 0) {
        perror("clock_gettime");
        exit(EXIT_FAILURE);
    }
    return (uint64_t)value.tv_sec * UINT64_C(1000000000) + (uint64_t)value.tv_nsec;
}

/* Contenu du tableau : SplitMix64, facile à réimplémenter pour la vérification. */
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

/* Somme de référence, écrite dans le harnais et non dans les noyaux mesurés. */
static uint64_t reference_sum(const uint64_t *data, size_t n) {
    uint64_t sum = 0;
    for (size_t i = 0; i < n; ++i) sum += data[i];
    return sum;
}

static uint64_t expected_per_call(enum expectation expect, uint64_t prefix_sum, size_t n) {
    switch (expect) {
    case EXPECT_SUM: return prefix_sum;
    case EXPECT_TWICE: return 2 * prefix_sum;
    case EXPECT_ZERO: return 0;
    case EXPECT_INDICES: return n == 0 ? 0 : (uint64_t)n * ((uint64_t)n - 1) / 2;
    }
    return 0;
}

/* L'intervalle chronométré contient les deux lectures d'horloge, la boucle
 * d'appels et les appels indirects au noyau. sched_getcpu est hors intervalle. */
static NOINLINE struct sample measure(uint32_t label, const uint64_t *data, size_t n,
                                      uint64_t calls) {
    struct sample sample = {.label = label, .calls = calls};
    kernel_fn fn = LABELS[label].fn;
    uint64_t accumulated = 0;
    sample.cpu_before = sched_getcpu();
    uint64_t before = monotonic_ns();
    for (uint64_t call = 0; call < calls; ++call) {
        accumulated += fn(data, n);
    }
    uint64_t after = monotonic_ns();
    sample.cpu_after = sched_getcpu();
    sample.elapsed_ns = after - before;
    sample.result = accumulated;
    return sample;
}

static int self_test(void) {
    const size_t sizes[] = {0, 1, 2, 7, 64, 1000, 4099};
    uint64_t *data = malloc(4099 * sizeof(*data));
    if (data == NULL) return EXIT_FAILURE;
    for (size_t i = 0; i < 4099; ++i) data[i] = splitmix64(UINT64_C(20260916) + i);
    for (size_t j = 0; j < sizeof(sizes) / sizeof(sizes[0]); ++j) {
        size_t n = sizes[j];
        uint64_t prefix = reference_sum(data, n);
        for (uint32_t label = 0; label < LABEL_COUNT; ++label) {
            uint64_t got = LABELS[label].fn(data, n);
            uint64_t expected = expected_per_call(LABELS[label].expect, prefix, n);
            if (got != expected) {
                fprintf(stderr, "self-test (%s): %s differs for n=%zu\n",
                        kernel_opt_level, LABELS[label].name, n);
                free(data);
                return EXIT_FAILURE;
            }
        }
    }
    free(data);
    printf("self-test (%s): OK\n", kernel_opt_level);
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

static void usage(const char *program) {
    fprintf(stderr,
            "usage: %s --self-test\n"
            "       %s --output FILE --meta FILE --run-id N [--seed N] [--rounds N]\n"
            "          [--warmup-rounds N] [--min-log2 N] [--max-log2 N] [--step-log2 N]\n"
            "          [--target-log2 N]\n",
            program, program);
}

static struct options parse_options(int argc, char **argv) {
    struct options options = {
        .seed = UINT64_C(20260916),
        .rounds = 16,
        .warmup_rounds = 1,
        .min_log2 = 6,
        .max_log2 = 22,
        .step_log2 = 2,
        .target_log2 = 22,
    };
    for (int i = 1; i < argc; ++i) {
        if (i + 1 >= argc) {
            usage(argv[0]);
            exit(EXIT_FAILURE);
        }
        const char *option = argv[i++];
        const char *value = argv[i];
        if (strcmp(option, "--output") == 0) options.output = value;
        else if (strcmp(option, "--meta") == 0) options.meta = value;
        else if (strcmp(option, "--run-id") == 0) options.run_id = parse_u64(value, option);
        else if (strcmp(option, "--seed") == 0) options.seed = parse_u64(value, option);
        else if (strcmp(option, "--rounds") == 0) options.rounds = parse_u64(value, option);
        else if (strcmp(option, "--warmup-rounds") == 0) options.warmup_rounds = parse_u64(value, option);
        else if (strcmp(option, "--min-log2") == 0) options.min_log2 = parse_u64(value, option);
        else if (strcmp(option, "--max-log2") == 0) options.max_log2 = parse_u64(value, option);
        else if (strcmp(option, "--step-log2") == 0) options.step_log2 = parse_u64(value, option);
        else if (strcmp(option, "--target-log2") == 0) options.target_log2 = parse_u64(value, option);
        else {
            usage(argv[0]);
            exit(EXIT_FAILURE);
        }
    }
    const char *problem = NULL;
    if (options.output == NULL || options.meta == NULL) problem = "--output and --meta are required";
    else if (options.run_id == 0) problem = "--run-id must be positive";
    else if (options.rounds == 0 || options.rounds > 100000) problem = "--rounds must be in [1, 100000]";
    else if (options.warmup_rounds >= options.rounds) problem = "--warmup-rounds must be smaller than --rounds";
    else if (options.step_log2 == 0) problem = "--step-log2 must be positive";
    else if (options.min_log2 > options.max_log2 || options.max_log2 > 30)
        problem = "sizes must satisfy min-log2 <= max-log2 <= 30";
    else if (options.target_log2 > 34) problem = "--target-log2 must be at most 34";
    if (problem != NULL) {
        fprintf(stderr, "%s\n", problem);
        usage(argv[0]);
        exit(EXIT_FAILURE);
    }
    return options;
}

static void read_frequency(int cpu, char *buffer, size_t length) {
    char path[128];
    snprintf(path, sizeof(path), "/sys/devices/system/cpu/cpu%d/cpufreq/scaling_cur_freq", cpu);
    FILE *file = fopen(path, "r");
    if (file == NULL || fgets(buffer, (int)length, file) == NULL) {
        buffer[0] = '\0';
    }
    if (file != NULL) fclose(file);
    buffer[strcspn(buffer, "\n")] = '\0';
}

int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "--self-test") == 0) return self_test();
    struct options options = parse_options(argc, argv);

    size_t size_count = (size_t)((options.max_log2 - options.min_log2) / options.step_log2 + 1);
    size_t max_n = (size_t)1 << (options.min_log2 + (size_count - 1) * options.step_log2);
    size_t per_round = size_count * LABEL_COUNT;
    size_t sample_count = per_round * (size_t)options.rounds;

    /* Alignement sur une page : tous les binaires lisent la même disposition mémoire. */
    uint64_t *data = aligned_alloc(4096, ((max_n * sizeof(*data) + 4095) / 4096) * 4096);
    uint64_t *prefix = calloc(size_count, sizeof(*prefix));
    struct sample *samples = calloc(sample_count, sizeof(*samples));
    if (data == NULL || prefix == NULL || samples == NULL) {
        perror("allocation");
        return EXIT_FAILURE;
    }
    /* Initialisation hors mesure : toutes les pages sont touchées avant la première mesure. */
    for (size_t i = 0; i < max_n; ++i) data[i] = splitmix64(options.seed + i);
    for (size_t s = 0; s < size_count; ++s) {
        prefix[s] = reference_sum(data, (size_t)1 << (options.min_log2 + s * options.step_log2));
    }

    /* Plan complet : dans chaque tour, les couples (noyau, taille) sont permutés. */
    uint64_t random_state = options.seed ^ (options.run_id * UINT64_C(0x9e3779b97f4a7c15));
    if (random_state == 0) random_state = 1;
    for (uint32_t round = 0; round < options.rounds; ++round) {
        struct sample *slice = samples + (size_t)round * per_round;
        for (size_t j = 0; j < per_round; ++j) {
            slice[j] = (struct sample){.round = round, .label = (uint32_t)(j % LABEL_COUNT),
                                       .size_index = (uint32_t)(j / LABEL_COUNT)};
        }
        for (size_t j = per_round; j > 1; --j) {
            size_t other = (size_t)(random_next(&random_state) % j);
            struct sample temporary = slice[j - 1];
            slice[j - 1] = slice[other];
            slice[other] = temporary;
        }
        for (size_t j = 0; j < per_round; ++j) slice[j].position = (uint32_t)j;
    }

    int first_cpu = sched_getcpu();
    char frequency_before[32];
    read_frequency(first_cpu, frequency_before, sizeof(frequency_before));
    struct rusage usage_before;
    getrusage(RUSAGE_SELF, &usage_before);

    uint64_t target = UINT64_C(1) << options.target_log2;
    for (size_t i = 0; i < sample_count; ++i) {
        struct sample planned = samples[i];
        size_t n = (size_t)1 << (options.min_log2 + planned.size_index * options.step_log2);
        uint64_t calls = target > n ? target / n : 1;
        struct sample measured = measure(planned.label, data, n, calls);
        measured.round = planned.round;
        measured.position = planned.position;
        measured.size_index = planned.size_index;
        samples[i] = measured;
    }

    struct rusage usage_after;
    getrusage(RUSAGE_SELF, &usage_after);
    char frequency_after[32];
    read_frequency(first_cpu, frequency_after, sizeof(frequency_after));

    FILE *output = fopen(options.output, "w");
    if (output == NULL) {
        perror(options.output);
        return EXIT_FAILURE;
    }
    fprintf(output, "run_id,level,seed,sample,round,phase,position,label,n,calls,elapsed_ns,"
                    "cpu_before,cpu_after,result,expected\n");
    int mismatches = 0;
    for (size_t i = 0; i < sample_count; ++i) {
        const struct sample *s = &samples[i];
        size_t n = (size_t)1 << (options.min_log2 + s->size_index * options.step_log2);
        uint64_t expected = s->calls * expected_per_call(LABELS[s->label].expect,
                                                         prefix[s->size_index], n);
        mismatches += s->result != expected;
        fprintf(output,
                "%" PRIu64 ",%s,%" PRIu64 ",%zu,%" PRIu32 ",%s,%" PRIu32 ",%s,%zu,%" PRIu64
                ",%" PRIu64 ",%d,%d,%" PRIu64 ",%" PRIu64 "\n",
                options.run_id, kernel_opt_level, options.seed, i, s->round,
                s->round < options.warmup_rounds ? "warmup" : "measure", s->position,
                LABELS[s->label].name, n, s->calls, s->elapsed_ns, s->cpu_before,
                s->cpu_after, s->result, expected);
    }
    int status = fclose(output) == 0 ? EXIT_SUCCESS : EXIT_FAILURE;

    FILE *meta = fopen(options.meta, "w");
    if (meta == NULL) {
        perror(options.meta);
        return EXIT_FAILURE;
    }
    fprintf(meta, "run_id,level,compiler,first_cpu,frequency_before_khz,frequency_after_khz,"
                  "minor_faults,major_faults,voluntary_switches,involuntary_switches,mismatches\n");
    fprintf(meta, "%" PRIu64 ",%s,\"%s\",%d,%s,%s,%ld,%ld,%ld,%ld,%d\n", options.run_id,
            kernel_opt_level, kernel_compiler, first_cpu, frequency_before, frequency_after,
            usage_after.ru_minflt - usage_before.ru_minflt,
            usage_after.ru_majflt - usage_before.ru_majflt,
            usage_after.ru_nvcsw - usage_before.ru_nvcsw,
            usage_after.ru_nivcsw - usage_before.ru_nivcsw, mismatches);
    if (fclose(meta) != 0) status = EXIT_FAILURE;

    free(samples);
    free(prefix);
    free(data);
    if (mismatches != 0) {
        fprintf(stderr, "%d résultats inexacts : les mesures ne sont pas valides\n", mismatches);
        return EXIT_FAILURE;
    }
    return status;
}
