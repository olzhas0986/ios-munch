/* Munch CPU0-only MMU/GIC probe. No UFS, PSCI or secondary CPU startup. */
#include <stdint.h>
#include "console.h"
#include "mmu.h"
#include "probe.h"

#define readreg(name) ({ uint64_t v; __asm__ volatile("mrs %0, " name : "=r"(v)); v; })
#define writereg(name, value) __asm__ volatile("msr " name ", %0" : : "r"((uint64_t)(value)) : "memory")
#define barrier() __asm__ volatile("dsb sy; isb" ::: "memory")
#define GICD 0x17a00000UL
#define GICR 0x17a60000UL
#define SGI 1
#define VTIMER 27
#define PTIMER 30
#define SOURCES ((1U << SGI) | (1U << VTIMER) | (1U << PTIMER))

static const char *stage;
static uintptr_t rdist;
static volatile uint32_t count, other, last;
static uint32_t source;
static int ready, split_eoi;

const char *munch_stage(void) { return stage ? stage : "CPU0 ENTRY"; }
int munch_irq_ready(void) { return ready; }
static uint32_t rd(uintptr_t p) { return *(volatile uint32_t *)p; }
static void wr(uintptr_t p, uint32_t v) { *(volatile uint32_t *)p = v; }
static uint64_t now(void) { __asm__ volatile("isb"); return readreg("cntpct_el0"); }

/* Bounded even if a device never acknowledges the change. */
static int wait_clear(uintptr_t p, uint32_t mask)
{
    for (unsigned i = 0; i < 1000000; i++) if (!(rd(p) & mask)) return 1;
    return 0;
}

void munch_irq_handler(void)
{
    uint64_t iar = readreg("icc_iar1_el1");
    uint32_t id = iar & 0xffffff;
    if (id >= 1020 && id <= 1023) return;
    last = id;
    if (id == source) count++; else other++;
    if (id == VTIMER) writereg("cntv_tval_el0", readreg("cntfrq_el0") / 100);
    else if (id == PTIMER) writereg("cntp_tval_el0", readreg("cntfrq_el0") / 100);
    else if (id != SGI && id < 1020) {
        /* Mask inherited unexpected interrupts instead of risking a storm. */
        uintptr_t base = id < 32 ? rdist + 0x10000 : GICD;
        wr(base + 0x180 + (id / 32) * 4, 1U << (id % 32));
    }
    barrier();
    writereg("icc_eoir1_el1", iar);
    if (split_eoi) writereg("icc_dir_el1", iar);
    __asm__ volatile("isb" ::: "memory");
}

static uint64_t self_sgi(void)
{
    uint64_t m = readreg("mpidr_el1");
    return ((m >> 32) & 0xff) << 48 | ((m >> 16) & 0xff) << 32 |
           ((m >> 8) & 0xff) << 16 | (uint64_t)SGI << 24 | (1U << (m & 15));
}

static int gic_init(void)
{
    stage = "GIC SYSREG";
    writereg("icc_sre_el1", readreg("icc_sre_el1") | 1);
    __asm__ volatile("isb");
    if (!(readreg("icc_sre_el1") & 1)) return 0;
    stage = "GIC REDIST";
    uint64_t m = readreg("mpidr_el1");
    uint32_t affinity = (m & 0xffffff) | ((m >> 8) & 0xff000000);
    for (uintptr_t off = 0; off < 0x100000; off += 0x20000) {
        uint64_t typer = *(volatile uint64_t *)(GICR + off + 8);
        if ((uint32_t)(typer >> 32) == affinity) { rdist = GICR + off; break; }
        if (typer & (1U << 4)) break;
    }
    if (!rdist) return 0;
    wr(rdist + 0x14, rd(rdist + 0x14) & ~2U);
    if (!wait_clear(rdist + 0x14, 4)) return 0;
    stage = "GIC DISTRIBUTOR";
    uint32_t before = rd(GICD);
    /* NS view: ARE_NS + EnableGrp1A + EnableGrp1, as in Linux GICv3. */
    wr(GICD, before | 0x13);
    if (!wait_clear(GICD, 1U << 31)) return 0;
    con_hex2("GICD", "old=", before, "new=", rd(GICD));
    con_hex("GICR", rdist);
    stage = "GIC LOCAL CONFIG";
    uintptr_t s = rdist + 0x10000;
    wr(s + 0x180, SOURCES);
    if (!wait_clear(rdist, 1U << 3)) return 0;
    wr(s + 0x280, SOURCES);
    wr(s + 0x80, rd(s + 0x80) | SOURCES);
    for (unsigned id = 0; id < 32; id++) if (SOURCES & (1U << id))
        *(volatile uint8_t *)(s + 0x400 + id) = 0xa0;
    /* Both timer PPIs are level-triggered; SGI has fixed edge semantics. */
    wr(s + 0xc04, rd(s + 0xc04) & ~((2U << ((VTIMER - 16) * 2)) |
                                           (2U << ((PTIMER - 16) * 2))));
    wr(s + 0x100, SOURCES);
    if (!wait_clear(rdist, 1U << 3)) return 0;
    writereg("icc_ctlr_el1", readreg("icc_ctlr_el1") & ~2ULL);
    __asm__ volatile("isb");
    split_eoi = !!(readreg("icc_ctlr_el1") & 2);
    writereg("icc_pmr_el1", 0xf0);
    writereg("icc_bpr1_el1", 0);
    writereg("icc_igrpen1_el1", 1);
    barrier();
    con_hex2("ICC", "ctlr=", readreg("icc_ctlr_el1"), "group1=", readreg("icc_igrpen1_el1"));
    con_hex("ENABLE", rd(s + 0x100));
    ready = 1;
    return 1;
}

