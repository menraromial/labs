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
#define HUGE_SIZE (UINT64_C(2) << 20)
#define PAGE_SIZE_4K UINT64_C(4096)

/* Entier de 128 bits (extension GCC et Clang), pour le produit de fast_range. */
__extension__ typedef unsigned __int128 u128;

/* ------------------------------------------------------------------ noyaux mesurés */

/* Accès dépendants : l'indice suivant est la valeur lue. Le processeur ne connaît
 * l'adresse d'un accès qu'une fois le précédent terminé : les défauts de cache ne
 * peuvent pas se recouvrir. */
static NOINLINE uint64_t chase(const uint64_t *next, uint64_t start, uint64_t steps) {
    uint64_t index = start, sum = 0;
    for (uint64_t j = 0; j < steps; ++j) {
        sum += index;
        index = next[index];
    }
    return sum;
}

static inline uint64_t mix(uint64_t salt, uint64_t j) {
    uint64_t x = salt + j * GOLDEN;
    x ^= x >> 31;
    x *= UINT64_C(0xbf58476d1ce4e5b9);
    x ^= x >> 29;
    return x;
}

/* Accès indépendants (comme C1) : l'indice ne dépend que du rang. */
static NOINLINE uint64_t independent(const uint64_t *data, uint64_t n, uint64_t salt, uint64_t accesses) {
    uint64_t sum = 0;
    for (uint64_t j = 0; j < accesses; ++j) {
        sum += data[(uint64_t)(((u128)mix(salt, j) * n) >> 64)];
    }
    return sum;
}

/* Premier ou second accès en écriture à chaque page de 4 Kio d'une zone. */
static NOINLINE uint64_t touch(unsigned char *region, uint64_t bytes, unsigned char value) {
    uint64_t pages = 0;
    for (uint64_t offset = 0; offset < bytes; offset += PAGE_SIZE_4K) {
        region[offset] = value;
        ++pages;
    }
    return pages;
}

/* ------------------------------------------------------------------ références */

static uint64_t reference_chase(const uint64_t *next, uint64_t start, uint64_t steps) {
    uint64_t sum = 0;
    for (uint64_t j = 0, index = start; j != steps; index = next[index], ++j) sum += index;
    return sum;
}

