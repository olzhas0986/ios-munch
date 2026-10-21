# Munch XNU0005: first CPU0 kernel handoff

## Kernel provenance

The early kernel built successfully in
https://github.com/olzhas0986/ios-munch/actions/runs/39572263994.
Artifact12332518950 contains plain ARM64 kernel.development.sweet,
16,923,712bytes, SHA256
`b391e0376f6ee6d790b263cee839241474c706b48159e12dbe51610fbc83a597`.
The downloaded file matched SHA256SUMS. Build scope is patches0001–0027;
sweet UFS, USB and input drivers are absent.

## Boot image

Build from the extracted artifact directory and the supplied live FDT:

```sh
bash shim/munch/build-xnu.sh research/munch/xnu-run-39572263994/kernel.development.sweet ../live.dtb
```

The script validates kernel hashes, plain ARM64 type and the exact early
patch manifest before packaging. tools/mkmunchadt.py audits board-id,
DDR coverage, fixed reservations, dynamic allocation ranges and FDT
memreserve entries before selecting4..5GiB. The ADT contains CPU0 only,
virtualINTID27, tested splash geometry and no UFS node. The missing Apple
product-tree warning is expected for this early kernel-only experiment.

The shim links only start, console, FDT parsing, guarded payload loading,
board/splash guard and the handoff entry. It does not link UFS diagnostics,
PSCI/SMP or the ordinary sweet hardware probe. Source and destination bounds
are validated before writes to the XNU aperture. Boot-v3 vendor ramdisk
prefixes are located without assuming8-byte payload alignment; packed
metadata and byte-copy fallback avoid unaligned Device-memory accesses.

Boot arguments use CPU0 and rd=md0, but no root RAMDisk is supplied yet.
The expected milestone is early XNU output or an observable no-root stop,
not SpringBoard. Original SWEET console labels come from the shared kernel
implementation. Their appearance does not mean a sweet image was flashed.

Output: `shim/out/munch-xnu-0005/testios.img`,16,424,960bytes,boot-v3.
Current SHA256:
`2d2244af0c18b0d3214fd1945ccf3922e8a20d1530e9119f803f182bffdc2da8`.
New builds contain a fresh ADT random seed and may have different hashes.

## Validation and limits

- Warnings-as-errors cross-build; no undefined symbols or ELF relocations.
- Boot unpack roundtrip matches Image and payload; Image size verified.
- Native loader harness exercised prefixes0,1,7,2347,4096; every segment,
  BSS, ADT and boot-args field was checked against the actual payload.
- Eight malformed size/count/address/entry cases failed before writes/jump.
- RAM audit accepted the supplied live DT and rejected a wrong board,
  insufficient DDR, fixed-reservation overlap and dynamic-pool overlap.
- Harnesses model hardware operations; XNU0005 has not booted on the phone.
  No persistent partitions are accessed by this selected kernel/shim.

## Windows CMD

```bat
copy /Y "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\shim\out\munch-xnu-0005\testios.img" C:\platform-tools\testios.img
cd /d C:\platform-tools
fastboot getvar product
```

For exactly one munch in bootloader fastboot:

```bat
fastboot boot testios.img
```

Capture the full screen, especially SWEET EARLY/PANIC or the last visible
line. A shim exception/ERROR/PREFIX line is also useful. Never flash this
image; hold power to reboot after observing the result.
