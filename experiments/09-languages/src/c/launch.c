#define _GNU_SOURCE

/* Durée de démarrage : du lancement d'un programme (posix_spawn) à la fin de son
 * attente (wait4), pour un programme qui se termine aussitôt (--noop). Les commandes
 * sont lancées dans un ordre tiré au hasard à chaque répétition. */

#include <inttypes.h>
#include <spawn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <time.h>

extern char **environ;

static uint64_t monotonic_ns(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (uint64_t)t.tv_sec * UINT64_C(1000000000) + (uint64_t)t.tv_nsec;
}

static uint64_t xorshift(uint64_t *state) {
    *state ^= *state >> 12;
    *state ^= *state << 25;
    *state ^= *state >> 27;
    return *state * UINT64_C(2685821657736338717);
}

int main(int argc, char **argv) {
    /* usage : launch SORTIE REPETITIONS GRAINE nom "commande arguments" [nom "commande"...] */
    if (argc < 6 || (argc - 4) % 2 != 0) {
        fprintf(stderr, "usage : launch SORTIE REPETITIONS GRAINE NOM COMMANDE [NOM COMMANDE...]\n");
        return EXIT_FAILURE;
    }
    const char *output = argv[1];
    long reps = strtol(argv[2], NULL, 10);
    uint64_t state = strtoull(argv[3], NULL, 10) | 1;
    int commands = (argc - 4) / 2;
    char ***argvs = calloc((size_t)commands, sizeof *argvs);
    for (int c = 0; c < commands; ++c) {
        char *copy = strdup(argv[5 + 2 * c]);
        argvs[c] = calloc(32, sizeof **argvs);
        int k = 0;
        for (char *token = strtok(copy, " "); token && k < 31; token = strtok(NULL, " ")) argvs[c][k++] = token;
    }
    FILE *out = fopen(output, "w");
    if (!out) return EXIT_FAILURE;
    fprintf(out, "repetition,position,label,elapsed_ns,user_us,system_us,max_rss_kib,status\n");
    int *order = calloc((size_t)commands, sizeof *order);
    for (long r = 0; r < reps; ++r) {
        for (int c = 0; c < commands; ++c) order[c] = c;
        for (int j = commands; j > 1; --j) {
            int other = (int)(xorshift(&state) % (uint64_t)j), t = order[j - 1];
            order[j - 1] = order[other];
            order[other] = t;
        }
        for (int p = 0; p < commands; ++p) {
            int c = order[p];
            pid_t pid;
            struct rusage usage;
            int status = -1;
            uint64_t t0 = monotonic_ns();
            if (posix_spawn(&pid, argvs[c][0], NULL, NULL, argvs[c], environ) != 0) return EXIT_FAILURE;
            if (wait4(pid, &status, 0, &usage) < 0) return EXIT_FAILURE;
            uint64_t t1 = monotonic_ns();
            fprintf(out, "%ld,%d,%s,%" PRIu64 ",%ld,%ld,%ld,%d\n", r, p, argv[4 + 2 * c], t1 - t0,
                    usage.ru_utime.tv_sec * 1000000L + usage.ru_utime.tv_usec,
                    usage.ru_stime.tv_sec * 1000000L + usage.ru_stime.tv_usec, usage.ru_maxrss, status);
        }
    }
    return fclose(out) == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
