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

#if defined(__GNUC__) || defined(__clang__)
#define NOINLINE __attribute__((noinline))
#else
#define NOINLINE
#endif

#define GOLDEN UINT64_C(0x9e3779b97f4a7c15)
#define VARIANT_COUNT 3U

enum mode { MODE_AMORTIZATION, MODE_FIXED, MODE_INTERLEAVED };

struct variant {
    const char *name;
    unsigned calls_per_op;
    uint64_t (*run)(uint64_t state, uint32_t ops);
};

struct sample {
    uint32_t round;
    uint32_t position;
    uint32_t variant;
    uint32_t ops;
    uint64_t elapsed_ns;
    uint64_t result;
    int cpu_before;
    int cpu_after;
};

enum prime { PRIME_NONE, PRIME_CLOCK, PRIME_CODE, PRIME_FULL };
static const char *const PRIME_NAMES[] = {"none", "clock", "code", "full"};

struct options {
    const char *output;
    const char *meta;
    const char *protocol;
    const char *affinity;
    enum mode mode;
    enum prime prime;
    uint64_t run_id;
    uint64_t seed;
    uint64_t batch;
    uint64_t rounds;
    uint64_t warmup_rounds;
    uint64_t max_batch;
    uint64_t warmup_ops;
};

static uint64_t monotonic_ns(void) {
    struct timespec value;
    if (clock_gettime(CLOCK_MONOTONIC, &value) != 0) {
        perror("clock_gettime");
        exit(EXIT_FAILURE);
    }
    return (uint64_t)value.tv_sec * UINT64_C(1000000000) + (uint64_t)value.tv_nsec;
}

/* Travail mesuré : chaque résultat est l'entrée de l'appel suivant, ce qui
 * empêche d'exécuter plusieurs opérations en parallèle ou de les supprimer. */
static NOINLINE uint64_t tiny_work(uint64_t value) {
    value ^= value >> 12;
    value ^= value << 25;
    value ^= value >> 27;
    return value * UINT64_C(2685821657736338717);
}

static uint64_t reference_work(uint64_t value) {
    uint64_t first = value ^ (value >> 12);
    uint64_t second = first ^ (first << 25);
    uint64_t third = second ^ (second >> 27);
    return third * UINT64_C(2685821657736338717);
}

static NOINLINE uint64_t run_single(uint64_t state, uint32_t ops) {
    for (uint32_t i = 0; i < ops; ++i) {
        state = tiny_work(state);
    }
    return state;
}

static NOINLINE uint64_t run_double(uint64_t state, uint32_t ops) {
    for (uint32_t i = 0; i < ops; ++i) {
        state = tiny_work(state);
        state = tiny_work(state);
    }
    return state;
}

/* A et A_bis exécutent le même code machine : le rapport vrai de leurs coûts
 * vaut 1 (contrôle négatif). B effectue exactement deux fois plus d'appels à
 * tiny_work par opération (contrôle positif). */
static const struct variant VARIANTS[VARIANT_COUNT] = {
    {"A", 1, run_single},
    {"A_bis", 1, run_single},
    {"B", 2, run_double},
};

/* Générateur des permutations, indépendant de l'état du travail mesuré. */
static uint64_t random_next(uint64_t *state) {
    *state ^= *state >> 12;
    *state ^= *state << 25;
    *state ^= *state >> 27;
    return *state * UINT64_C(2685821657736338717);
}

static void shuffle_u32(uint32_t *values, size_t count, uint64_t *random_state) {
    for (size_t i = count; i > 1; --i) {
        size_t other = (size_t)(random_next(random_state) % i);
        uint32_t temporary = values[i - 1];
        values[i - 1] = values[other];
        values[other] = temporary;
    }
}

static uint64_t initial_state(uint64_t seed, uint64_t run_id) {
    uint64_t state = seed ^ (run_id * GOLDEN);
    return state != 0 ? state : GOLDEN;
}

/* L'intervalle chronométré contient les deux lectures d'horloge, l'appel
 * indirect et la boucle. Les appels à sched_getcpu sont hors intervalle.
 * La fonction n'est pas intégrée à l'appelant : toutes les mesures, y compris
 * celles jetées par l'amorçage « full », passent par les mêmes instructions. */
