/* Noyaux mesurés. Ce fichier est compilé à -O0, -O1, -O2 ou -O3 ; le harnais,
 * compilé séparément à -O2 et sans optimisation à l'édition de liens, ne voit
 * pas leur code et ne peut donc pas les transformer lui-même. */

#include "kernels.h"

#ifndef KERNEL_OPT
#define KERNEL_OPT "inconnu"
#endif

const char kernel_opt_level[] = KERNEL_OPT;
const char kernel_compiler[] = __VERSION__;

/* Somme des éléments : le résultat est renvoyé puis vérifié par l'appelant. */
uint64_t sum_array(const uint64_t *data, size_t n) {
    uint64_t sum = 0;
    for (size_t i = 0; i < n; ++i) {
        sum += data[i];
    }
    return sum;
}

/* Contrôle positif : deux parcours complets, donc deux fois plus de lectures
 * et d'additions que sum_array. */
uint64_t sum_array_twice(const uint64_t *data, size_t n) {
    uint64_t sum = 0;
    for (size_t i = 0; i < n; ++i) {
        sum += data[i];
    }
    for (size_t i = 0; i < n; ++i) {
        sum += data[i];
    }
    return sum;
}

/* Erreur classique de microbenchmark : la somme est calculée puis ignorée.
 * Rien d'observable ne dépend de la boucle. */
uint64_t sum_discarded(const uint64_t *data, size_t n) {
    uint64_t sum = 0;
    for (size_t i = 0; i < n; ++i) {
        sum += data[i];
    }
    (void)sum;
    return 0;
}

/* Somme 0 + 1 + ... + (n - 1) : le résultat est utilisé, mais il existe une
 * formule fermée que le compilateur a le droit d'employer à la place de la boucle. */
uint64_t sum_indices(const uint64_t *data, size_t n) {
    (void)data;
    uint64_t sum = 0;
    for (size_t i = 0; i < n; ++i) {
        sum += i;
    }
    return sum;
}
