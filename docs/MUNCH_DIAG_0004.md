# Munch DIAG0004: early entry markers and deferred CPU_OFF

## Previous observation

Photo ../WIN_20261021_13_14_45_Pro.jpg, kept outside git, shows DIAG0003
SMP TEST INCOMPLETE and PSCI1.1. CPU1–CPU4 have CPU_ON0, finalOFF1,
ready1 and EL1. CPU4 MIDR is0x411fd0d0, MPIDR0x81000400, MMFR00x101122.
CPU5 has CPU_ON0, ON_PENDING2 and no C record within the500ms window.
CPU6–CPU7 were not tested. This does not establish the cause or a permanent
fault; the effect of powering off CPU4 was only a hypothesis.

## Revised experiment

A separate munch_secondary_entry records hardware MPIDR, original context,
EL, SCTLR and stage before SP/C. Hardware Aff1 indexes the slot independently
of context. C-entry cores remain inWFE until CPU0 has attempted every CPU_ON.
Each core gets up to2s; one timeout does not prevent CPU6/7 testing. Cores
already on before the experiment are left alone.

CPU0 sets release_all and issuesSEV. Entered cores invoke CPU_OFF; the global
power-off wait is bounded to2s. Initial START lines are replaced with the final
all-core table. Its state field is the post-release AFFINITY_INFO.

| ENTRY asm (hex) | Last published stage |
| --- | --- |
| 0 | No early entry marker |
| 1 | Early record, before SP/vectors |
| 2 | SP/VBAR installed, before C |
| 3 | C record, waiting for release |
| 4 | Released, before CPU_OFF |
| 5 | CPU_OFF returned |
| E0–EF | Secondary exception; ESR/ELR/FAR follow |

Context must match CPU. PASS also requires C-entry before release, correct
EL/MPIDR/granule/cache state and finalOFF. Late C-entry after release cannot
turn an earlier timeout intoPASS. MMU/cache remain off; no UFS/XNU/GIC,
clock/voltage or DSI programming. Cache coherence and secondary MMU remain
unverified by this test.

## Build and results

Build: `bash shim/munch/build.sh 0004` (current diagnostic default).
Output: `shim/out/munch-diag-0004/testios.img`,90112bytes.
SHA256: `4d81cd8cb6f9d24f434b2f74837fb7a42f38b02477560ae513fed2828aea1712`.

Cross-build, layout static assertions, no undefined/relocations, boot
roundtrip and disassembly of pre-SP/pre-C stores passed. Native control-flow
harness covered success and12 errors, including pending CPU5, early marker
withoutC, CPU6/7 continuation, cleanup, CPU_OFF return, exceptions, invalid
context/EL/granule/cache, already-on, unsupported PSCI and late entry.
Harness: ignored research/munch/smp-host-0004.c. Old image hashes were unchanged.

Photo ../WIN_20261021_13_23_59_Pro.jpg confirms **SMP START STOP PASS**:
all CPU1–7 on0, finalstate1, asm4, matchingctx, EL1, ready1, MMFR00x101122.
CPU1–3 MIDR0x51df805e; CPU4–7 MIDR0x411fd0d0. CPU5 pending did not recur.
The experiment changed both core retention and timeout, so their effects
are not distinguished by this result.

```bat
copy /Y "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\shim\out\munch-diag-0004\testios.img" C:\platform-tools\testios.img
cd /d C:\platform-tools
fastboot boot testios.img
```

Report the final all-core table and STATUS, or the last START lines if stuck.
Use temporary boot only.
