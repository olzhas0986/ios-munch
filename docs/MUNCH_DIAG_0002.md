# Munch DIAG0002: CPU0 16K MMU and interrupts

## Input evidence

The user transcribed the successful DIAG0001 screen:

```text
DTB     00000000AFDFD000
EL      0000000000000001
MIDR    0000000051DF805E
MPIDR   0000000081000000
MMFR0   0000000000101122
CNTFRQ  00000000124F800
SCTLR   000000000C00808
```

The last two strings are preserved exactly; omitted digits were not inferred.
CNTFRQ0x124f800 is19,200,000Hz; MMFR0 indicates 16K granule support.

## Experiment

The existing board/splash guard remains. Precheck requires 16K support and
SCTLR.M/C initially off. Existing shim/mmu.c builds identity mappings with
16K pages: own Image Normal-WB, framebuffer Normal-NC, other addresses below
8GiB Device/XN, and no mapping above8GiB. Other DDR is not probed or allocated.

AT S1E1R checks Image/framebuffer/GIC and an intentionally unmapped8GiB
address, printing SCTLR/TCR/PAR. GICv3 selects the current redistributor by
MPIDR, configures Group1, virtual timerINTID27, physical timer30 and selfSGI1.
There is no SMP/PSCI. RWP/WAKER waits are bounded.

Each timer runs for about300ms, yielding about30 interrupts; SGI is sent10
times. Counts are hexadecimal:1E and0A. Pending/HPPIR/timer state/lastINTID
are also printed. Unexpected IRQs are masked and make the result incomplete.
Timers and selected sources are disabled after testing. PASS requires valid
translation checks, >=10 IRQs per timer, exactly10 SGIs and no unexpected IRQ.

Exceptions produce a blue screen with STAGE/ESR/ELR/FAR/SPSR. Otherwise a
failed check prints TESTS INCOMPLETE. No UFS/XNU/partition/clock/power/DSI
programming is included.

References: [Linux GICv3](https://raw.githubusercontent.com/torvalds/linux/master/drivers/irqchip/irq-gic-v3.c)
and [ARM64 boot protocol](https://docs.kernel.org/arch/arm64/booting.html).

## Build, validation and physical result

Build: `bash shim/munch/build.sh 0002`.
Output: `shim/out/munch-diag-0002/testios.img`,163840bytes,boot-v3.
SHA256: `23d8041bb599d7f77cf232bc34b93155940937231c5968ead464b3e39afe494b`.

Warnings-as-errors cross-build, undefined/relocation checks and boot
roundtrip passed. A native harness exercised real MMU table construction
with register/cache-operation stubs: one/two L3 tables, identity PA,
WB/NC/Device/XN, the8GiB hole, TCR16K and SCTLR.M/C/I. This is not ARM64
execution. Harness: ignored research/munch/mmu-host-0002.c.

The user subsequently confirmed MMU IRQ TESTS PASS: both timers0x1E,
SGI0x0A, unexpected0. Thus these checks passed on the real phone.
[Next experiment: PSCI](MUNCH_DIAG_0003.md).

```bat
copy /Y "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\shim\out\munch-diag-0002\testios.img" C:\platform-tools\testios.img
cd /d C:\platform-tools
fastboot boot testios.img
```

Use temporary boot only, for one verified munch in bootloader fastboot.
