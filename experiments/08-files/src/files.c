#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#define PAGE 4096
#define WORDS (PAGE / 8)
#define SEQ_CHUNK (128 * 1024)
#define BATCHES 5                          /* lots de 1, 4, 16, 64 et 256 enregistrements */
#define WRITE_KEY UINT64_C(0x5752495445)   /* contenu des écritures, distinct du fichier lu */

/* ------------------------------------------------------------------ contenu vérifiable */

static uint64_t mix64(uint64_t x) {
    x += UINT64_C(0x9e3779b97f4a7c15);
    x = (x ^ (x >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
    x = (x ^ (x >> 27)) * UINT64_C(0x94d049bb133111eb);
    return x ^ (x >> 31);
}

/* Bloc de 4 Kio : 512 mots pseudo-aléatoires déterminés par la clé et l'indice du bloc. */
static void fill_block(unsigned char *block, uint64_t key, uint64_t index) {
    for (uint64_t w = 0; w < WORDS; ++w) {
        uint64_t value = mix64(key + index * WORDS + w);
        memcpy(block + 8 * w, &value, sizeof(value));
    }
}

/* Somme pondérée : un bloc nul, décalé ou d'un autre indice donne une autre valeur. */
static uint64_t block_sum(const unsigned char *block) {
    uint64_t sum = 0;
    for (uint64_t w = 0; w < WORDS; ++w) {
        uint64_t value;
        memcpy(&value, block + 8 * w, sizeof(value));
        sum += value * (2 * w + 1);
    }
    return sum;
}

/* ------------------------------------------------------------------ outils */

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

static void die(const char *what) {
    perror(what);
    exit(EXIT_FAILURE);
}

static int open_or_die(const char *path, int flags) {
    int fd = open(path, flags | O_CLOEXEC, 0644);
    if (fd < 0) die(path);
    return fd;
}

static unsigned char *page_aligned(size_t bytes) {
    unsigned char *memory = aligned_alloc(PAGE, (bytes + PAGE - 1) / PAGE * PAGE);
    if (memory == NULL) die("aligned_alloc");
    memset(memory, 0, bytes);
    return memory;
}

/* Compteurs du processus tenus par le noyau (/proc/self/io). */
struct io_counts {
    uint64_t syscr, syscw, read_bytes, write_bytes, cancelled_write_bytes;
};

static void io_counters(struct io_counts *counts) {
    char line[128];
    memset(counts, 0, sizeof(*counts));
    FILE *file = fopen("/proc/self/io", "r");
    if (file == NULL) return;
    while (fgets(line, sizeof(line), file) != NULL) {
        unsigned long long value;
        if (sscanf(line, "syscr: %llu", &value) == 1) counts->syscr = value;
        else if (sscanf(line, "syscw: %llu", &value) == 1) counts->syscw = value;
        else if (sscanf(line, "read_bytes: %llu", &value) == 1) counts->read_bytes = value;
        else if (sscanf(line, "write_bytes: %llu", &value) == 1) counts->write_bytes = value;
        else if (sscanf(line, "cancelled_write_bytes: %llu", &value) == 1) counts->cancelled_write_bytes = value;
    }
    fclose(file);
}

/* Compteurs de toute la machine : requêtes du périphérique NVMe et transactions du journal ext4.
 * D'autres processus peuvent y contribuer ; ils servent de preuve de mécanisme, pas de durée. */
struct system_counts {
    uint64_t device_reads, device_read_sectors, device_writes, device_write_sectors, device_flushes, journal_commits;
};

static const char *device_stat_path, *journal_info_path;

static void system_counters(struct system_counts *counts) {
    memset(counts, 0, sizeof(*counts));
    FILE *file = fopen(device_stat_path, "r");
    if (file != NULL) {
        unsigned long long field[17] = {0};
        int got = 0;
        while (got < 17 && fscanf(file, "%llu", &field[got]) == 1) ++got;
        fclose(file);
        counts->device_reads = field[0];
        counts->device_read_sectors = field[2];   /* secteurs de 512 octets */
        counts->device_writes = field[4];
        counts->device_write_sectors = field[6];
        counts->device_flushes = got >= 16 ? field[15] : 0;
    }
    file = fopen(journal_info_path, "r");
    if (file != NULL) {
        unsigned long long transactions;
        if (fscanf(file, "%llu transactions", &transactions) == 1) counts->journal_commits = transactions;
        fclose(file);
    }
}

/* Pages du fichier présentes dans le cache de pages, selon mincore sur une projection jamais lue. */
static uint64_t resident_pages(void *mapping, size_t bytes, unsigned char *vector) {
    if (mincore(mapping, bytes, vector) != 0) die("mincore");
    uint64_t pages = 0;
    for (size_t i = 0; i < bytes / PAGE; ++i) pages += vector[i] & 1;
    return pages;
}

/* ------------------------------------------------------------------ fichier lu */

static void create_read_file(const char *path, uint64_t pages) {
    int fd = open_or_die(path, O_WRONLY | O_CREAT | O_TRUNC);
    unsigned char *chunk = page_aligned(256 * PAGE);
    for (uint64_t first = 0; first < pages; first += 256) {
        uint64_t count = pages - first < 256 ? pages - first : 256;
        for (uint64_t i = 0; i < count; ++i) fill_block(chunk + i * PAGE, 0, first + i);
        if (pwrite(fd, chunk, count * PAGE, (off_t)(first * PAGE)) != (ssize_t)(count * PAGE)) die("pwrite");
    }
    if (fsync(fd) != 0) die("fsync");
    posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED);   /* rend la mémoire : pages propres, notre fichier seul */
    close(fd);
    free(chunk);
}

/* ------------------------------------------------------------------ plan */

enum kind { KIND_SEQ, KIND_RAND, KIND_WRITE };
enum cache { CACHE_WARM, CACHE_COLD, CACHE_DIRECT, CACHE_NONE };
enum sync { SYNC_NONE, SYNC_FSYNC, SYNC_FDATASYNC, SYNC_ODSYNC };
enum target { TARGET_EXT4, TARGET_TMPFS };

struct file_state {
    const char *name;
    enum target target;
    int append;
    int dsync;
    int fd, readback_fd;
    uint64_t records;       /* taille initiale (réécriture) en enregistrements */
    uint64_t init_chunk;    /* enregistrements par écriture d'initialisation : fixe la taille des folios */
};

struct measure {
    const char *label;
    enum kind kind;
    enum cache cache;
    enum sync sync;
    struct file_state *file;
    uint64_t per_op;       /* blocs lus ou enregistrements écrits par opération */
    uint64_t sync_every;   /* enregistrements entre deux demandes de persistance */
    uint64_t ops;
    uint64_t param;        /* taille du lot, pour les tracés */
};

struct sample {
    uint32_t round, position, measure;
    uint64_t elapsed_ns, deferred_ns, result, expected;
    uint64_t resident_before, resident_after;
    struct io_counts io;
    struct system_counts system, deferred;
    long voluntary, involuntary;
    int cpu_before, cpu_after;
    uint64_t first_op;
};

static struct io_counts io_delta(const struct io_counts *a, const struct io_counts *b) {
    return (struct io_counts){b->syscr - a->syscr, b->syscw - a->syscw, b->read_bytes - a->read_bytes,
                              b->write_bytes - a->write_bytes, b->cancelled_write_bytes - a->cancelled_write_bytes};
}

static struct system_counts system_delta(const struct system_counts *a, const struct system_counts *b) {
    return (struct system_counts){b->device_reads - a->device_reads, b->device_read_sectors - a->device_read_sectors,
                                  b->device_writes - a->device_writes, b->device_write_sectors - a->device_write_sectors,
                                  b->device_flushes - a->device_flushes, b->journal_commits - a->journal_commits};
}

static int request_persistence(int fd, enum sync sync) {
    if (sync == SYNC_FSYNC) return fsync(fd);
    if (sync == SYNC_FDATASYNC) return fdatasync(fd);
    return 0;   /* SYNC_NONE ; SYNC_ODSYNC : chaque pwrite attend déjà la persistance */
}

int main(int argc, char **argv) {
    const char *output_path = NULL, *ops_path = NULL, *meta_path = NULL, *core = "inconnu";
    const char *read_path = NULL, *scratch = NULL, *tmpfs = NULL, *create_path = NULL;
    uint64_t run_id = 0, seed = UINT64_C(20260921), rounds = 11, warmup_rounds = 1, ops = 256, file_mib = 256;
    int self_test = 0;
    device_stat_path = "/sys/block/nvme0n1/stat";
    journal_info_path = "/proc/fs/jbd2/dm-0-8/info";
    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--self-test") == 0) { self_test = 1; continue; }
        if (i + 1 >= argc) {
            fprintf(stderr, "missing value for %s\n", argv[i]);
            return EXIT_FAILURE;
        }
        const char *value = argv[++i];
        if (strcmp(argv[i - 1], "--output") == 0) output_path = value;
        else if (strcmp(argv[i - 1], "--ops-output") == 0) ops_path = value;
        else if (strcmp(argv[i - 1], "--meta") == 0) meta_path = value;
        else if (strcmp(argv[i - 1], "--core") == 0) core = value;
        else if (strcmp(argv[i - 1], "--read-file") == 0) read_path = value;
        else if (strcmp(argv[i - 1], "--create-read-file") == 0) create_path = value;
        else if (strcmp(argv[i - 1], "--scratch") == 0) scratch = value;
        else if (strcmp(argv[i - 1], "--tmpfs") == 0) tmpfs = value;
        else if (strcmp(argv[i - 1], "--device-stat") == 0) device_stat_path = value;
        else if (strcmp(argv[i - 1], "--journal-info") == 0) journal_info_path = value;
        else if (strcmp(argv[i - 1], "--run-id") == 0) run_id = parse_u64(value, argv[i - 1]);
        else if (strcmp(argv[i - 1], "--seed") == 0) seed = parse_u64(value, argv[i - 1]);
        else if (strcmp(argv[i - 1], "--rounds") == 0) rounds = parse_u64(value, argv[i - 1]);
        else if (strcmp(argv[i - 1], "--warmup-rounds") == 0) warmup_rounds = parse_u64(value, argv[i - 1]);
        else if (strcmp(argv[i - 1], "--ops") == 0) ops = parse_u64(value, argv[i - 1]);
        else if (strcmp(argv[i - 1], "--file-mib") == 0) file_mib = parse_u64(value, argv[i - 1]);
        else {
            fprintf(stderr, "unknown option %s\n", argv[i - 1]);
            return EXIT_FAILURE;
        }
    }
    uint64_t pages = file_mib * 256;
    if (create_path != NULL) {
        create_read_file(create_path, pages);
        return EXIT_SUCCESS;
    }
    if (read_path == NULL || scratch == NULL || tmpfs == NULL || file_mib == 0 || file_mib > 4096 ||
        ops < 256 || ops % 256 != 0 || ops > pages / 4 ||
        (!self_test && (output_path == NULL || ops_path == NULL || meta_path == NULL || run_id == 0 ||
                        rounds == 0 || warmup_rounds >= rounds))) {
        fprintf(stderr, "usage: %s --create-read-file FILE --file-mib N\n"
                        "       %s --read-file FILE --scratch DIR --tmpfs DIR --file-mib N --ops N "
                        "(--self-test | --output FILE --ops-output FILE --meta FILE --run-id N [--core LABEL] "
                        "[--seed N] [--rounds N] [--warmup-rounds N] [--device-stat FILE] [--journal-info FILE])\n",
                argv[0], argv[0]);
        return EXIT_FAILURE;
    }
    size_t file_bytes = (size_t)(pages * PAGE);

    /* Fichier lu : taille contrôlée, sommes attendues de chaque bloc, projection pour mincore. */
    struct stat info;
    int probe = open_or_die(read_path, O_RDONLY);
    if (fstat(probe, &info) != 0 || (uint64_t)info.st_size != file_bytes) {
        fprintf(stderr, "%s : taille inattendue\n", read_path);
        return EXIT_FAILURE;
    }
    void *mapping = mmap(NULL, file_bytes, PROT_READ, MAP_SHARED, probe, 0);
    if (mapping == MAP_FAILED) die("mmap");
    unsigned char *vector = malloc(pages);
    uint64_t *expected_sum = malloc(pages * sizeof(*expected_sum));
    uint32_t *permutation = malloc(pages * sizeof(*permutation));
    unsigned char *block = page_aligned(PAGE);
    if (vector == NULL || expected_sum == NULL || permutation == NULL) die("malloc");
    for (uint64_t b = 0; b < pages; ++b) {
        fill_block(block, 0, b);
        expected_sum[b] = block_sum(block);
    }
    uint64_t state = mix64(seed ^ (run_id * UINT64_C(0x9e3779b97f4a7c15)));
    if (state == 0) state = 1;
    for (uint64_t b = 0; b < pages; ++b) permutation[b] = (uint32_t)b;
    for (uint64_t b = pages; b > 1; --b) {   /* pages distinctes au sein d'un échantillon */
        uint64_t other = random_next(&state) % b;
        uint32_t temporary = permutation[b - 1];
        permutation[b - 1] = permutation[other];
        permutation[other] = temporary;
    }

    /* Fichiers écrits : un par mesure, pour qu'aucune n'hérite de l'état d'une autre. */
    char path[4096];
    struct file_state files[] = {
        {"append-buffered.dat", TARGET_EXT4, 1, 0, -1, -1, 0, 1},
        {"append-fsync-1.dat", TARGET_EXT4, 1, 0, -1, -1, 0, 1},
        {"append-fsync-4.dat", TARGET_EXT4, 1, 0, -1, -1, 0, 1},
        {"append-fsync-16.dat", TARGET_EXT4, 1, 0, -1, -1, 0, 1},
        {"append-fsync-64.dat", TARGET_EXT4, 1, 0, -1, -1, 0, 1},
        {"append-fsync-256.dat", TARGET_EXT4, 1, 0, -1, -1, 0, 1},
        {"append-fdatasync.dat", TARGET_EXT4, 1, 0, -1, -1, 0, 1},
        {"append-fsync.dat", TARGET_TMPFS, 1, 0, -1, -1, 0, 1},
        {"overwrite-fsync.dat", TARGET_EXT4, 0, 0, -1, -1, ops, 1},
        {"overwrite-fdatasync.dat", TARGET_EXT4, 0, 0, -1, -1, ops, 1},
        {"overwrite-fdatasync-bis.dat", TARGET_EXT4, 0, 0, -1, -1, ops, 1},
        {"overwrite-fdatasync-double.dat", TARGET_EXT4, 0, 0, -1, -1, 2 * ops, 1},
        {"overwrite-odsync.dat", TARGET_EXT4, 0, 1, -1, -1, ops, 1},
        {"overwrite-fdatasync-folio.dat", TARGET_EXT4, 0, 0, -1, -1, ops, ops},
        {"overwrite-odsync-folio.dat", TARGET_EXT4, 0, 1, -1, -1, ops, ops},
    };
    size_t file_count = sizeof(files) / sizeof(files[0]);
    unsigned char *records = page_aligned(2 * ops * PAGE);
    uint64_t *record_sum = malloc(2 * ops * sizeof(*record_sum));
    if (record_sum == NULL) die("malloc");
    for (size_t f = 0; f < file_count; ++f) {
        struct file_state *file = &files[f];
        snprintf(path, sizeof(path), "%s/%s", file->target == TARGET_TMPFS ? tmpfs : scratch, file->name);
        file->fd = open_or_die(path, O_RDWR | O_CREAT | O_TRUNC | (file->dsync ? O_DSYNC : 0));
        /* Relecture : sans le cache de pages sur ext4 ; tmpfs n'a pas d'autre copie que ce cache. */
        file->readback_fd = open_or_die(path, O_RDONLY | (file->target == TARGET_EXT4 ? O_DIRECT : 0));
        for (uint64_t r = 0; r < file->records; ++r) fill_block(records + r * PAGE, WRITE_KEY, r);
        /* Écritures de 4 Kio : petits folios dans le cache ; une écriture de 1 Mio : un grand folio. */
        for (uint64_t r = 0; r < file->records; r += file->init_chunk) {
            size_t bytes = (size_t)(file->init_chunk * PAGE);
            if (pwrite(file->fd, records + r * PAGE, bytes, (off_t)(r * PAGE)) != (ssize_t)bytes) die("initialisation");
        }
        if (file->records != 0 && fsync(file->fd) != 0) die("initialisation");
    }

    /* Plan des mesures. */
    struct measure measures[32];
    size_t count = 0;
    uint64_t seq_ops = file_bytes / SEQ_CHUNK;
    measures[count++] = (struct measure){"seq_read_warm", KIND_SEQ, CACHE_WARM, SYNC_NONE, NULL, SEQ_CHUNK / PAGE, 0, seq_ops, 0};
    measures[count++] = (struct measure){"seq_read_cold", KIND_SEQ, CACHE_COLD, SYNC_NONE, NULL, SEQ_CHUNK / PAGE, 0, seq_ops, 0};
    measures[count++] = (struct measure){"seq_read_direct", KIND_SEQ, CACHE_DIRECT, SYNC_NONE, NULL, SEQ_CHUNK / PAGE, 0, seq_ops, 0};
    measures[count++] = (struct measure){"rand_read_warm", KIND_RAND, CACHE_WARM, SYNC_NONE, NULL, 1, 0, ops, 0};
    measures[count++] = (struct measure){"rand_read_cold", KIND_RAND, CACHE_COLD, SYNC_NONE, NULL, 1, 0, ops, 0};
    measures[count++] = (struct measure){"rand_read_cold_bis", KIND_RAND, CACHE_COLD, SYNC_NONE, NULL, 1, 0, ops, 0};
    measures[count++] = (struct measure){"rand_read_direct", KIND_RAND, CACHE_DIRECT, SYNC_NONE, NULL, 1, 0, ops, 0};
    measures[count++] = (struct measure){"rand_read_direct_double", KIND_RAND, CACHE_DIRECT, SYNC_NONE, NULL, 2, 0, ops, 0};
    measures[count++] = (struct measure){"append_buffered", KIND_WRITE, CACHE_NONE, SYNC_NONE, &files[0], 1, 0, ops, 0};
    for (uint64_t b = 0, batch = 1; b < BATCHES; ++b, batch *= 4)
        measures[count++] = (struct measure){"append_fsync", KIND_WRITE, CACHE_NONE, SYNC_FSYNC, &files[1 + b], batch, batch, ops / batch, batch};
    measures[count++] = (struct measure){"append_fdatasync", KIND_WRITE, CACHE_NONE, SYNC_FDATASYNC, &files[6], 1, 1, ops, 1};
    measures[count++] = (struct measure){"tmpfs_append_fsync", KIND_WRITE, CACHE_NONE, SYNC_FSYNC, &files[7], 1, 1, ops, 1};
    measures[count++] = (struct measure){"overwrite_fsync", KIND_WRITE, CACHE_NONE, SYNC_FSYNC, &files[8], 1, 1, ops, 1};
    measures[count++] = (struct measure){"overwrite_fdatasync", KIND_WRITE, CACHE_NONE, SYNC_FDATASYNC, &files[9], 1, 1, ops, 1};
    measures[count++] = (struct measure){"overwrite_fdatasync_bis", KIND_WRITE, CACHE_NONE, SYNC_FDATASYNC, &files[10], 1, 1, ops, 1};
    measures[count++] = (struct measure){"overwrite_fdatasync_double", KIND_WRITE, CACHE_NONE, SYNC_FDATASYNC, &files[11], 2, 1, ops, 1};
    measures[count++] = (struct measure){"overwrite_odsync", KIND_WRITE, CACHE_NONE, SYNC_ODSYNC, &files[12], 1, 1, ops, 1};
    measures[count++] = (struct measure){"overwrite_fdatasync_folio", KIND_WRITE, CACHE_NONE, SYNC_FDATASYNC, &files[13], 1, 1, ops, 1};
    measures[count++] = (struct measure){"overwrite_odsync_folio", KIND_WRITE, CACHE_NONE, SYNC_ODSYNC, &files[14], 1, 1, ops, 1};

    if (self_test) rounds = 1, warmup_rounds = 0;
    size_t sample_count = count * (size_t)rounds;
    uint64_t ops_per_round = 0;
    for (size_t j = 0; j < count; ++j) ops_per_round += measures[j].ops;
    struct sample *samples = calloc(sample_count, sizeof(*samples));
    uint32_t *latency = malloc(ops_per_round * rounds * sizeof(*latency));   /* ns ; < 4,29 s par opération */
    unsigned char *buffer = page_aligned(SEQ_CHUNK);
    if (samples == NULL || latency == NULL) die("allocation");
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
    uint64_t op_cursor = 0, residency_retries = 0, over_limit = 0;
    for (size_t i = 0; i < sample_count; ++i) {
        struct sample *s = &samples[i];
        const struct measure *m = &measures[s->measure];
        s->first_op = op_cursor;
        uint32_t *lat = latency + op_cursor;
        op_cursor += m->ops;
        int fd = -1;

        /* ---- préparation, hors chronométrage */
        if (m->kind != KIND_WRITE) {
            if (m->cache == CACHE_COLD) {
                /* Retire du cache les seules pages de notre fichier, propres depuis sa création. */
                for (int attempt = 0; attempt < 5; ++attempt) {
                    posix_fadvise(probe, 0, 0, POSIX_FADV_DONTNEED);
                    if (resident_pages(mapping, file_bytes, vector) == 0) break;
                    ++residency_retries;
                }
            } else if (m->cache == CACHE_WARM && resident_pages(mapping, file_bytes, vector) != pages) {
                int warm = open_or_die(read_path, O_RDONLY);
                while (read(warm, buffer, SEQ_CHUNK) > 0) {}
                close(warm);
            }
            fd = open_or_die(read_path, O_RDONLY | (m->cache == CACHE_DIRECT ? O_DIRECT : 0));
            if (m->kind == KIND_RAND && m->cache != CACHE_DIRECT) posix_fadvise(fd, 0, 0, POSIX_FADV_RANDOM);
            s->resident_before = resident_pages(mapping, file_bytes, vector);
            s->expected = m->ops * m->per_op;
        } else {
            struct file_state *file = m->file;
            fd = file->fd;
            if (file->append && (ftruncate(fd, 0) != 0 || fsync(fd) != 0)) die("ftruncate");
            uint64_t key = mix64(WRITE_KEY ^ (run_id << 40) ^ ((uint64_t)i << 8));
            uint64_t total = m->ops * m->per_op;
            for (uint64_t r = 0; r < total; ++r) {
                fill_block(records + r * PAGE, key, r);
                record_sum[r] = block_sum(records + r * PAGE);
            }
            s->expected = total;
        }
        uint64_t start = random_next(&state) % pages;

        struct system_counts system_before, system_after;
        struct io_counts io_before, io_after;
        struct rusage usage_before, usage_after;
        system_counters(&system_before);
        getrusage(RUSAGE_THREAD, &usage_before);
        io_counters(&io_before);
        s->cpu_before = sched_getcpu();

        /* ---- opérations chronométrées une à une ; les vérifications restent hors des fenêtres */
        uint64_t correct = 0;
        if (m->kind == KIND_SEQ) {
            for (uint64_t op = 0; op < m->ops; ++op) {
                uint64_t before = monotonic_ns();
                ssize_t done = read(fd, buffer, SEQ_CHUNK);
                uint64_t after = monotonic_ns();
                lat[op] = (uint32_t)(after - before);
                over_limit += after - before > UINT32_MAX;
                if (done != SEQ_CHUNK) continue;
                for (uint64_t b = 0; b < m->per_op; ++b)
                    correct += block_sum(buffer + b * PAGE) == expected_sum[op * m->per_op + b];
            }
        } else if (m->kind == KIND_RAND) {
            for (uint64_t op = 0; op < m->ops; ++op) {
                uint64_t page[2] = {permutation[(start + 2 * op) % pages], permutation[(start + 2 * op + 1) % pages]};
                ssize_t done[2] = {0, 0};
                uint64_t before = monotonic_ns();
                for (uint64_t k = 0; k < m->per_op; ++k)
                    done[k] = pread(fd, buffer + k * PAGE, PAGE, (off_t)(page[k] * PAGE));
                uint64_t after = monotonic_ns();
                lat[op] = (uint32_t)(after - before);
                over_limit += after - before > UINT32_MAX;
                for (uint64_t k = 0; k < m->per_op; ++k)
                    correct += done[k] == PAGE && block_sum(buffer + k * PAGE) == expected_sum[page[k]];
            }
        } else {
            uint64_t written = 0;
            for (uint64_t op = 0; op < m->ops; ++op) {
                uint64_t first = op * m->per_op;
                uint64_t before = monotonic_ns();
                for (uint64_t r = first; r < first + m->per_op; ++r) {
                    written += pwrite(fd, records + r * PAGE, PAGE, (off_t)(r * PAGE)) == PAGE;
                    if (m->sync_every != 0 && (r + 1) % m->sync_every == 0 && request_persistence(fd, m->sync) != 0)
                        written = 0;
                }
                uint64_t after = monotonic_ns();
                lat[op] = (uint32_t)(after - before);
                over_limit += after - before > UINT32_MAX;
            }
            correct = written;
        }

        s->cpu_after = sched_getcpu();
        io_counters(&io_after);
        getrusage(RUSAGE_THREAD, &usage_after);
        system_counters(&system_after);
        s->io = io_delta(&io_before, &io_after);
        s->system = system_delta(&system_before, &system_after);
        s->voluntary = usage_after.ru_nvcsw - usage_before.ru_nvcsw;
        s->involuntary = usage_after.ru_nivcsw - usage_before.ru_nivcsw;
        for (uint64_t op = 0; op < m->ops; ++op) s->elapsed_ns += lat[op];

        /* ---- après : persistance différée des écritures en tampon, puis relecture */
        if (m->kind != KIND_WRITE) {
            s->resident_after = resident_pages(mapping, file_bytes, vector);
            s->result = correct;
            close(fd);
            continue;
        }
        struct file_state *file = m->file;
        if (m->sync == SYNC_NONE) {
            struct system_counts deferred_before, deferred_after;
            system_counters(&deferred_before);
            uint64_t before = monotonic_ns();
            if (fsync(fd) != 0) correct = 0;
            s->deferred_ns = monotonic_ns() - before;
            system_counters(&deferred_after);
            s->deferred = system_delta(&deferred_before, &deferred_after);
        }
        uint64_t total = m->ops * m->per_op;
        struct stat written_info;
        uint64_t verified = 0;
        if (fstat(fd, &written_info) == 0 &&
            (uint64_t)written_info.st_size == (file->append ? total : file->records) * PAGE) {
            for (uint64_t r = 0; r < total; ++r)
                verified += pread(file->readback_fd, block, PAGE, (off_t)(r * PAGE)) == PAGE &&
                            block_sum(block) == record_sum[r];
        }
        s->result = correct == total ? verified : 0;
    }

    if (self_test) {
        int ok = 1;
        for (size_t i = 0; i < sample_count; ++i) {
            const struct sample *s = &samples[i];
            const struct measure *m = &measures[s->measure];
            int residency = m->cache == CACHE_COLD ? s->resident_before == 0
                          : m->cache == CACHE_WARM ? s->resident_before == pages : 1;
            if (s->result != s->expected || !residency) {
                fprintf(stderr, "self-test: %s résultat %" PRIu64 "/%" PRIu64 " pages en cache %" PRIu64 "\n",
                        m->label, s->result, s->expected, s->resident_before);
                ok = 0;
            }
        }
        puts(ok ? "self-test: OK" : "self-test: FAILED");
        return ok ? EXIT_SUCCESS : EXIT_FAILURE;
    }

    FILE *file = fopen(output_path, "w");
    FILE *ops_file = fopen(ops_path, "w");
    if (file == NULL || ops_file == NULL) die("sorties");
    fprintf(file, "run_id,core,seed,sample,round,phase,position,label,param,ops,units_per_op,elapsed_ns,deferred_ns,"
                  "result,expected,resident_before,resident_after,file_pages,read_syscalls,write_syscalls,read_bytes,"
                  "write_bytes,cancelled_write_bytes,device_reads,device_read_sectors,device_writes,device_write_sectors,"
                  "device_flushes,journal_commits,deferred_device_writes,deferred_device_write_sectors,"
                  "deferred_device_flushes,deferred_journal_commits,voluntary_switches,"
                  "involuntary_switches,cpu_before,cpu_after\n");
    fprintf(ops_file, "sample,op,latency_ns\n");
    int invalid = 0;
    for (size_t i = 0; i < sample_count; ++i) {
        const struct sample *s = &samples[i];
        const struct measure *m = &measures[s->measure];
        invalid += s->result != s->expected;
        fprintf(file,
                "%" PRIu64 ",%s,%" PRIu64 ",%zu,%" PRIu32 ",%s,%" PRIu32 ",%s,%" PRIu64 ",%" PRIu64 ",%" PRIu64
                ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64
                ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64
                ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%ld,%ld,%d,%d\n",
                run_id, core, seed, i, s->round, s->round < warmup_rounds ? "warmup" : "measure", s->position,
                m->label, m->param, m->ops, m->per_op, s->elapsed_ns, s->deferred_ns, s->result, s->expected,
                s->resident_before, s->resident_after, pages, s->io.syscr, s->io.syscw, s->io.read_bytes,
                s->io.write_bytes, s->io.cancelled_write_bytes, s->system.device_reads, s->system.device_read_sectors,
                s->system.device_writes, s->system.device_write_sectors, s->system.device_flushes,
                s->system.journal_commits, s->deferred.device_writes, s->deferred.device_write_sectors,
                s->deferred.device_flushes, s->deferred.journal_commits, s->voluntary, s->involuntary,
                s->cpu_before, s->cpu_after);
        if (m->kind == KIND_SEQ) continue;   /* lectures séquentielles : seule la somme est gardée */
        for (uint64_t op = 0; op < m->ops; ++op)
            fprintf(ops_file, "%zu,%" PRIu64 ",%" PRIu32 "\n", i, op, latency[s->first_op + op]);
    }
    int status = fclose(file) == 0 && fclose(ops_file) == 0 ? EXIT_SUCCESS : EXIT_FAILURE;

    struct rusage usage;
    getrusage(RUSAGE_SELF, &usage);
    FILE *meta = fopen(meta_path, "w");
    if (meta == NULL) die(meta_path);
    fprintf(meta, "run_id,core,first_cpu,file_pages,ops,device_stat,journal_info,residency_retries,"
                  "latency_over_limit,voluntary_switches,involuntary_switches,invalid_samples\n");
    fprintf(meta, "%" PRIu64 ",%s,%d,%" PRIu64 ",%" PRIu64 ",%s,%s,%" PRIu64 ",%" PRIu64 ",%ld,%ld,%d\n", run_id,
            core, first_cpu, pages, ops, device_stat_path, journal_info_path, residency_retries, over_limit,
            usage.ru_nvcsw, usage.ru_nivcsw, invalid);
    if (fclose(meta) != 0) status = EXIT_FAILURE;
    for (size_t f = 0; f < file_count; ++f) {
        close(files[f].fd);
        close(files[f].readback_fd);
    }
    if (invalid != 0 || over_limit != 0) {
        fprintf(stderr, "%d échantillons invalides, %" PRIu64 " durées hors limite : mesures non valides\n",
                invalid, over_limit);
        return EXIT_FAILURE;
    }
    return status;
}
