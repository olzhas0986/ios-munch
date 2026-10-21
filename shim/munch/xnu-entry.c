/* CPU0-only XNU handoff. No diagnostic UFS, PSCI, GIC or MMU programming. */
#include <stdint.h>
#include "console.h"
#include "guard.h"
#include "loader.h"

#define reg(name) ({ uint64_t v; __asm__ volatile("mrs %0, " name : "=r"(v)); v; })

static void __attribute__((noreturn)) stop(void)
{
    for (;;) __asm__ volatile("wfe");
}

void secondary_main(uint64_t cpu) { (void)cpu; stop(); }

void exc_handler(uint64_t slot, uint64_t *regs)
{
    (void)regs;
    con_clear(BLUE);
    con_str("MUNCH", "XNU 0016 SHIM EXCEPTION");
    con_hex("SLOT", slot);
    con_hex("ESR", reg("esr_el1"));
    con_hex("ELR", reg("elr_el1"));
    con_hex("FAR", reg("far_el1"));
    stop();
}

void shim_main(uintptr_t dtb)
{
    if (!munch_splash_allowed((void *)dtb, 4U * 1024U * 1024U)) stop();
    con_clear(0xff102030);
    con_str("MUNCH", "XNU 0016 CPU0 HANDOFF");
    con_hex("DTB", dtb);
    con_hex("SHIM", (uintptr_t)shim_main);
    if ((reg("CurrentEL") >> 2) != 1 || (reg("sctlr_el1") & 5)) {
        con_str("ERROR", "EL/MMU PRECHECK FAILED"); stop();
    }
    con_str("ERROR", loader_boot(dtb));
    stop();
}