static NOINLINE struct sample measure(uint32_t variant, uint32_t ops, uint64_t *state) {
    struct sample sample = {.variant = variant, .ops = ops};
    uint64_t current = *state;
    sample.cpu_before = sched_getcpu();
    uint64_t before = monotonic_ns();
    uint64_t next = VARIANTS[variant].run(current, ops);
    uint64_t after = monotonic_ns();
    sample.cpu_after = sched_getcpu();
    sample.elapsed_ns = after - before;
    sample.result = next;
    *state = next;
    return sample;
}

static int self_test(void) {
    const uint64_t cases[] = {UINT64_C(1), UINT64_C(42), GOLDEN, UINT64_MAX};
    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        if (tiny_work(cases[i]) != reference_work(cases[i])) {
            fprintf(stderr, "self-test: tiny_work differs for case %zu\n", i);
            return EXIT_FAILURE;
        }
        const uint32_t counts[] = {0, 1, 5, 1000};
        for (size_t j = 0; j < sizeof(counts) / sizeof(counts[0]); ++j) {
            uint64_t expected = cases[i];
            for (uint32_t k = 0; k < counts[j]; ++k) expected = reference_work(expected);
            if (run_single(cases[i], counts[j]) != expected) {
                fprintf(stderr, "self-test: run_single differs (%zu, %u)\n", i, counts[j]);
                return EXIT_FAILURE;
            }
            if (run_double(cases[i], counts[j]) != run_single(cases[i], 2 * counts[j])) {
                fprintf(stderr, "self-test: run_double differs (%zu, %u)\n", i, counts[j]);
                return EXIT_FAILURE;
            }
        }
    }
    for (uint64_t seed = 1; seed <= 50; ++seed) {
        uint32_t values[VARIANT_COUNT] = {0, 1, 2};
        uint64_t random_state = seed;
        shuffle_u32(values, VARIANT_COUNT, &random_state);
        unsigned seen = 0;
        for (unsigned i = 0; i < VARIANT_COUNT; ++i) seen |= 1U << values[i];
        if (seen != (1U << VARIANT_COUNT) - 1) {
            fprintf(stderr, "self-test: shuffle is not a permutation (seed %" PRIu64 ")\n", seed);
            return EXIT_FAILURE;
        }
    }
    puts("self-test: OK");
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
            "       %s --mode amortization|fixed|interleaved --output FILE --meta FILE\n"
            "          --run-id N --protocol LABEL [--affinity LABEL] [--seed N]\n"
            "          [--batch N] [--rounds N] [--warmup-rounds N]\n"
            "          [--max-batch N] [--warmup-ops N] [--prime none|clock|code|full]\n",
            program, program);
}

