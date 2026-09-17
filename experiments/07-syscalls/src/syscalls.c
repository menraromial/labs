#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <sys/uio.h>
#include <time.h>
#include <unistd.h>

#if defined(__GNUC__) || defined(__clang__)
#define NOINLINE __attribute__((noinline))
#else
#define NOINLINE
#endif

#define RECORD_SIZE 16
#define MANUAL_BUFFER 4096
#define LARGE_STDIO_BUFFER 65536
#define NONEXISTENT_SYSCALL 100000   /* au-delà du dernier numéro : le noyau répond ENOSYS */

/* ------------------------------------------------------------------ partie 1 : entrée dans le noyau */

static NOINLINE long plain_function(long value) {
    return value + 1;
}

static NOINLINE uint64_t loop_function(uint64_t calls) {
    uint64_t sum = 0;
    for (uint64_t i = 0; i < calls; ++i) sum += (uint64_t)plain_function((long)i);
    return sum;
}

/* clock_gettime par la bibliothèque C : servi par le vDSO, sans entrer dans le noyau. */
static NOINLINE uint64_t loop_vdso_clock(uint64_t calls) {
    struct timespec ts;
    uint64_t ok = 0;
    for (uint64_t i = 0; i < calls; ++i) ok += clock_gettime(CLOCK_MONOTONIC, &ts) == 0;
    return ok;
}

/* Même travail, mais par un vrai appel système. */
static NOINLINE uint64_t loop_syscall_clock(uint64_t calls) {
    struct timespec ts;
    uint64_t ok = 0;
    for (uint64_t i = 0; i < calls; ++i) ok += syscall(SYS_clock_gettime, CLOCK_MONOTONIC, &ts) == 0;
    return ok;
}

static NOINLINE uint64_t loop_getppid(uint64_t calls, unsigned per_iteration) {
    uint64_t sum = 0;
    for (uint64_t i = 0; i < calls; ++i) {
        for (unsigned k = 0; k < per_iteration; ++k) sum += (uint64_t)syscall(SYS_getppid);
    }
    return sum;
}

/* Numéro d'appel inexistant : entrée et sortie du noyau, presque aucun travail. */
static NOINLINE uint64_t loop_enosys(uint64_t calls) {
    uint64_t count = 0;
    for (uint64_t i = 0; i < calls; ++i) count += syscall(NONEXISTENT_SYSCALL) == -1 && errno == ENOSYS;
    return count;
}

/* ------------------------------------------------------------------ partie 2 : lots */

static NOINLINE uint64_t write_chunks(int fd, const unsigned char *buffer, uint64_t chunk, uint64_t calls) {
    uint64_t bytes = 0;
    for (uint64_t i = 0; i < calls; ++i) {
        ssize_t done = write(fd, buffer, chunk);
        if (done < 0) return 0;
        bytes += (uint64_t)done;
    }
    return bytes;
}

static NOINLINE uint64_t read_chunks(int fd, unsigned char *buffer, uint64_t chunk, uint64_t calls) {
    uint64_t bytes = 0;
    for (uint64_t i = 0; i < calls; ++i) {
        ssize_t done = read(fd, buffer, chunk);
        if (done < 0) return 0;
        bytes += (uint64_t)done;
    }
    return bytes;
}

/* ------------------------------------------------------------------ partie 3 : tampon utilisateur */

static void make_record(unsigned char *record, uint64_t index) {
    memcpy(record, &index, sizeof(index));
    uint64_t check = index * UINT64_C(0x9e3779b97f4a7c15);
    memcpy(record + 8, &check, sizeof(check));
}

static NOINLINE uint64_t records_write_each(int fd, uint64_t records) {
    unsigned char record[RECORD_SIZE];
    uint64_t bytes = 0;
    for (uint64_t i = 0; i < records; ++i) {
        make_record(record, i);
        ssize_t done = write(fd, record, RECORD_SIZE);
        if (done < 0) return 0;
        bytes += (uint64_t)done;
    }
    return bytes;
}

