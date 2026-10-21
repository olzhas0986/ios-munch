/* Diagnostics: 0001 splash; 0002 CPU0 MMU/IRQ; 0003 PSCI secondary entry/off.
 * No version includes XNU, storage or clock programming.
 * DT guard confines splash stores to the expected board's reservation.
 */
#include <stdint.h>
#include "console.h"
#include "guard.h"
#ifdef MUNCH_SMP
#include "smp.h"
#endif
#ifdef MUNCH_MMU_IRQ
#include "probe.h"
#endif

#define reg(name) ({ uint64_t v; __asm__ volatile("mrs %0, " name : "=r"(v)); v; })

static void __attribute__((noreturn)) stop(void)
{
    for (;;) __asm__ volatile("wfe");
}

#ifndef MUNCH_SMP
void secondary_main(uint64_t cpu) { (void)cpu; stop(); }
#endif
void exc_handler(uint64_t slot, uint64_t *regs)
{
#ifdef MUNCH_MMU_IRQ
    if (slot == 5 && munch_irq_ready()) {
        munch_irq_handler();
        return;
    }
    con_clear(BLUE);
    con_str("MUNCH", "DIAG 0002 EXCEPTION");
    con_str("STAGE", munch_stage());
    con_hex("SLOT", slot);
    con_hex("ESR", reg("esr_el1"));
    con_hex("ELR", reg("elr_el1"));
    con_hex("FAR", reg("far_el1"));
    con_hex("SPSR", reg("spsr_el1"));
    con_hex("X0", regs[0]);
#else
#ifdef MUNCH_SMP
#ifdef MUNCH_SMP_HOLD
    munch_smp_secondary_exception(slot);
#endif
    con_clear(BLUE);
#ifdef MUNCH_SMP_HOLD
    con_str("MUNCH", "DIAG 0004 EXCEPTION");
#else
    con_str("MUNCH", "DIAG 0003 EXCEPTION");
#endif
    con_hex("CPU", reg("mpidr_el1"));
    con_hex("SLOT", slot);
    con_hex("ESR", reg("esr_el1"));
    con_hex("ELR", reg("elr_el1"));
    con_hex("FAR", reg("far_el1"));
    (void)regs;
#else
    (void)slot; (void)regs;
#endif
#endif
    stop();
}

void shim_main(uintptr_t dtb)
{
    if (!munch_splash_allowed((void *)dtb, 4U * 1024U * 1024U)) stop();
    con_clear(0xff102030);
#if defined(MUNCH_SMP_HOLD)
    con_str("MUNCH", "DIAG 0004");
#elif defined(MUNCH_SMP)
    con_str("MUNCH", "DIAG 0003");
#elif defined(MUNCH_MMU_IRQ)
    con_str("MUNCH", "DIAG 0002");
#else
    con_str("MUNCH", "DIAG 0001");
#endif
    con_str("TEST", "ABL SPLASH WRITE");
    con_hex("DTB", dtb);
    con_hex("EL", reg("CurrentEL") >> 2);
    con_hex("MIDR", reg("midr_el1"));
    con_hex("MPIDR", reg("mpidr_el1"));
    con_hex("MMFR0", reg("id_aa64mmfr0_el1"));
    con_hex("CNTFRQ", reg("cntfrq_el0"));
    con_hex("SCTLR", reg("sctlr_el1"));
    con_skip();
#if defined(MUNCH_SMP)
    int ok = munch_smp_probe();
    con_str("STATUS", ok ? "SMP START STOP PASS" : "SMP TEST INCOMPLETE");
#elif defined(MUNCH_MMU_IRQ)
    int ok = munch_probe();
    con_str("STATUS", ok ? "MMU IRQ TESTS PASS" : "TESTS INCOMPLETE");
#else
    con_str("STATUS", "CPU0 C ENTRY OK");
#endif
    con_str("END", "HOLD POWER TO REBOOT");
    __asm__ volatile("dsb sy" ::: "memory");
    stop();
}