static struct options parse_options(int argc, char **argv) {
    struct options options = {
        .affinity = "libre",
        .mode = MODE_FIXED,
        .seed = UINT64_C(20260916),
        .batch = 1,
        .rounds = 1,
        .max_batch = 32768,
    };
    int mode_given = 0;
    for (int i = 1; i < argc; ++i) {
        if (i + 1 >= argc) {
            usage(argv[0]);
            exit(EXIT_FAILURE);
        }
        const char *option = argv[i++];
        const char *value = argv[i];
        if (strcmp(option, "--output") == 0) options.output = value;
        else if (strcmp(option, "--meta") == 0) options.meta = value;
        else if (strcmp(option, "--protocol") == 0) options.protocol = value;
        else if (strcmp(option, "--affinity") == 0) options.affinity = value;
        else if (strcmp(option, "--run-id") == 0) options.run_id = parse_u64(value, option);
        else if (strcmp(option, "--seed") == 0) options.seed = parse_u64(value, option);
        else if (strcmp(option, "--batch") == 0) options.batch = parse_u64(value, option);
        else if (strcmp(option, "--rounds") == 0) options.rounds = parse_u64(value, option);
        else if (strcmp(option, "--warmup-rounds") == 0) options.warmup_rounds = parse_u64(value, option);
        else if (strcmp(option, "--max-batch") == 0) options.max_batch = parse_u64(value, option);
        else if (strcmp(option, "--warmup-ops") == 0) options.warmup_ops = parse_u64(value, option);
        else if (strcmp(option, "--prime") == 0) {
            size_t index = 0;
            while (index < 4 && strcmp(value, PRIME_NAMES[index]) != 0) ++index;
            if (index == 4) {
                fprintf(stderr, "unknown prime: %s\n", value);
                exit(EXIT_FAILURE);
            }
            options.prime = (enum prime)index;
        } else if (strcmp(option, "--mode") == 0) {
            mode_given = 1;
            if (strcmp(value, "amortization") == 0) options.mode = MODE_AMORTIZATION;
            else if (strcmp(value, "fixed") == 0) options.mode = MODE_FIXED;
            else if (strcmp(value, "interleaved") == 0) options.mode = MODE_INTERLEAVED;
            else {
                fprintf(stderr, "unknown mode: %s\n", value);
                exit(EXIT_FAILURE);
            }
        } else {
            usage(argv[0]);
            exit(EXIT_FAILURE);
        }
    }
    const char *problem = NULL;
    if (!mode_given || options.output == NULL || options.meta == NULL || options.protocol == NULL)
        problem = "--mode, --output, --meta and --protocol are required";
    else if (options.run_id == 0) problem = "--run-id must be positive";
    else if (options.batch == 0 || options.batch > UINT32_MAX) problem = "--batch must be in [1, 2^32 - 1]";
    else if (options.rounds == 0 || options.rounds > UINT32_MAX) problem = "--rounds must be in [1, 2^32 - 1]";
    else if (options.warmup_rounds >= options.rounds) problem = "--warmup-rounds must be smaller than --rounds";
    else if (options.max_batch == 0 || options.max_batch > (UINT64_C(1) << 31))
        problem = "--max-batch must be in [1, 2^31]";
    else if (options.warmup_ops > UINT32_MAX) problem = "--warmup-ops must be below 2^32";
    if (problem != NULL) {
        fprintf(stderr, "%s\n", problem);
        usage(argv[0]);
        exit(EXIT_FAILURE);
    }
    return options;
}

/* Construit le plan de mesure complet avant d'exécuter la moindre mesure. */
static struct sample *build_plan(const struct options *options, size_t *count) {
    uint64_t random_state = options->seed ? options->seed : GOLDEN;
    struct sample *plan = NULL;

    if (options->mode == MODE_AMORTIZATION) {
        size_t sizes = 0;
        for (uint64_t batch = 1; batch <= options->max_batch; batch *= 2) ++sizes;
        *count = sizes * (size_t)options->rounds;
        plan = calloc(*count, sizeof(*plan));
        if (plan == NULL) return NULL;
        size_t cursor = 0;
        for (uint32_t round = 0; round < options->rounds; ++round) {
            for (uint64_t batch = 1; batch <= options->max_batch; batch *= 2) {
                plan[cursor++] = (struct sample){.round = round, .ops = (uint32_t)batch};
            }
        }
        /* Permutation de Fisher-Yates sur les indices du plan. */
        for (size_t i = *count; i > 1; --i) {
            size_t other = (size_t)(random_next(&random_state) % i);
            struct sample temporary = plan[i - 1];
            plan[i - 1] = plan[other];
            plan[other] = temporary;
        }
        return plan;
    }

    *count = (size_t)options->rounds * VARIANT_COUNT;
    plan = calloc(*count, sizeof(*plan));
    if (plan == NULL) return NULL;
    for (uint32_t round = 0; round < options->rounds; ++round) {
        uint32_t order[VARIANT_COUNT] = {0, 1, 2};
        if (options->mode == MODE_INTERLEAVED) shuffle_u32(order, VARIANT_COUNT, &random_state);
        for (uint32_t position = 0; position < VARIANT_COUNT; ++position) {
            plan[(size_t)round * VARIANT_COUNT + position] = (struct sample){
                .round = round,
                .position = position,
                .variant = order[position],
                .ops = (uint32_t)options->batch,
            };
        }
    }
    return plan;
}

static const char *mode_name(enum mode mode) {
    switch (mode) {
    case MODE_AMORTIZATION: return "amortization";
    case MODE_FIXED: return "fixed";
    case MODE_INTERLEAVED: return "interleaved";
    }
    return "unknown";
}

