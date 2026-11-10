#ifndef AXIOM_MACHINE_H
#define AXIOM_MACHINE_H
#include <stdint.h>
/* Serialized fields are little-endian u64; use explicit readers, not host
 * struct layout. The native CLI reads a seed from stdin and writes history.
 * This interface describes virtual stabilizer qubits, not physical devices. */
#define AXIOM_MACHINE_VERSION 1u
#define AXIOM_MACHINE_QUBITS 32u
#define AXIOM_MACHINE_HEADER_BYTES 64u
#define AXIOM_MACHINE_STATE_BYTES 4096u
#define AXIOM_MACHINE_RECORD_BYTES 32u
#define AXIOM_MACHINE_TABLEAU_OFFSET 1024u
#define AXIOM_MACHINE_TABLEAU_ROWS 64u
#define AXIOM_MACHINE_ROW_BYTES 24u
#define AXIOM_MACHINE_MAX_RECORDS 1024u
#define AXIOM_MACHINE_MAX_GAS 1024u
#define AXIOM_MACHINE_MAX_GUEST_DEPTH 16u
enum axiom_machine_opcode {
 AXIOM_QHALT=0, AXIOM_QH=1, AXIOM_QS=2, AXIOM_QSDG=3,
 AXIOM_QCX=4, AXIOM_QX=5, AXIOM_QY=6, AXIOM_QZ=7,
 AXIOM_QENTROPY=8, AXIOM_QEPHASE=9,
 AXIOM_VMCALL=16, AXIOM_VMRETURN=17
};
#endif