static NOINLINE uint64_t records_stdio(FILE *stream, uint64_t records) {
    unsigned char record[RECORD_SIZE];
    uint64_t bytes = 0;
    for (uint64_t i = 0; i < records; ++i) {
        make_record(record, i);
        bytes += RECORD_SIZE * fwrite(record, RECORD_SIZE, 1, stream);
    }
    if (fflush(stream) != 0) return 0;
    return bytes;
}

static NOINLINE uint64_t records_manual_batch(int fd, uint64_t records) {
    unsigned char buffer[MANUAL_BUFFER];
    size_t used = 0;
    uint64_t bytes = 0;
    for (uint64_t i = 0; i < records; ++i) {
        make_record(buffer + used, i);
        used += RECORD_SIZE;
        if (used == MANUAL_BUFFER) {
            ssize_t done = write(fd, buffer, used);
            if (done < 0) return 0;
            bytes += (uint64_t)done;
            used = 0;
        }
    }
    if (used) {
        ssize_t done = write(fd, buffer, used);
        if (done < 0) return 0;
        bytes += (uint64_t)done;
    }
    return bytes;
}

/* ------------------------------------------------------------------ plan */

enum kind {
    KIND_FUNCTION, KIND_VDSO_CLOCK, KIND_SYSCALL_CLOCK, KIND_GETPPID, KIND_GETPPID_DOUBLE, KIND_ENOSYS,
    KIND_WRITE_NULL, KIND_READ_ZERO, KIND_RECORDS_EACH, KIND_RECORDS_STDIO, KIND_RECORDS_STDIO_LARGE,
    KIND_RECORDS_MANUAL
};

struct measure {
    const char *label;
    enum kind kind;
    uint64_t chunk;     /* taille de bloc (partie 2) */
    uint64_t calls;     /* appels, blocs ou enregistrements par échantillon */
};

struct sample {
    uint32_t round, position, measure;
    uint64_t elapsed_ns, result, expected;
    uint64_t read_syscalls, write_syscalls;   /* depuis /proc/self/io */
    uint64_t user_us, system_us;             /* depuis getrusage */
    int cpu_before, cpu_after;
};

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

/* Compteurs d'appels read et write du processus, tenus par le noyau. */
static void io_counters(uint64_t *reads, uint64_t *writes) {
    char line[128];
    FILE *file = fopen("/proc/self/io", "r");
    *reads = *writes = 0;
    if (file == NULL) return;
    while (fgets(line, sizeof(line), file) != NULL) {
        unsigned long long value;
        if (sscanf(line, "syscr: %llu", &value) == 1) *reads = value;
        else if (sscanf(line, "syscw: %llu", &value) == 1) *writes = value;
    }
    fclose(file);
}

static uint64_t cpu_time_us(const struct timeval *time) {
    return (uint64_t)time->tv_sec * 1000000 + (uint64_t)time->tv_usec;
}

