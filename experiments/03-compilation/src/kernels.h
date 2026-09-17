#ifndef KERNELS_H
#define KERNELS_H

#include <stddef.h>
#include <stdint.h>

/* Signature commune : chaque noyau reçoit le tableau et sa taille. */
typedef uint64_t (*kernel_fn)(const uint64_t *data, size_t n);

uint64_t sum_array(const uint64_t *data, size_t n);
uint64_t sum_array_twice(const uint64_t *data, size_t n);
uint64_t sum_discarded(const uint64_t *data, size_t n);
uint64_t sum_indices(const uint64_t *data, size_t n);

/* Renseignés à la compilation de kernels.c : le binaire décrit lui-même
 * le niveau d'optimisation et le compilateur de ses noyaux. */
extern const char kernel_opt_level[];
extern const char kernel_compiler[];

#endif
