#ifndef KERNELS_H
#define KERNELS_H

#include <stddef.h>
#include <stdint.h>

/* Signature commune : tableau, taille, seuil (ignoré par les noyaux sans
 * condition) et tampon de sortie (utilisé par les seuls filtres). */
typedef uint64_t (*kernel_fn)(const uint64_t *data, size_t n, uint64_t threshold,
                              uint64_t *output);

/* Multiplicateur impair utilisé par les noyaux de dépendance. */
#define KERNEL_MULTIPLIER UINT64_C(0x9e3779b97f4a7c15)

uint64_t chain_xor_mul(const uint64_t *data, size_t n, uint64_t threshold, uint64_t *output);
uint64_t split_xor_mul(const uint64_t *data, size_t n, uint64_t threshold, uint64_t *output);
uint64_t sum_one(const uint64_t *data, size_t n, uint64_t threshold, uint64_t *output);
uint64_t sum_four(const uint64_t *data, size_t n, uint64_t threshold, uint64_t *output);
uint64_t sum_twice(const uint64_t *data, size_t n, uint64_t threshold, uint64_t *output);
uint64_t sum_if(const uint64_t *data, size_t n, uint64_t threshold, uint64_t *output);
uint64_t filter_copy(const uint64_t *data, size_t n, uint64_t threshold, uint64_t *output);
uint64_t filter_copy_mask(const uint64_t *data, size_t n, uint64_t threshold, uint64_t *output);

extern const char kernel_build[];
extern const char kernel_compiler[];

#endif
