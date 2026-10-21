# Munch XNU0016: userspace IOSurface framebuffer probe

This test adds a minimal IOSurface and IOMobileFramebuffer implementation
from upstream patch0046, integrated independently as patch0083. It maps the
inherited ABL framebuffer only when its physical address is0x9c000000,
geometry1080x2400 and stride4320. No display controller programming is added.
The device tree publishes munch,display; internal upstream class names remain.

The RAM root uses the working XNU0014 launchd/account baseline. The failed
syslog job is excluded. A new root job starts /usr/libexec/munch-graphics,
a plain ARM64 Mach-O with twelve actual dyld imports from IOKit, IOSurface
and libSystem. It finds AppleCLCD, opens its user client, requests the default
surface, maps it through IOSurface and validates the native dimensions.

On success the probe prints:

```
MUNCH GRAPHICS: IOSurface mapped 1080x2400; drawing bands
```

It draws three colored bands in rows1700..1939, alternating colors every
two seconds. The rest of the screen remains available to the boot console.
Failure prints a stage number and blocks:1 service lookup,2 opening the
framebuffer,3 requesting the surface port,4 IOSurface lookup,5 geometry or
base address,6 lock/unlock. This is a graphics API probe, not SpringBoard.

Build the probe with `bash tools/build-munch-graphics.sh`. The root builder
uses the baseline launchd userland plus `--graphics` and no `--syslog`:

```sh
python3 tools/mkmunchroot.py research/munch/hfsprogs/newfs_hfs.tproj/newfs_hfs /tmp/munch-hfsplus shim/out/munch-init-0012/init.macho shim/out/munch-init-0016/root.hfs --userland research/munch/launchd-userland --launchd --system-version research/munch/launchd-SystemVersion.plist --accounts research/munch/restore-accounts --graphics shim/out/munch-graphics-0016/probe.macho
```

Host checks validate the twelve imports against the actual restore library
export/reexport tables, Mach-O bounds, entry point, dyld bindings and all
CodeDirectory page hashes. Repository syntax/integrity checks pass.
Kernel CI39615713929 succeeded. Kernel SHA256:
`fff602fc743d5169bb63756fba98733647443d44bb45887b6e952a5af1b36f0c`.
Image: shim/out/munch-xnu-0016/testios.img,125538304 bytes,SHA256
`ef3df9d904fa532fc835bd929b89c633afad21d7141de02011bc72a4d0db3584`.
Boot-v3 kernel/payload roundtrip, reserved-memory audit and loader host
checks pass: five aligned/unaligned prefixes, full segment/BSS/ADT/boot-args
validation and eight malformed inputs rejected before writes or jump.
The embedded probe matches the signed executable; the root has exactly
the graphics job and the working cat job. No physical test yet.

Temporary boot from Windows:

```bat
copy /Y "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\shim\out\munch-xnu-0016\testios.img" C:\platform-tools\testios.img
cd /d C:\platform-tools
fastboot boot testios.img
```

Capture the changing bands and mapped message, or the failure stage/panic.
