/* Noyaux mesurés. Ce fichier est compilé avec plusieurs jeux d'options ; le
 * harnais, compilé une seule fois, ne voit pas ce code (pas de LTO). */

#include "kernels.h"

#ifndef KERNEL_BUILD
#define KERNEL_BUILD "inconnu"
#endif

const char kernel_build[] = KERNEL_BUILD;
const char kernel_compiler[] = __VERSION__;

/* Dépendance longue : le xor et la multiplication sont tous deux sur le chemin
 * qui relie une itération à la suivante (h dépend de h). */
uint64_t chain_xor_mul(const uint64_t *data, size_t n, uint64_t threshold, uint64_t *output) {
    (void)threshold;
    (void)output;
    uint64_t h = 0;
    for (size_t i = 0; i < n; ++i) {
        h = (h ^ data[i]) * KERNEL_MULTIPLIER;
    }
    return h;
}

/* Mêmes opérations par élément (lecture, multiplication, xor), mais la
 * multiplication ne dépend que de l'élément : seul le xor relie les itérations. */
uint64_t split_xor_mul(const uint64_t *data, size_t n, uint64_t threshold, uint64_t *output) {
    (void)threshold;
    (void)output;
    uint64_t h = 0;
    for (size_t i = 0; i < n; ++i) {
        h ^= data[i] * KERNEL_MULTIPLIER;
    }
    return h;
}

/* Somme à un seul accumulateur : une chaîne d'additions. */
uint64_t sum_one(const uint64_t *data, size_t n, uint64_t threshold, uint64_t *output) {
    (void)threshold;
    (void)output;
    uint64_t sum = 0;
    for (size_t i = 0; i < n; ++i) {
        sum += data[i];
    }
    return sum;
}

/* Même somme, répartie sur quatre accumulateurs indépendants : quatre chaînes
 * d'additions qui peuvent progresser en même temps. */
uint64_t sum_four(const uint64_t *data, size_t n, uint64_t threshold, uint64_t *output) {
    (void)threshold;
    (void)output;
    uint64_t s0 = 0, s1 = 0, s2 = 0, s3 = 0;
    size_t i = 0;
    for (; i + 4 <= n; i += 4) {
        s0 += data[i];
        s1 += data[i + 1];
        s2 += data[i + 2];
        s3 += data[i + 3];
    }
    for (; i < n; ++i) {
        s0 += data[i];
    }
    return s0 + s1 + s2 + s3;
}

/* Contrôle positif : deux parcours complets. */
uint64_t sum_twice(const uint64_t *data, size_t n, uint64_t threshold, uint64_t *output) {
    (void)threshold;
    (void)output;
    uint64_t sum = 0;
    for (size_t i = 0; i < n; ++i) {
        sum += data[i];
    }
    for (size_t i = 0; i < n; ++i) {
        sum += data[i];
    }
    return sum;
}

/* Somme conditionnelle écrite avec un if : le compilateur choisit entre un
 * branchement, un transfert conditionnel (cmov) ou une version vectorisée. */
uint64_t sum_if(const uint64_t *data, size_t n, uint64_t threshold, uint64_t *output) {
    (void)output;
    uint64_t sum = 0;
    for (size_t i = 0; i < n; ++i) {
        if (data[i] >= threshold) {
            sum += data[i];
        }
    }
    return sum;
}

/* Filtre : copie les éléments retenus et renvoie leur nombre. Rendre ce if sans
 * branchement obligerait à écrire à chaque itération, ce que le compilateur ne
 * s'autorise pas de lui-même. */
uint64_t filter_copy(const uint64_t *data, size_t n, uint64_t threshold, uint64_t *output) {
    size_t kept = 0;
    for (size_t i = 0; i < n; ++i) {
        if (data[i] >= threshold) {
            output[kept++] = data[i];
        }
    }
    return kept;
}

/* Même filtre écrit sans branchement : écriture systématique, avance conditionnelle.
 * Le tampon doit contenir n éléments. */
uint64_t filter_copy_mask(const uint64_t *data, size_t n, uint64_t threshold, uint64_t *output) {
    size_t kept = 0;
    for (size_t i = 0; i < n; ++i) {
        output[kept] = data[i];
        kept += data[i] >= threshold;
    }
    return kept;
}
