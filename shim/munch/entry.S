/* PSCI entry marker before stack/C. Index by hardware Aff1, not context. */
#include "entry-layout.h"
    .text
    .balign 64
    .globl munch_secondary_entry
munch_secondary_entry:
    msr daifset, #0xf
    mrs x9, mpidr_el1
    ubfx x10, x9, #8, #8
    cbz x10, 9f
    cmp x10, #7
    b.hi 9f
    adr x11, munch_entry_records
    add x11, x11, x10, lsl #ENTRY_SHIFT
    str x9, [x11, #ENTRY_MPIDR]
    str x0, [x11, #ENTRY_CONTEXT]
    mrs x12, CurrentEL
    lsr x12, x12, #2
    str x12, [x11, #ENTRY_EL]
    mrs x12, sctlr_el1
    str x12, [x11, #ENTRY_SCTLR]
    mov x12, #1
    str x12, [x11, #ENTRY_STAGE]
    dsb sy
    msr spsel, #1
    adr x12, _sec_stacks
    add x12, x12, x10, lsl #12
    add x12, x12, #0x1000
    mov sp, x12
    adr x12, vectors
    msr vbar_el1, x12
    isb
    mov x12, #2
    str x12, [x11, #ENTRY_STAGE]
    dsb sy
    mov x0, x10
    bl secondary_main
9:  wfe
    b 9b
