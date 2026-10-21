# Munch XNU0008: RAMDisk and first userspace process

XNU0007 reached BSD startup and stopped because rd=md0 had no configured
RAMDisk. This image adds a static, ad-hoc signed ARM64 Mach-O as a RAMDisk.
The existing mockfs root filesystem exposes that executable as
/sbin/launchd and provides /dev for devfs. No HFS image is needed for this
single-program test. This is a PID1 probe, not Apple launchd or the iOS UI.

The program opens /dev/console, writes its PID, and prints a heartbeat
after each five-second select timeout. It never exits. Code is position
independent, has no relocations or external libraries and uses raw XNU
syscalls. The GNU ARM64 assembler and the existing Mach-O wrapper allow
building it on Linux without an Apple SDK.

```sh
bash tools/build-munch-init.sh
bash shim/munch/build-xnu.sh research/munch/xnu-run-39582602130/kernel.development.sweet ../live.dtb shim/out/munch-init-0008/init.macho
```

Kernel and patch set are unchanged from XNU0007. The shim screen says
XNU 0008. RAMDisk is at PA 0x102078000, length 0x8000, within the audited
4..5 GiB aperture. ADT and boot-args are placed after it. The executable
is 16,635 bytes; its RAMDisk segment is zero-padded to 32 KiB.

Output: shim/out/munch-xnu-0008/testios.img, 16,445,440 bytes, SHA256
`13b6cfb24503dd4bbd6120f050aca413e0332a742aa36ae99381025c6fec1427`.

Checks passed: RAMDisk segment/ADT correspondence and bounds, static
Mach-O thread entry, all CodeDirectory page hashes, boot-v3 roundtrip,
loader harness with five prefixes/eight rejected malformed inputs,
RAM audit, cross-build and repository validation.

Hardware confirmed md0 root, execution of /sbin/launchd, PID 1 output and
repeated MUNCH heartbeat messages. No panic is visible in the supplied
photo. The heartbeat is intentional; its exact interval was not measured.

```bat
copy /Y "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\shim\out\munch-xnu-0008\testios.img" C:\platform-tools\testios.img
cd /d C:\platform-tools
fastboot boot testios.img
```

Expected milestone: `MUNCH userspace: init running as PID 1`, followed by
`MUNCH init: still alive`. Capture output or the complete panic if it stops
before that point. Temporary boot only; no partition writes are required.