int main(int argc, char **argv) {
    const char *output_path = NULL, *meta_path = NULL, *core = "inconnu";
    uint64_t run_id = 0, seed = UINT64_C(20260920), rounds = 11, warmup_rounds = 1, scale_log2 = 0;
    int self_test = argc == 2 && strcmp(argv[1], "--self-test") == 0;
    for (int i = 1; !self_test && i + 1 < argc; i += 2) {
        if (strcmp(argv[i], "--output") == 0) output_path = argv[i + 1];
        else if (strcmp(argv[i], "--meta") == 0) meta_path = argv[i + 1];
        else if (strcmp(argv[i], "--core") == 0) core = argv[i + 1];
        else if (strcmp(argv[i], "--run-id") == 0) run_id = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--seed") == 0) seed = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--rounds") == 0) rounds = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--warmup-rounds") == 0) warmup_rounds = parse_u64(argv[i + 1], argv[i]);
        else if (strcmp(argv[i], "--scale-log2") == 0) scale_log2 = parse_u64(argv[i + 1], argv[i]);
        else {
            fprintf(stderr, "unknown option %s\n", argv[i]);
            return EXIT_FAILURE;
        }
    }
    if (!self_test && (argc % 2 == 0 || output_path == NULL || meta_path == NULL || run_id == 0 ||
                       rounds == 0 || warmup_rounds >= rounds || scale_log2 > 12)) {
        fprintf(stderr, "usage: %s --self-test | --output FILE --meta FILE --run-id N [--core LABEL] "
                        "[--seed N] [--rounds N] [--warmup-rounds N] [--scale-log2 N]\n", argv[0]);
        return EXIT_FAILURE;
    }

    /* Plan des mesures. --scale-log2 divise les nombres d'appels (vérifications rapides). */
    struct measure measures[64];
    size_t count = 0;
    uint64_t base = UINT64_C(1) << (20 - scale_log2);
    measures[count++] = (struct measure){"function_call", KIND_FUNCTION, 0, base};
    measures[count++] = (struct measure){"vdso_clock_gettime", KIND_VDSO_CLOCK, 0, base};
    measures[count++] = (struct measure){"syscall_clock_gettime", KIND_SYSCALL_CLOCK, 0, base >> 2};
    measures[count++] = (struct measure){"syscall_getppid", KIND_GETPPID, 0, base >> 2};
    measures[count++] = (struct measure){"syscall_getppid_bis", KIND_GETPPID, 0, base >> 2};
    measures[count++] = (struct measure){"syscall_getppid_double", KIND_GETPPID_DOUBLE, 0, base >> 2};
    measures[count++] = (struct measure){"syscall_enosys", KIND_ENOSYS, 0, base >> 2};
    for (uint64_t chunk = 1; chunk <= UINT64_C(1) << 20; chunk <<= 2) {
        /* 2^16 appels jusqu'à 4 Kio, puis 256 Mio au total ; divisés par le facteur d'échelle. */
        uint64_t calls = chunk <= 4096 ? (UINT64_C(1) << 16) : (UINT64_C(1) << 28) / chunk;
        calls >>= scale_log2;
        if (calls == 0) calls = 1;
        measures[count++] = (struct measure){"write_dev_null", KIND_WRITE_NULL, chunk, calls};
        measures[count++] = (struct measure){"read_dev_zero", KIND_READ_ZERO, chunk, calls};
    }
    uint64_t records = base;
    measures[count++] = (struct measure){"records_write_each", KIND_RECORDS_EACH, RECORD_SIZE, records >> 2};
    measures[count++] = (struct measure){"records_stdio_default", KIND_RECORDS_STDIO, RECORD_SIZE, records};
    measures[count++] = (struct measure){"records_stdio_64k", KIND_RECORDS_STDIO_LARGE, RECORD_SIZE, records};
    measures[count++] = (struct measure){"records_manual_4k", KIND_RECORDS_MANUAL, RECORD_SIZE, records};

    int null_fd = open("/dev/null", O_WRONLY | O_CLOEXEC);
    int zero_fd = open("/dev/zero", O_RDONLY | O_CLOEXEC);
    FILE *stdio_default = fdopen(open("/dev/null", O_WRONLY | O_CLOEXEC), "wb");
    FILE *stdio_large = fdopen(open("/dev/null", O_WRONLY | O_CLOEXEC), "wb");
    static char large_buffer[LARGE_STDIO_BUFFER];
    unsigned char *buffer = aligned_alloc(4096, UINT64_C(1) << 20);
    if (null_fd < 0 || zero_fd < 0 || stdio_default == NULL || stdio_large == NULL || buffer == NULL ||
        setvbuf(stdio_large, large_buffer, _IOFBF, sizeof(large_buffer)) != 0) {
        perror("préparation");
        return EXIT_FAILURE;
    }
    memset(buffer, 0xA5, UINT64_C(1) << 20);   /* pages du tampon touchées avant la mesure */

    if (self_test) {
        uint64_t r0, w0, r1, w1;
        io_counters(&r0, &w0);
        int ok = loop_function(10) == 55 && loop_vdso_clock(10) == 10 && loop_syscall_clock(10) == 10 &&
                 loop_getppid(10, 1) == 10 * (uint64_t)getppid() &&
                 loop_getppid(10, 2) == 20 * (uint64_t)getppid() && loop_enosys(10) == 10 &&
                 write_chunks(null_fd, buffer, 4096, 3) == 3 * 4096 && read_chunks(zero_fd, buffer, 4096, 3) == 3 * 4096 &&
                 buffer[4095] == 0 && records_write_each(null_fd, 7) == 7 * RECORD_SIZE &&
                 records_stdio(stdio_default, 1000) == 1000 * RECORD_SIZE &&
                 records_manual_batch(null_fd, 1000) == 1000 * RECORD_SIZE;
        io_counters(&r1, &w1);
        /* 3 lectures ; écritures : 3 + 7 + au moins 1 (stdio) + 4 (1000 enregistrements par 256) */
        ok = ok && r1 - r0 >= 3 && w1 - w0 >= 3 + 7 + 1 + 4;
        puts(ok ? "self-test: OK" : "self-test: FAILED");
        return ok ? EXIT_SUCCESS : EXIT_FAILURE;
    }

    size_t sample_count = count * (size_t)rounds;
    struct sample *samples = calloc(sample_count, sizeof(*samples));
    if (samples == NULL) {
        perror("calloc");
        return EXIT_FAILURE;
    }
    uint64_t state = seed ^ (run_id * UINT64_C(0x9e3779b97f4a7c15));
    if (state == 0) state = 1;
    for (uint32_t round = 0; round < rounds; ++round) {
        struct sample *slice = samples + (size_t)round * count;
        for (size_t j = 0; j < count; ++j) slice[j] = (struct sample){.round = round, .measure = (uint32_t)j};
        for (size_t j = count; j > 1; --j) {
            size_t other = (size_t)(random_next(&state) % j);
            struct sample temporary = slice[j - 1];
            slice[j - 1] = slice[other];
            slice[other] = temporary;
        }
        for (size_t j = 0; j < count; ++j) slice[j].position = (uint32_t)j;
    }

    int first_cpu = sched_getcpu();
    long ppid = (long)getppid();
    for (size_t i = 0; i < sample_count; ++i) {
        struct sample *s = &samples[i];
        const struct measure *m = &measures[s->measure];
        struct rusage usage_before, usage_after;
        uint64_t reads_before, writes_before, reads_after, writes_after;
        io_counters(&reads_before, &writes_before);
        getrusage(RUSAGE_SELF, &usage_before);
        s->cpu_before = sched_getcpu();
        uint64_t before = monotonic_ns();
        switch (m->kind) {
        case KIND_FUNCTION: s->result = loop_function(m->calls); s->expected = m->calls * (m->calls + 1) / 2; break;
        case KIND_VDSO_CLOCK: s->result = loop_vdso_clock(m->calls); s->expected = m->calls; break;
        case KIND_SYSCALL_CLOCK: s->result = loop_syscall_clock(m->calls); s->expected = m->calls; break;
        case KIND_GETPPID: s->result = loop_getppid(m->calls, 1); s->expected = m->calls * (uint64_t)ppid; break;
        case KIND_GETPPID_DOUBLE: s->result = loop_getppid(m->calls, 2); s->expected = 2 * m->calls * (uint64_t)ppid; break;
        case KIND_ENOSYS: s->result = loop_enosys(m->calls); s->expected = m->calls; break;
        case KIND_WRITE_NULL: s->result = write_chunks(null_fd, buffer, m->chunk, m->calls); s->expected = m->chunk * m->calls; break;
        case KIND_READ_ZERO: s->result = read_chunks(zero_fd, buffer, m->chunk, m->calls); s->expected = m->chunk * m->calls; break;
        case KIND_RECORDS_EACH: s->result = records_write_each(null_fd, m->calls); s->expected = RECORD_SIZE * m->calls; break;
        case KIND_RECORDS_STDIO: s->result = records_stdio(stdio_default, m->calls); s->expected = RECORD_SIZE * m->calls; break;
        case KIND_RECORDS_STDIO_LARGE: s->result = records_stdio(stdio_large, m->calls); s->expected = RECORD_SIZE * m->calls; break;
        case KIND_RECORDS_MANUAL: s->result = records_manual_batch(null_fd, m->calls); s->expected = RECORD_SIZE * m->calls; break;
        }
        uint64_t after = monotonic_ns();
        s->cpu_after = sched_getcpu();
        getrusage(RUSAGE_SELF, &usage_after);
        io_counters(&reads_after, &writes_after);
        s->elapsed_ns = after - before;
        s->user_us = cpu_time_us(&usage_after.ru_utime) - cpu_time_us(&usage_before.ru_utime);
        s->system_us = cpu_time_us(&usage_after.ru_stime) - cpu_time_us(&usage_before.ru_stime);
        /* La lecture de /proc/self/io faite avant la mesure compte elle-même un appel read. */
        s->read_syscalls = reads_after - reads_before;
        s->write_syscalls = writes_after - writes_before;
        if (m->kind == KIND_READ_ZERO && buffer[m->chunk - 1] != 0) s->expected = 0;   /* contenu inexact */
        if (m->kind == KIND_READ_ZERO) memset(buffer, 0xA5, m->chunk);
    }

    FILE *file = fopen(output_path, "w");
    if (file == NULL) {
        perror(output_path);
        return EXIT_FAILURE;
    }
    fprintf(file, "run_id,core,seed,sample,round,phase,position,label,chunk,calls,elapsed_ns,user_us,system_us,"
                  "read_syscalls,write_syscalls,cpu_before,cpu_after,result,expected\n");
    int invalid = 0;
    for (size_t i = 0; i < sample_count; ++i) {
        const struct sample *s = &samples[i];
        const struct measure *m = &measures[s->measure];
        invalid += s->result != s->expected;
        fprintf(file,
                "%" PRIu64 ",%s,%" PRIu64 ",%zu,%" PRIu32 ",%s,%" PRIu32 ",%s,%" PRIu64 ",%" PRIu64 ",%" PRIu64
                ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%d,%d,%" PRIu64 ",%" PRIu64 "\n",
                run_id, core, seed, i, s->round, s->round < warmup_rounds ? "warmup" : "measure", s->position,
                m->label, m->chunk, m->calls, s->elapsed_ns, s->user_us, s->system_us, s->read_syscalls,
                s->write_syscalls, s->cpu_before, s->cpu_after, s->result, s->expected);
    }
    int status = fclose(file) == 0 ? EXIT_SUCCESS : EXIT_FAILURE;

    struct rusage usage;
    getrusage(RUSAGE_SELF, &usage);
    FILE *meta = fopen(meta_path, "w");
    if (meta == NULL) {
        perror(meta_path);
        return EXIT_FAILURE;
    }
    fprintf(meta, "run_id,core,first_cpu,stdio_default_buffer,involuntary_switches,invalid_samples\n");
    /* Taille du tampon choisie par la bibliothèque C pour /dev/null : lue sur le flux lui-même. */
    fprintf(meta, "%" PRIu64 ",%s,%d,%zu,%ld,%d\n", run_id, core, first_cpu,
            (size_t)(stdio_default->_IO_buf_end - stdio_default->_IO_buf_base), usage.ru_nivcsw, invalid);
    if (fclose(meta) != 0) status = EXIT_FAILURE;
    free(samples);
    if (invalid != 0) {
        fprintf(stderr, "%d échantillons invalides : les mesures ne sont pas valides\n", invalid);
        return EXIT_FAILURE;
    }
    return status;
}