int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "--self-test") == 0) return self_test();
    struct options options = parse_options(argc, argv);

    size_t count = 0;
    struct sample *samples = build_plan(&options, &count);
    if (samples == NULL) {
        perror("calloc");
        return EXIT_FAILURE;
    }

    cpu_set_t allowed;
    CPU_ZERO(&allowed);
    if (sched_getaffinity(0, sizeof(allowed), &allowed) != 0) {
        perror("sched_getaffinity");
        free(samples);
        return EXIT_FAILURE;
    }

    uint64_t state = initial_state(options.seed, options.run_id);
    state = run_single(state, (uint32_t)options.warmup_ops);

    /* Amorçage non chronométré, pour le contrôle du premier passage à froid :
     * clock : une lecture d'horloge ; code : un appel direct de chaque fonction
     * mesurée ; full : une mesure complète de chaque variante, jetée. */
    if (options.prime == PRIME_CLOCK) {
        (void)monotonic_ns();
    } else if (options.prime == PRIME_CODE) {
        state = run_single(state, 1);
        state = run_double(state, 1);
    } else if (options.prime == PRIME_FULL) {
        for (uint32_t variant = 0; variant < VARIANT_COUNT; ++variant) {
            (void)measure(variant, 1, &state);
        }
    }

    struct rusage usage_before;
    getrusage(RUSAGE_SELF, &usage_before);

    /* Mesures : aucune écriture ni allocation entre deux échantillons. */
    for (size_t i = 0; i < count; ++i) {
        struct sample planned = samples[i];
        struct sample measured = measure(planned.variant, planned.ops, &state);
        measured.round = planned.round;
        measured.position = planned.position;
        samples[i] = measured;
    }

    struct rusage usage_after;
    getrusage(RUSAGE_SELF, &usage_after);

    FILE *output = fopen(options.output, "w");
    if (output == NULL) {
        perror(options.output);
        free(samples);
        return EXIT_FAILURE;
    }
    fprintf(output, "protocol,mode,prime,run_id,seed,affinity,allowed_cpus,warmup_ops,warmup_rounds,"
                    "sample,round,phase,position,variant,ops,calls_per_op,elapsed_ns,"
                    "cpu_before,cpu_after,result\n");
    for (size_t i = 0; i < count; ++i) {
        const struct sample *s = &samples[i];
        const char *phase = s->round < options.warmup_rounds ? "warmup" : "measure";
        fprintf(output,
                "%s,%s,%s,%" PRIu64 ",%" PRIu64 ",%s,%d,%" PRIu64 ",%" PRIu64 ",%zu,%" PRIu32
                ",%s,%" PRIu32 ",%s,%" PRIu32 ",%u,%" PRIu64 ",%d,%d,%" PRIu64 "\n",
                options.protocol, mode_name(options.mode), PRIME_NAMES[options.prime],
                options.run_id, options.seed,
                options.affinity, CPU_COUNT(&allowed), options.warmup_ops,
                options.warmup_rounds, i, s->round, phase, s->position,
                VARIANTS[s->variant].name, s->ops, VARIANTS[s->variant].calls_per_op,
                s->elapsed_ns, s->cpu_before, s->cpu_after, s->result);
    }
    int status = fclose(output) == 0 ? EXIT_SUCCESS : EXIT_FAILURE;

    FILE *meta = fopen(options.meta, "w");
    if (meta == NULL) {
        perror(options.meta);
        free(samples);
        return EXIT_FAILURE;
    }
    fprintf(meta, "run_id,protocol,affinity,minor_faults,major_faults,"
                  "voluntary_switches,involuntary_switches\n");
    fprintf(meta, "%" PRIu64 ",%s,%s,%ld,%ld,%ld,%ld\n", options.run_id, options.protocol,
            options.affinity, usage_after.ru_minflt - usage_before.ru_minflt,
            usage_after.ru_majflt - usage_before.ru_majflt,
            usage_after.ru_nvcsw - usage_before.ru_nvcsw,
            usage_after.ru_nivcsw - usage_before.ru_nivcsw);
    if (fclose(meta) != 0) status = EXIT_FAILURE;

    free(samples);
    return status;
}
