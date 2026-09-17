#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static uint64_t to_ns(struct timespec t) {
    return (uint64_t)t.tv_sec * UINT64_C(1000000000) + (uint64_t)t.tv_nsec;
}

static uint64_t read_ns(clockid_t clock_id) {
    struct timespec t;
    if (clock_gettime(clock_id, &t) != 0) {
        perror("clock_gettime");
        exit(EXIT_FAILURE);
    }
    return to_ns(t);
}

static uint64_t parse_u64(const char *text, const char *option) {
    char *end = NULL;
    errno = 0;
    unsigned long long value = strtoull(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0') {
        fprintf(stderr, "invalid value for %s: %s\n", option, text);
        exit(EXIT_FAILURE);
    }
    return (uint64_t)value;
}

static void print_resolution(const char *name, clockid_t clock_id) {
    struct timespec resolution;
    if (clock_getres(clock_id, &resolution) != 0) {
        perror("clock_getres");
        exit(EXIT_FAILURE);
    }
    printf("%s_resolution_ns=%" PRIu64 "\n", name, to_ns(resolution));
}

static int sleep_ns(uint64_t duration_ns) {
    struct timespec request = {
        .tv_sec = (time_t)(duration_ns / UINT64_C(1000000000)),
        .tv_nsec = (long)(duration_ns % UINT64_C(1000000000)),
    };
    while (clock_nanosleep(CLOCK_MONOTONIC, 0, &request, &request) == EINTR) {
    }
    return 0;
}

/* Burn approximately target_ns of process CPU time. The polling is deliberate:
 * this is an observation workload, not a computation-performance benchmark. */
static uint64_t burn_cpu(uint64_t target_ns) {
    uint64_t start = read_ns(CLOCK_PROCESS_CPUTIME_ID);
    uint64_t now = start;
    uint64_t state = UINT64_C(0x9e3779b97f4a7c15);
    uint64_t iterations = 0;

    do {
        for (unsigned int i = 0; i < 1024; ++i) {
            state = state * UINT64_C(6364136223846793005) + UINT64_C(1);
        }
        iterations += 1024;
        now = read_ns(CLOCK_PROCESS_CPUTIME_ID);
    } while (now - start < target_ns);

    /* Make the result observable and return useful validation information. */
    return iterations ^ state;
}

static void usage(const char *program) {
    fprintf(stderr,
            "usage: %s [--output FILE] [--pairs N] [--repetitions N] "
            "[--batch N] [--sleep-ms N] [--busy-ms N] [--seed N]\n",
            program);
}

int main(int argc, char **argv) {
    const char *output_path = "data/raw.csv";
    uint64_t pairs = 10000;
    uint64_t repetitions = 20;
    uint64_t batch = 1000;
    uint64_t sleep_ms = 100;
    uint64_t busy_ms = 50;
    uint64_t seed = UINT64_C(20260916);

    for (int i = 1; i < argc; ++i) {
        if (i + 1 >= argc) {
            usage(argv[0]);
            return EXIT_FAILURE;
        }
        const char *option = argv[i++];
        const char *value = argv[i];
        if (strcmp(option, "--output") == 0) output_path = value;
        else if (strcmp(option, "--pairs") == 0) pairs = parse_u64(value, option);
        else if (strcmp(option, "--repetitions") == 0) repetitions = parse_u64(value, option);
        else if (strcmp(option, "--batch") == 0) batch = parse_u64(value, option);
        else if (strcmp(option, "--sleep-ms") == 0) sleep_ms = parse_u64(value, option);
        else if (strcmp(option, "--busy-ms") == 0) busy_ms = parse_u64(value, option);
        else if (strcmp(option, "--seed") == 0) seed = parse_u64(value, option);
        else {
            usage(argv[0]);
            return EXIT_FAILURE;
        }
    }
    if (pairs == 0 || repetitions == 0 || batch == 0) {
        fputs("pairs, repetitions and batch must be positive\n", stderr);
        return EXIT_FAILURE;
    }

    print_resolution("monotonic", CLOCK_MONOTONIC);
    print_resolution("process_cpu", CLOCK_PROCESS_CPUTIME_ID);

    FILE *output = fopen(output_path, "w");
    if (output == NULL) {
        perror(output_path);
        return EXIT_FAILURE;
    }
    fprintf(output, "variant,sample,order,operations,elapsed_ns,cpu_ns,value_ns,result,seed,sleep_target_ns,busy_target_ns,batch_size\n");

    /* Naive measurement: the interval is comparable to the measurement itself. */
    for (uint64_t sample = 0; sample < pairs; ++sample) {
        uint64_t before = read_ns(CLOCK_MONOTONIC);
        uint64_t after = read_ns(CLOCK_MONOTONIC);
        fprintf(output, "consecutive_reads,%" PRIu64 ",0,1,%" PRIu64 ",0,%" PRIu64 ",0,%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 "\n",
                sample, after - before, after - before, seed,
                sleep_ms * UINT64_C(1000000), busy_ms * UINT64_C(1000000), batch);
    }

    /* Batch many reads so the two boundary reads are amortized. */
    for (uint64_t sample = 0; sample < repetitions; ++sample) {
        uint64_t before = read_ns(CLOCK_MONOTONIC);
        for (uint64_t operation = 0; operation < batch; ++operation) {
            (void)read_ns(CLOCK_MONOTONIC);
        }
        uint64_t after = read_ns(CLOCK_MONOTONIC);
        uint64_t elapsed = after - before;
        fprintf(output, "batched_reads,%" PRIu64 ",0,%" PRIu64 ",%" PRIu64 ",0,%.0f,0,%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 "\n",
                sample, batch, elapsed, (double)elapsed / (double)batch, seed,
                sleep_ms * UINT64_C(1000000), busy_ms * UINT64_C(1000000), batch);
    }

    /* Alternate the order deterministically to reduce a systematic order bias. */
    for (uint64_t sample = 0; sample < repetitions; ++sample) {
        int sleep_first = (int)((sample + seed) & 1U);
        for (int position = 0; position < 2; ++position) {
            int do_sleep = sleep_first ? position == 0 : position == 1;
            uint64_t elapsed_before = read_ns(CLOCK_MONOTONIC);
            uint64_t cpu_before = read_ns(CLOCK_PROCESS_CPUTIME_ID);
            uint64_t result;
            const char *variant;
            if (do_sleep) {
                variant = "sleep";
                result = (uint64_t)sleep_ns(sleep_ms * UINT64_C(1000000));
            } else {
                variant = "busy_cpu";
                result = burn_cpu(busy_ms * UINT64_C(1000000));
            }
            uint64_t cpu_after = read_ns(CLOCK_PROCESS_CPUTIME_ID);
            uint64_t elapsed_after = read_ns(CLOCK_MONOTONIC);
            uint64_t elapsed = elapsed_after - elapsed_before;
            uint64_t cpu = cpu_after - cpu_before;
            fprintf(output,
                    "%s,%" PRIu64 ",%d,1,%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 "\n",
                    variant, sample, position, elapsed, cpu, elapsed, result, seed,
                    sleep_ms * UINT64_C(1000000), busy_ms * UINT64_C(1000000), batch);
        }
    }

    if (fclose(output) != 0) {
        perror("fclose");
        return EXIT_FAILURE;
    }
    printf("raw_data=%s\n", output_path);
    printf("seed=%" PRIu64 "\n", seed);
    return EXIT_SUCCESS;
}
