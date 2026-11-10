#ifndef AXIOM_QVU_H
#define AXIOM_QVU_H

#include <stdint.h>

/* x86-64 System V C ABI. No packed host structs are required.
 * Inputs are byte buffers in canonical little-endian QVU1/QSEED01 format.
 * Neither function allocates memory, consumes entropy, or performs syscalls.
 * The caller must supply a readable buffer of at least byte_len bytes.
 * Returns 0 on acceptance and -1 on refusal. See docs for exact fields.
 */
#ifdef __cplusplus
extern "C" {
#endif
int qvu_abi_packet_validate(const uint8_t *buffer, uint64_t byte_len);
int qvu_abi_seed_validate(const uint8_t *buffer, uint64_t byte_len);
#ifdef __cplusplus
}
#endif

#define AXIOM_QVU_HEADER_BYTES 48u
#define AXIOM_QVU_RECORD_BYTES 16u
#define AXIOM_QVU_SEED_BYTES 64u
#define AXIOM_QVU_MAX_RECORDS 4096u
#define AXIOM_QVU_FORMAT_MAX_SITES 256u
#define AXIOM_QVU_DENSE_MAX_SITES 20u
#define AXIOM_QVU_CLIFFORD_SITES 32u

#endif
