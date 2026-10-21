/* Sequential PSCI CPU_ON/OFF test with all participants' MMU/D-cache off.
 * This avoids sharing WB data with a secondary entering with caches disabled.
 * No GIC, clock, voltage or storage programming.
 */
#include <stdint.h>
#include "console.h"
#include "smp.h"

#define reg(name) ({ uint64_t v; __asm__ volatile("mrs %0, " name : "=r"(v)); v; })
#define barrier() __asm__ volatile("dsb sy; isb" ::: "memory")
#define PSCI_VERSION 0x84000000UL
#define PSCI_CPU_OFF 0x84000002UL
#define PSCI_CPU_ON 0xc4000003UL
#define PSCI_AFFINITY_INFO 0xc4000004UL
#define AFFINITY_OFF 1
#define AFFINITY_MASK 0xff00ffffffULL
#define CPUS 8

struct observation {
    uint64_t mpidr, midr, mmfr0, el, sctlr;
    int64_t off_return;
    uint32_t ready;
};

static volatile struct observation observations[CPUS];
extern char secondary_entry[];

static int64_t smc(uint64_t fn, uint64_t a, uint64_t b, uint64_t c)
{
    register uint64_t x0 __asm__("x0") = fn;
    register uint64_t x1 __asm__("x1") = a;
    register uint64_t x2 __asm__("x2") = b;
    register uint64_t x3 __asm__("x3") = c;
    __asm__ volatile("smc #0" : "+r"(x0), "+r"(x1), "+r"(x2), "+r"(x3)
        : : "x4", "x5", "x6", "x7", "x8", "x9", "x10", "x11", "x12",
            "x13", "x14", "x15", "x16", "x17", "memory", "cc");
    return (int64_t)x0;
}

static uint64_t now(void) { __asm__ volatile("isb"); return reg("cntpct_el0"); }
static void __attribute__((noreturn)) park(void)
{
    for (;;) __asm__ volatile("wfe");
}

void secondary_main(uint64_t cpu)
{
    if (cpu == 0 || cpu >= CPUS) park();
    volatile struct observation *o = &observations[cpu];
    o->mpidr = reg("mpidr_el1");
    o->midr = reg("midr_el1");
    o->mmfr0 = reg("id_aa64mmfr0_el1");
    o->el = reg("CurrentEL") >> 2;
    o->sctlr = reg("sctlr_el1");
    barrier();
    o->ready = 1;
    barrier();
    /* Success never returns. Primary verifies OFF via AFFINITY_INFO. */
    o->off_return = smc(PSCI_CPU_OFF, 0, 0, 0);
    barrier();
    o->ready = 2;
    barrier();
    park();
}

int munch_smp_probe(void)
{
    if ((reg("sctlr_el1") & 5) || (reg("mpidr_el1") & AFFINITY_MASK)) {
        con_str("SMP", "PRECHECK FAILED"); return 0;
    }
    int64_t version = smc(PSCI_VERSION, 0, 0, 0);
    con_hex("PSCI", version);
    if ((uint32_t)version == 0xffffffffU || (uint32_t)version < 2) return 0;
    con_str("SMP", "CPU1..7 ENTRY THEN OFF");
    uint64_t freq = reg("cntfrq_el0");
    for (unsigned cpu = 1; cpu < CPUS; cpu++) {
        uint64_t target = (uint64_t)cpu << 8;
        char label[] = "CPU0";
        label[3] = '0' + cpu;
        int64_t state = smc(PSCI_AFFINITY_INFO, target, 0, 0);
        if (state != AFFINITY_OFF) {
            con_hex2(label, "before=", state, "skip=", 1); return 0;
        }
        barrier();
        int64_t on_return = smc(PSCI_CPU_ON, target, (uintptr_t)secondary_entry, cpu);
        volatile struct observation *o = &observations[cpu];
        if (!on_return) {
            uint64_t end = now() + freq / 2;
            do {
                barrier();
                state = smc(PSCI_AFFINITY_INFO, target, 0, 0);
                if ((o->ready && state == AFFINITY_OFF) || o->ready == 2) break;
                uint64_t next = now() + freq / 1000;
                while (now() < next) ;
            } while (now() < end);
        }
        barrier();
        con_hex2(label, "on=", on_return, "state=", state);
        con_hex2("CORE", "midr=", o->midr, "mpidr=", o->mpidr);
        con_hex2("FEAT", "mmfr0=", o->mmfr0, "sctlr=", o->sctlr);
        con_hex2("BOOT", "el=", o->el, "ready=", o->ready);
        if (o->ready == 2) con_hex("OFF RET", o->off_return);
        if (on_return || state != AFFINITY_OFF || o->ready != 1 || o->el != 1 ||
            (o->mpidr & AFFINITY_MASK) != target || (o->sctlr & 5) ||
            ((o->mmfr0 >> 20) & 15) != 1) return 0;
    }
    return 1;
}