static uint64_t reference_independent(const uint64_t *data, uint64_t n, uint64_t salt, uint64_t accesses) {
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

/* ------------------------------------------------------------------ utilitaires */

static uint64_t monotonic_ns(void) {
    struct timespec value;
    if (clock_gettime(CLOCK_MONOTONIC, &value) != 0) {
        perror("clock_gettime");
        exit(EXIT_FAILURE);
    }
    return (uint64_t)value.tv_sec * UINT64_C(1000000000) + (uint64_t)value.tv_nsec;
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

/* Zone anonyme alignée sur 2 Mio, avec le conseil de pages demandé pour ce seul
 * processus : MADV_HUGEPAGE (2 Mio) ou MADV_NOHUGEPAGE (4 Kio). */
static void *map_region(uint64_t bytes, int huge) {
    uint64_t rounded = (bytes + HUGE_SIZE - 1) / HUGE_SIZE * HUGE_SIZE;
    uint64_t span = rounded + HUGE_SIZE;
    unsigned char *raw = mmap(NULL, span, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (raw == MAP_FAILED) {
        perror("mmap");
        exit(EXIT_FAILURE);
    }
    uint64_t lead = (HUGE_SIZE - ((uint64_t)(uintptr_t)raw % HUGE_SIZE)) % HUGE_SIZE;
    if (lead) munmap(raw, lead);
    if (span - lead > rounded) munmap(raw + lead + rounded, span - lead - rounded);
    unsigned char *region = raw + lead;
    if (madvise(region, rounded, huge ? MADV_HUGEPAGE : MADV_NOHUGEPAGE) != 0) {
        perror("madvise");
        exit(EXIT_FAILURE);
    }
    return region;
}

static void unmap_region(void *region, uint64_t bytes) {
    munmap(region, (bytes + HUGE_SIZE - 1) / HUGE_SIZE * HUGE_SIZE);
}

/* Cycle aléatoire unique par l'algorithme de Sattolo : next[i] est le successeur de
 * i, et partir de n'importe quel élément visite les n éléments avant de revenir. */
static void build_random_cycle(uint64_t *next, uint64_t n, uint64_t *state) {
    for (uint64_t i = 0; i < n; ++i) next[i] = i;
    for (uint64_t i = n - 1; i > 0; --i) {
        uint64_t j = random_next(state) % i;   /* j < i : garantit un seul cycle */
        uint64_t temporary = next[i];
        next[i] = next[j];
        next[j] = temporary;
    }
}

static void build_sequential_list(uint64_t *next, uint64_t n) {
    for (uint64_t i = 0; i < n; ++i) next[i] = i + 1 < n ? i + 1 : 0;
}

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

static long minor_faults(void) {
    struct rusage usage;
    getrusage(RUSAGE_SELF, &usage);
    return usage.ru_minflt;
}

static int self_test(void) {
    uint64_t state = 1;
    static uint64_t next[4096];
    static unsigned char seen[4096];
    const uint64_t sizes[] = {2, 3, 7, 64, 1000, 4096};
    for (size_t s = 0; s < 6; ++s) {
        uint64_t n = sizes[s];
        build_random_cycle(next, n, &state);
        memset(seen, 0, n);
        uint64_t index = 0;
        for (uint64_t j = 0; j < n; ++j) {
            if (seen[index]) {
                fprintf(stderr, "self-test: cycle shorter than n=%" PRIu64 "\n", n);
                return EXIT_FAILURE;
            }
            seen[index] = 1;
            index = next[index];
        }
        if (index != 0 || chase(next, 3 % n, 5000) != reference_chase(next, 3 % n, 5000) ||
            independent(next, n, 42, 5000) != reference_independent(next, n, 42, 5000)) {
            fprintf(stderr, "self-test: walk differs for n=%" PRIu64 "\n", n);
            return EXIT_FAILURE;
        }
        build_sequential_list(next, n);
        if (chase(next, 0, 2 * n) != 2 * (n * (n - 1) / 2)) {
            fprintf(stderr, "self-test: sequential list differs for n=%" PRIu64 "\n", n);
            return EXIT_FAILURE;
        }
    }
    unsigned char page[3 * 4096];
    if (touch(page, sizeof(page), 1) != 3 || page[4096] != 1) return EXIT_FAILURE;
    puts("self-test: OK");
    return EXIT_SUCCESS;
}

/* ------------------------------------------------------------------ plan */

enum kind { KIND_CHASE_RANDOM, KIND_CHASE_SEQUENTIAL, KIND_INDEPENDENT, KIND_FAULT };

struct measure {
    const char *label;
    enum kind kind;
    uint64_t access_factor;
};

static const struct measure MEASURES[] = {
    {"chase_random", KIND_CHASE_RANDOM, 1},
    {"chase_random_double", KIND_CHASE_RANDOM, 2},
    {"chase_sequential", KIND_CHASE_SEQUENTIAL, 1},
    {"independent_random", KIND_INDEPENDENT, 1},
    {"independent_random_bis", KIND_INDEPENDENT, 1},
};
#define ACCESS_MEASURES (sizeof(MEASURES) / sizeof(MEASURES[0]))

struct sample {
    uint32_t round, position, measure, size_index;
    uint64_t bytes, accesses, start, salt;
    uint64_t elapsed_ns, second_elapsed_ns, result, expected;
    long faults;
    int cpu_before, cpu_after;
};

int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "--self-test") == 0) return self_test();

    const char *output_path = NULL, *meta_path = NULL, *core = "inconnu", *pages = NULL;
    uint64_t run_id = 0, seed = UINT64_C(20260919), rounds = 7, warmup_rounds = 1;
    uint64_t min_log2 = 12, max_log2 = 28, accesses_log2 = 20, chase_accesses_log2 = 18;
    uint64_t fault_small_log2 = 24, fault_large_log2 = 28;
    for (int i = 1; i + 1 < argc; i += 2) {
        if (strcmp(argv[i], "--output") == 0) output_path = argv[i + 1];
        else if (strcmp(argv[i], "--meta") == 0) meta_path = argv[i + 1];
        else if (strcmp(argv[i], "--core") == 0) core = argv[i + 1];
        else if (strcmp(argv[i], "--pages") == 0) pages = argv[i + 1];
        else if (strcmp(argv[i], "--run-id") == 0) run_id = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--seed") == 0) seed = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--rounds") == 0) rounds = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--warmup-rounds") == 0) warmup_rounds = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--min-log2") == 0) min_log2 = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--max-log2") == 0) max_log2 = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--accesses-log2") == 0) accesses_log2 = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--chase-accesses-log2") == 0) chase_accesses_log2 = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--fault-small-log2") == 0) fault_small_log2 = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--fault-large-log2") == 0) fault_large_log2 = parse_u64(argv[i + 1], argv[i]);
        else {
            fprintf(stderr, "unknown option %s\n", argv[i]);
            return EXIT_FAILURE;
        }
    }
    int huge = pages != NULL && strcmp(pages, "2m") == 0;
    if (argc % 2 == 0 || output_path == NULL || meta_path == NULL || run_id == 0 || pages == NULL ||
        (!huge && strcmp(pages, "4k") != 0) || rounds == 0 || warmup_rounds >= rounds ||
        min_log2 < 12 || min_log2 > max_log2 || max_log2 > 31 || accesses_log2 > 30 || chase_accesses_log2 > 30 ||
        fault_small_log2 < 21 || fault_large_log2 < fault_small_log2 || fault_large_log2 > 31) {
        fprintf(stderr, "usage: %s --self-test | --output FILE --meta FILE --run-id N --pages 4k|2m "
                        "[--core LABEL] [--seed N] [--rounds N] [--warmup-rounds N] [--min-log2 N] "
                        "[--max-log2 N] [--accesses-log2 N] [--chase-accesses-log2 N] [--fault-small-log2 N] "
                        "[--fault-large-log2 N]\n",
                argv[0]);
        return EXIT_FAILURE;
    }

    size_t size_count = (size_t)(max_log2 - min_log2 + 1);
    /* Les parcours dépendants, bien plus lents, font moins d'accès par échantillon. */
    uint64_t accesses = UINT64_C(1) << accesses_log2;
    uint64_t chase_accesses = UINT64_C(1) << chase_accesses_log2;
    uint64_t fault_sizes[2] = {UINT64_C(1) << fault_small_log2, UINT64_C(1) << fault_large_log2};

    /* Un cycle aléatoire et une liste séquentielle par taille, chacun dans sa zone,
     * construits et entièrement écrits avant la première mesure. */
    uint64_t *cycles[32], *lists[32];
    uint64_t state = seed ^ (run_id * GOLDEN);
    uint64_t allocated = 0;
    for (size_t s = 0; s < size_count; ++s) {
        uint64_t bytes = UINT64_C(1) << (min_log2 + s), n = bytes / 8;
        cycles[s] = map_region(bytes, huge);
        lists[s] = map_region(bytes, huge);
        uint64_t cycle_state = seed + s;   /* même cycle pour tous les processus */
        build_random_cycle(cycles[s], n, &cycle_state);
        build_sequential_list(lists[s], n);
        allocated += 2 * ((bytes + HUGE_SIZE - 1) / HUGE_SIZE * HUGE_SIZE);   /* zones arrondies à 2 Mio */
    }
    long huge_kb = anon_huge_pages_kb();

    /* Plan : accès (5 mesures × tailles) et défauts de page (2 tailles), mélangés à
     * chaque tour ; départ et sel tirés pour chaque échantillon. */
    size_t per_round = ACCESS_MEASURES * size_count + 2;
    size_t sample_count = per_round * (size_t)rounds;
    struct sample *samples = calloc(sample_count, sizeof(*samples));
    if (samples == NULL) {
        perror("calloc");
        return EXIT_FAILURE;
    }
    for (uint32_t round = 0; round < rounds; ++round) {
        struct sample *slice = samples + (size_t)round * per_round;
        for (size_t j = 0; j < per_round; ++j) {
            struct sample *s = &slice[j];
            *s = (struct sample){.round = round};
            if (j < ACCESS_MEASURES * size_count) {
                s->measure = (uint32_t)(j % ACCESS_MEASURES);
                s->size_index = (uint32_t)(j / ACCESS_MEASURES);
                s->bytes = UINT64_C(1) << (min_log2 + s->size_index);
                s->accesses = (MEASURES[s->measure].kind == KIND_INDEPENDENT ? accesses : chase_accesses) *
                              MEASURES[s->measure].access_factor;
            } else {
                s->measure = (uint32_t)ACCESS_MEASURES;   /* défauts de page */
                s->bytes = fault_sizes[j - ACCESS_MEASURES * size_count];
                s->accesses = s->bytes / PAGE_SIZE_4K;
            }
        }
        for (size_t j = per_round; j > 1; --j) {
            size_t other = (size_t)(random_next(&state) % j);
            struct sample temporary = slice[j - 1];
            slice[j - 1] = slice[other];
            slice[other] = temporary;
        }
        for (size_t j = 0; j < per_round; ++j) {
            slice[j].position = (uint32_t)j;
            slice[j].start = random_next(&state) % (slice[j].bytes / 8);
            slice[j].salt = random_next(&state);
        }
    }

    int first_cpu = sched_getcpu();
    struct rusage usage_before, usage_after;
    getrusage(RUSAGE_SELF, &usage_before);

    for (size_t i = 0; i < sample_count; ++i) {
        struct sample *s = &samples[i];
        if (s->measure == ACCESS_MEASURES) {
            /* Zone neuve : premier accès (défauts de page), puis second accès. */
            unsigned char *region = map_region(s->bytes, huge);
            long faults_before = minor_faults();
            s->cpu_before = sched_getcpu();
            uint64_t before = monotonic_ns();
            s->result = touch(region, s->bytes, 1);
            uint64_t middle = monotonic_ns();
            long faults_after = minor_faults();
            uint64_t second_before = monotonic_ns();
            s->result += touch(region, s->bytes, 2);
            uint64_t after = monotonic_ns();
            s->cpu_after = sched_getcpu();
            s->elapsed_ns = middle - before;
            s->second_elapsed_ns = after - second_before;
            s->faults = faults_after - faults_before;
            s->expected = 2 * (s->bytes / PAGE_SIZE_4K);
            for (uint64_t offset = 0; offset < s->bytes; offset += PAGE_SIZE_4K) {
                if (region[offset] != 2) s->expected = 0;   /* contenu inexact : échantillon invalide */
            }
            unmap_region(region, s->bytes);
            continue;
        }
        const struct measure *m = &MEASURES[s->measure];
        uint64_t n = s->bytes / 8;
        s->cpu_before = sched_getcpu();
        uint64_t before = monotonic_ns();
        if (m->kind == KIND_CHASE_RANDOM) s->result = chase(cycles[s->size_index], s->start, s->accesses);
        else if (m->kind == KIND_CHASE_SEQUENTIAL) s->result = chase(lists[s->size_index], s->start, s->accesses);
        else s->result = independent(cycles[s->size_index], n, s->salt, s->accesses);
        uint64_t after = monotonic_ns();
        s->cpu_after = sched_getcpu();
        s->elapsed_ns = after - before;
    }

    getrusage(RUSAGE_SELF, &usage_after);

    /* Références, après toutes les mesures. */
    int invalid = 0;
    for (size_t i = 0; i < sample_count; ++i) {
        struct sample *s = &samples[i];
        if (s->measure == ACCESS_MEASURES) {
            invalid += s->result != s->expected;
            continue;
        }
        const struct measure *m = &MEASURES[s->measure];
        if (m->kind == KIND_CHASE_RANDOM) s->expected = reference_chase(cycles[s->size_index], s->start, s->accesses);
        else if (m->kind == KIND_CHASE_SEQUENTIAL) s->expected = reference_chase(lists[s->size_index], s->start, s->accesses);
        else s->expected = reference_independent(cycles[s->size_index], s->bytes / 8, s->salt, s->accesses);
        invalid += s->result != s->expected;
    }

    FILE *file = fopen(output_path, "w");
    if (file == NULL) {
        perror(output_path);
        return EXIT_FAILURE;
    }
    fprintf(file, "run_id,core,pages,seed,sample,round,phase,position,label,bytes,accesses,start,salt,"
                  "elapsed_ns,second_elapsed_ns,faults,cpu_before,cpu_after,result,expected\n");
    for (size_t i = 0; i < sample_count; ++i) {
        const struct sample *s = &samples[i];
        const char *label = s->measure == ACCESS_MEASURES ? "page_fault_touch" : MEASURES[s->measure].label;
        fprintf(file,
                "%" PRIu64 ",%s,%s,%" PRIu64 ",%zu,%" PRIu32 ",%s,%" PRIu32 ",%s,%" PRIu64 ",%" PRIu64
                ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%ld,%d,%d,%" PRIu64 ",%" PRIu64 "\n",
                run_id, core, pages, seed, i, s->round, s->round < warmup_rounds ? "warmup" : "measure",
                s->position, label, s->bytes, s->accesses, s->start, s->salt, s->elapsed_ns,
                s->second_elapsed_ns, s->faults, s->cpu_before, s->cpu_after, s->result, s->expected);
    }
    int status = fclose(file) == 0 ? EXIT_SUCCESS : EXIT_FAILURE;

    FILE *meta = fopen(meta_path, "w");
    if (meta == NULL) {
        perror(meta_path);
        return EXIT_FAILURE;
    }
    fprintf(meta, "run_id,core,pages,first_cpu,allocated_bytes,anon_huge_pages_kb,huge_share,"
                  "involuntary_switches,invalid_samples\n");
    fprintf(meta, "%" PRIu64 ",%s,%s,%d,%" PRIu64 ",%ld,%.4f,%ld,%d\n", run_id, core, pages, first_cpu,
            allocated, huge_kb, huge_kb < 0 ? 0.0 : (double)huge_kb * 1024.0 / (double)allocated,
            usage_after.ru_nivcsw - usage_before.ru_nivcsw, invalid);
    if (fclose(meta) != 0) status = EXIT_FAILURE;

    for (size_t s = 0; s < size_count; ++s) {
        unmap_region(cycles[s], UINT64_C(1) << (min_log2 + s));
        unmap_region(lists[s], UINT64_C(1) << (min_log2 + s));
    }
    free(samples);
    if (invalid != 0) {
        fprintf(stderr, "%d échantillons invalides : les mesures ne sont pas valides\n", invalid);
        return EXIT_FAILURE;
    }
    return status;
}
