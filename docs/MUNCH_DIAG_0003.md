# Munch DIAG0003: sequential PSCI CPU1–CPU7 entry and power-off

DIAG0002 passed on hardware: virtualINTID27 and physicalINTID30 each delivered
0x1E IRQs; selfSGI1 delivered0x0A; unexpected0. This does not establish
cross-CPU SGI delivery or secondary MMU behavior.

## Sequential experiment

With MMU/D-cache off on every participant, CPU0 uses PSCI overSMC and live-DT
affinities0x100…0x700. This avoids sharing WB data with a cache-off secondary.
API constants follow [Linux PSCI definitions](https://raw.githubusercontent.com/torvalds/linux/master/include/uapi/linux/psci.h).

For each core, require initial AFFINITY_INFO=OFF, invoke CPU_ON64 with its
own stack, and record MIDR/MPIDR/MMFR0/EL/SCTLR. Publish ready1 with barriers,
then invoke CPU_OFF. CPU0 waits up to about500ms and verifies final OFF.
CPU_OFF returning is an error, ready2 and OFF RET. Stop at the first failure.

Expected core record:

```text
CPU1 on=00000000 state=00000001
CORE midr=........ mpidr=........
FEAT mmfr0=........ sctlr=........
BOOT el=00000001 ready=00000001
```

Different MIDRs across core groups are expected. PASS requires correct MPIDR,
EL1,16K support, SCTLR.M/C off, ready1, successful CPU_ON and final OFF.
No GIC, UFS, XNU, clock/voltage, DSI or cross-CPU SGI programming is included.

## Build and evidence

Build: `bash shim/munch/build.sh 0003`.
Output: `shim/out/munch-diag-0003/testios.img`,90112bytes,boot-v3.
SHA256: `d44d0b64d30ee110d88ba888469136654c3f582fdfd6dd3cc0b157ba37844d51`.

Cross-build, no undefined/relocations, Image/header/boot roundtrip and old
image hashes passed. Native mocked control flow accepted seven correct
records and rejected CPU_ON/OFF failures, wrong affinity/EL/granule/cache
state, timeout, already-on and unsupported PSCI. Harness is ignored at
research/munch/smp-host-0003.c; this model does not execute ARM64.

Physical result: CPU1–CPU4 entered and powered off; CPU5 remained ON_PENDING
with ready0. CPU6–CPU7 were not reached. [DIAG0004](MUNCH_DIAG_0004.md)
adds early entry markers and changes the experiment.

```bat
copy /Y "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\shim\out\munch-diag-0003\testios.img" C:\platform-tools\testios.img
cd /d C:\platform-tools
fastboot boot testios.img
```

Temporary boot only; never flash this diagnostic.
