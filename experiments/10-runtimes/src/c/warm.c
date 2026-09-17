#define _GNU_SOURCE

/* E2, partie 2 : trajectoire d'échauffement, référence compilée en C. À chaque pas, une
 * chaîne de hachage puis un produit scalaire strict sur n éléments, chronométrés un par un
 * dès le premier pas du processus. Mêmes boucles que E1. */

#include <inttypes.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define NOINLINE __attribute__((noinline))
#define K UINT64_C(0x9e3779b97f4a7c15)

static NOINLINE uint64_t hash_chain(const uint64_t *u, size_t n, uint64_t h) {
    for (size_t i = 0; i < n; ++i) h = (h ^ u[i]) * K;
    return h;
}

static NOINLINE double dot(const double *a, const double *b, size_t n) {
    double s = 0.0;
    for (size_t i = 0; i < n; ++i) s += a[i] * b[i];
    return s;
}

/* CPU autorisés (Cpus_allowed_list), virgules remplacées par « ; » pour le CSV. */
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

int main(int argc, char **argv) {
    const char *input = NULL, *output = NULL, *meta = NULL, *mode = "c", *generate = NULL;
    unsigned long run_id = 0, steps = 300, n_log2 = 16, count = 0, seed = 20260923;
    for (int i = 1; i + 1 < argc; i += 2) {
        const char *o = argv[i], *v = argv[i + 1];
        if (!strcmp(o, "--input")) input = v;
        else if (!strcmp(o, "--output")) output = v;
        else if (!strcmp(o, "--meta")) meta = v;
        else if (!strcmp(o, "--mode")) mode = v;
        else if (!strcmp(o, "--generate")) generate = v;
        else if (!strcmp(o, "--run-id")) run_id = strtoul(v, NULL, 10);
        else if (!strcmp(o, "--steps")) steps = strtoul(v, NULL, 10);
        else if (!strcmp(o, "--n-log2")) n_log2 = strtoul(v, NULL, 10);
        else if (!strcmp(o, "--count")) count = strtoul(v, NULL, 10);
        else if (!strcmp(o, "--seed")) seed = strtoul(v, NULL, 10);
    }
    if (generate) {   /* données communes : count entiers de 64 bits, SplitMix64 */
        FILE *f = fopen(generate, "wb");
        uint64_t state = seed;
        for (unsigned long i = 0; f && i < count; ++i) {
            uint64_t z = (state += K);
            z = (z ^ (z >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
            z = (z ^ (z >> 27)) * UINT64_C(0x94d049bb133111eb);
            z ^= z >> 31;
            if (fwrite(&z, sizeof z, 1, f) != 1) return EXIT_FAILURE;
        }
        return f && fclose(f) == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
    }
    if (!input || !output || !meta || run_id == 0 || n_log2 > 22) {
        fprintf(stderr, "usage : warm --input F --output CSV --meta CSV --run-id N --mode M [--steps S] [--n-log2 L]\n");
        return EXIT_FAILURE;
    }
    size_t n = (size_t)1 << n_log2;
    uint64_t *u = malloc(2 * n * sizeof *u);
    double *a = malloc(n * sizeof *a), *b = malloc(n * sizeof *b);
    uint64_t *elapsed = malloc(2 * steps * sizeof *elapsed), *result = malloc(2 * steps * sizeof *result);
    int *cpus = malloc(2 * steps * sizeof *cpus);
    FILE *f = fopen(input, "rb");
    if (!u || !a || !b || !elapsed || !result || !cpus || !f || fread(u, sizeof *u, 2 * n, f) != 2 * n) {
        fprintf(stderr, "lecture impossible\n");
        return EXIT_FAILURE;
    }
    fclose(f);
    for (size_t i = 0; i < n; ++i) {
        a[i] = (double)(u[i] >> 11) * 0x1.0p-53;
        b[i] = (double)(u[n + i] >> 11) * 0x1.0p-53;
    }
    for (unsigned long s = 0; s < steps; ++s) {
        uint64_t t0 = monotonic_ns();
        result[2 * s] = hash_chain(u, n, 0);
        uint64_t t1 = monotonic_ns();
        double d = dot(a, b, n);
        uint64_t t2 = monotonic_ns();
        memcpy(&result[2 * s + 1], &d, sizeof d);
        elapsed[2 * s] = t1 - t0;
        elapsed[2 * s + 1] = t2 - t1;
        cpus[2 * s] = cpus[2 * s + 1] = sched_getcpu();
    }
    FILE *out = fopen(output, "w");
    if (!out) return EXIT_FAILURE;
    fprintf(out, "run_id,mode,step,workload,elements,elapsed_ns,result,cpu\n");
    for (unsigned long s = 0; s < 2 * steps; ++s)
        fprintf(out, "%lu,%s,%lu,%s,%zu,%" PRIu64 ",%016" PRIx64 ",%d\n", run_id, mode, s / 2,
                s % 2 ? "dot" : "hash_chain", n, elapsed[s], result[s], cpus[s]);
    FILE *m = fopen(meta, "w");
    if (!m || fclose(out) != 0) return EXIT_FAILURE;
    char cpus_allowed[64];
    allowed_cpus(cpus_allowed, sizeof cpus_allowed);
    fprintf(m, "run_id,mode,runtime,jit,cpus_allowed\n%lu,%s,gcc %s,none,%s\n", run_id, mode, __VERSION__, cpus_allowed);
    return fclose(m) == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
