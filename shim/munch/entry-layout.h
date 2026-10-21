#pragma once
#define ENTRY_SHIFT 6
#define ENTRY_MPIDR 0
#define ENTRY_CONTEXT 8
#define ENTRY_EL 16
#define ENTRY_SCTLR 24
#define ENTRY_STAGE 32
#define ENTRY_ESR 40
#define ENTRY_ELR 48
#define ENTRY_FAR 56
#ifndef __ASSEMBLER__
#include <stddef.h>
#include <stdint.h>
struct entry_record {
    uint64_t mpidr, context, el, sctlr, stage, esr, elr, far;
};
_Static_assert(sizeof(struct entry_record) == (1U << ENTRY_SHIFT), "entry stride");
_Static_assert(offsetof(struct entry_record, stage) == ENTRY_STAGE, "entry stage");
_Static_assert(offsetof(struct entry_record, far) == ENTRY_FAR, "entry far");
extern volatile struct entry_record munch_entry_records[8];
#endif
