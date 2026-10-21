/* Keep secondary cores resident until every CPU_ON has been attempted.
 * Primary and secondaries run MMU/D-cache off. No storage/GIC/clock writes.
 */
#include <stdint.h>
#include "console.h"
#include "smp.h"
#include "entry-layout.h"

#define reg(name) ({ uint64_t v; __asm__ volatile("mrs %0, " name : "=r"(v)); v; })
#define barrier() __asm__ volatile("dsb sy; isb" ::: "memory")
#define PSCI_VERSION 0x84000000UL
#define PSCI_CPU_OFF 0x84000002UL
#define PSCI_CPU_ON 0xc4000003UL
#define PSCI_AFFINITY_INFO 0xc4000004UL
#define AFFINITY_MASK 0xff00ffffffULL
#define CPUS 8

struct observation {
    uint64_t mpidr, midr, mmfr0, el, sctlr;
    int64_t off_return;
    uint32_t ready;
};
volatile struct entry_record munch_entry_records[CPUS];
static volatile struct observation observations[CPUS];
static volatile uint32_t release_all;
extern char munch_secondary_entry[];

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
static void pause_ms(void)
{
    uint64_t end = now() + reg("cntfrq_el0") / 1000;
    while (now() < end) ;
}
static void __attribute__((noreturn)) park(void)
{
    for (;;) __asm__ volatile("wfe");
}

void munch_smp_secondary_exception(unsigned slot)
{
    unsigned cpu = (reg("mpidr_el1") >> 8) & 255;
    if (!cpu || cpu >= CPUS) return;
    volatile struct entry_record *e = &munch_entry_records[cpu];
    e->esr = reg("esr_el1");
    e->elr = reg("elr_el1");
    e->far = reg("far_el1");
    barrier();
    e->stage = 0xe0 + (slot & 15);
    observations[cpu].ready = 3;
    barrier();
    park();
}

void secondary_main(uint64_t cpu)
{
    if (!cpu || cpu >= CPUS) park();
    volatile struct observation *o = &observations[cpu];
    o->mpidr = reg("mpidr_el1");
    o->midr = reg("midr_el1");
    o->mmfr0 = reg("id_aa64mmfr0_el1");
    o->el = reg("CurrentEL") >> 2;
    o->sctlr = reg("sctlr_el1");
    munch_entry_records[cpu].stage = 3;
    barrier();
    o->ready = 1;
    barrier();
    while (!release_all) __asm__ volatile("wfe" ::: "memory");
    munch_entry_records[cpu].stage = 4;
    barrier();
    o->off_return = smc(PSCI_CPU_OFF, 0, 0, 0);
    barrier();
    munch_entry_records[cpu].stage = 5;
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
    con_str("SMP", "HOLD CORES UNTIL ALL ON");
    int64_t ret[CPUS] = {0}, state[CPUS] = {0};
    uint32_t seen[CPUS] = {0};
    uint64_t freq = reg("cntfrq_el0");
    for (unsigned cpu = 1; cpu < CPUS; cpu++) {
        uint64_t target = (uint64_t)cpu << 8;
        state[cpu] = smc(PSCI_AFFINITY_INFO, target, 0, 0);
        ret[cpu] = -4;
        if (state[cpu] == 1) {
            ret[cpu] = smc(PSCI_CPU_ON, target, (uintptr_t)munch_secondary_entry, cpu);
            if (!ret[cpu]) {
                uint64_t end = now() + freq * 2;
                do {
                    barrier();
                    if (observations[cpu].ready) break;
                    pause_ms();
                } while (now() < end);
            }
        }
        seen[cpu] = observations[cpu].ready;
        state[cpu] = smc(PSCI_AFFINITY_INFO, target, 0, 0);
        char label[] = "START0"; label[5] = '0' + cpu;
        con_hex2(label, "on=", ret[cpu], "state=", state[cpu]);
    }
    /* SEV closes the check/WFE race; no interrupt configuration is needed. */
    release_all = 1;
    barrier();
    __asm__ volatile("sev" ::: "memory");
    uint64_t end = now() + freq * 2;
    int all_off;
    do {
        all_off = 1;
        for (unsigned cpu = 1; cpu < CPUS; cpu++) {
            state[cpu] = smc(PSCI_AFFINITY_INFO, (uint64_t)cpu << 8, 0, 0);
            if (!ret[cpu] && state[cpu] != 1) all_off = 0;
        }
        if (all_off) break;
        pause_ms();
    } while (now() < end);

    con_clear(0xff102030);
    con_str("MUNCH", "DIAG 0004 RESULTS");
    con_hex("PSCI", version);
    con_str("SMP", "FINAL STATE AFTER OFF");
    int ok = 1;
    for (unsigned cpu = 1; cpu < CPUS; cpu++) {
        volatile struct observation *o = &observations[cpu];
        volatile struct entry_record *e = &munch_entry_records[cpu];
        char label[] = "CPU0"; label[3] = '0' + cpu;
        con_hex2(label, "on=", ret[cpu], "state=", state[cpu]);
        con_hex2("ENTRY", "asm=", e->stage, "ctx=", e->context);
        con_hex2("CORE", "midr=", o->midr, "mpidr=", o->mpidr);
        con_hex2("FEAT", "mmfr0=", o->mmfr0, "sctlr=", o->sctlr);
        con_hex2("BOOT", "el=", o->el, "ready=", o->ready);
        if (e->stage >= 0xe0) {
            con_hex("ESR", e->esr); con_hex("ELR", e->elr); con_hex("FAR", e->far);
        } else if (o->ready == 2) con_hex("OFF RET", o->off_return);
        if (ret[cpu] || state[cpu] != 1 || seen[cpu] != 1 || o->ready != 1 ||
            e->stage != 4 || e->context != cpu || o->el != 1 ||
            (o->mpidr & AFFINITY_MASK) != (uint64_t)cpu << 8 ||
            (o->sctlr & 5) || ((o->mmfr0 >> 20) & 15) != 1) ok = 0;
    }
    return ok;
}
