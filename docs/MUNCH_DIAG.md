# Munch DIAG0001: initial splash experiment

Build explicitly with `bash shim/munch/build.sh 0001`. The default now selects
[DIAG0004](MUNCH_DIAG_0004.md).

Output: `shim/out/munch-diag-0001/testios.img`, 86016 bytes, boot-v3,
Linux Image placement hint0x80000. Installed vendor_boot/DTBO supplies the
ABL DT; no donor DTB is embedded. OS metadata matches the provided stock
boot:13.0.0/2025-04.

SHA256: `5cde144e114e7cea0ad14a1caa4d3f42a7bc77ff2051133cf68ab0954d9fc94a`.
This is a temporary fastboot-boot experiment, not XNU/iOS or a flash image.

## Behavior

CPU0 masks interrupts, establishes its stack and checks root board-id
`<0x32 0>` plus reserved-memory/cont_splash_region@9c000000 at0x9c000000,
size at least1080×2400×4. A mismatch stops without splash writes. It expects
a valid ABL FDT pointer inx0.

The screen prints MUNCH DIAG0001 and DTB/EL/MIDR/MPIDR/MMFR0/CNTFRQ/SCTLR,
then waits inWFE. There is no software reset; hold power to restart. An
inherited firmware watchdog may also reset the device.

The link contains only start/console/guard/diag. No UFS, XNU, MMU, PSCI,
secondary startup, GIC, DSI, power or clock programming. Writes affect its own
RAM and guarded splash reservation. The guard does not prove scanout format;
linear32-bit pixels/stride4320 were initially a hypothesis.

## Validation and physical result

Cross-build used warnings-as-errors, no undefined symbols or relocations.
Repeated builds produced the same hash. Boot unpack roundtrip, Image size
and gzip/newc were checked. Native guard cases accepted live munch and
rejected wrong board/reservation/magic/truncation. QEMU was unavailable.

The user confirmed MUNCH DIAG0001 and STATUS CPU0 C ENTRY OK on the phone.
Thus CPU0 entered C and splash writes were visible without explicit DSI
programming. This did not yet test MMU/IRQ/SMP or continuous updates.

All subsequent boot artifacts are named **testios.img**, with test versions
in directory names and screen text.

## Windows CMD

```bat
copy /Y "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\shim\out\munch-diag-0001\testios.img" C:\platform-tools\testios.img
cd /d C:\platform-tools
fastboot getvar product
```

For exactly one munch in bootloader fastboot, not fastbootd:

```bat
fastboot boot testios.img
```

Report fastboot output and screen observations. OKAY proves acceptance by
ABL, not execution of our C code. Never use flash/erase for this experiment.