static int window(const char *label, unsigned id)
{
    stage = label;
    uint64_t freq = readreg("cntfrq_el0");
    source = id;
    count = other = 0;
    last = 0x3ff;
    if (id == VTIMER) {
        writereg("cntv_tval_el0", freq / 100);
        writereg("cntv_ctl_el0", 1);
    } else if (id == PTIMER) {
        writereg("cntp_tval_el0", freq / 100);
        writereg("cntp_ctl_el0", 1);
    } else writereg("icc_sgi1r_el1", self_sgi());
    barrier();
    uint64_t until = now() + freq / 50;
    while (now() < until) ;
    uint32_t pending = rd(rdist + 0x10200);
    uint32_t hppi = readreg("icc_hppir1_el1");
    uint32_t tctl = id == VTIMER ? readreg("cntv_ctl_el0") :
                    id == PTIMER ? readreg("cntp_ctl_el0") : 0;
    until = now() + freq * 3 / 10;
    uint64_t next = now() + freq / 100;
    unsigned sent = 1;
    __asm__ volatile("msr daifclr, #2; isb" ::: "memory");
    while (now() < until) {
        if (id == SGI && sent < 10 && now() >= next) {
            writereg("icc_sgi1r_el1", self_sgi());
            __asm__ volatile("isb");
            sent++; next += freq / 100;
        }
    }
    __asm__ volatile("msr daifset, #2; isb" ::: "memory");
    writereg("cntv_ctl_el0", 0);
    writereg("cntp_ctl_el0", 0);
    barrier();
    wr(rdist + 0x10280, SOURCES);
    con_hex2(label, "irqs=", count, "other=", other);
    con_hex2("PRE", "pend=", pending, "hppi=", hppi);
    con_hex2("RESULT", "tctl=", tctl, "last=", last);
    return !other && (id == SGI ? count == 10 : count >= 10 && last == id);
}

int munch_probe(void)
{
    stage = "MMU PRECHECK";
    uint64_t mmfr = readreg("id_aa64mmfr0_el1");
    if (((mmfr >> 20) & 15) != 1 || (readreg("sctlr_el1") & 5)) {
        con_str("MMU", "PRECHECK FAILED"); return 0;
    }
    struct mmu_info info;
    stage = "MMU ENABLE";
    con_str("STAGE", "ENABLING 16K MMU");
    barrier();
    if (mmu_enable(&info)) { con_str("MMU", "LAYOUT FAILED"); return 0; }
    stage = "MMU TRANSLATION";
    uint64_t img = mmu_probe((uintptr_t)munch_probe), fb = mmu_probe(FB_BASE);
    uint64_t gic = mmu_probe(GICD), hole = mmu_probe(0x200000000UL);
    con_hex("SCTLR+", info.sctlr_after);
    con_hex("TCR", readreg("tcr_el1"));
    con_hex("PAR IMG", img);
    con_hex("PAR FB", fb);
    con_hex("PAR GIC", gic);
    con_hex("PAR HOLE", hole);
    if ((img | fb | gic) & 1 || !(hole & 1)) {
        con_str("MMU", "TRANSLATION FAILED"); return 0;
    }
    con_str("MMU", "16K TRANSLATION OK");
    if (!gic_init()) { con_str("GIC", "INIT INCOMPLETE"); return 0; }
    int v = window("VTIMER27", VTIMER);
    int p = window("PTIMER30", PTIMER);
    int s = window("SGI1", SGI);
    wr(rdist + 0x10180, SOURCES);
    barrier();
    stage = "COMPLETE";
    return v && p && s;
}
