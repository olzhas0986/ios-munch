# Next milestone: early XNU on munch

## Verified prerequisites

DIAG0001 established CPU0/EL1 and visible splash output. DIAG0002 passed
16K MMU and local Group1 interrupts: virtual27/physical30 each30 IRQs,
selfSGI1 ten, unexpected0. DIAG0004 started and powered off all CPU1–7 with
PSCI1.1 after deferring release. Prior CPU5 pending did not recur.

Affinities are0,0x100,…,0x700. CPU0–3 MIDR0x51df805e, CPU4–7 MIDR0x411fd0d0;
all observed MMFR00x101122. This is not an iOS boot, secondary MMU check or
cross-CPU SGI/coherence test. Initial XNU boot stays CPU0-only.

## Early XNU boundary

The isolated CI build uses upstream patches0001–0027. UFS appears in0028,
writes in0030 and persistent logging in0047. Applying every sweet patch and
changing only ADT is insufficient to isolate mismatched hardware drivers.

Prepare an Apple DT with virtualIRQ27, actual CPU/RAM topology and tested
splash geometry, plus a boot-v3 loader without the ordinary shim/shim.c
hardware diagnostics. tools/mkmunchadt.py audits the live FDT and restricts
XNU to4..5GiB: all28 fixed reservations and12 dynamically allocated pools
exclude that interval; the latter constrain allocation below4GiB.
Payload and actual boot-time layout still require checks before jumping.

Initial boot uses cpus1 and framebuffer console, without UFS root. Observe
early XNU and an expected no-root stop, then add a RAMDisk. Persistent iOS
installation remains a separate later step.

## Build environment

The original build uses macOS/Xcode. Linux cross-compilation is possible in
principle but has not been prepared or verified for this complete kernel;
the local xnu-cc helper only replays individual compile commands.

The user supplied a GitHub fork; the first isolated macOS Actions build
successfully produced plain ARM64 kernel.development.sweet in run39572263994.
See MUNCH_ACTIONS.md. Its SHA256 was verified after download. The kernel has
not yet been booted on munch and is not a ready-made testios.img.

## Approved cleanup

Removed115 derived/corrupt/metadata items, freeing80.7MiB: roundtrip unpack
directories, build objects/Image/ramdisk copies, Zone.Identifier, bytecode,
corrupt device-tree.tar, unrelated board decompilations and extracted binary
duplicates. All are reproducible from retained originals.

Retained every stock .img, original custom ZIP, valid live.dtb/dt.tar,
iomem/input/dmesg, both photos, configs/selected trees, native harnesses,
and testios.img+diag.elf for all four diagnostics. Historical intermediate
paths may need regeneration. Ledger: ignored research/munch/cleanup-20261021.json.
