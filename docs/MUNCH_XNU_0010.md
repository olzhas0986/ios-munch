# Munch XNU0010: Apple dyld and a supervised dynamic child

The user confirmed the HFS read marker on XNU0009. XNU0010 keeps the
static PID1, forks a child and executes Apple's /bin/cat on
/etc/munch-dyld-test. stdout/stderr are connected to /dev/console.
PID1 polls wait4 with WNOHANG, reports raw wait status and continues its
heartbeat. A child failure is observable without deliberately exiting PID1.

Expected success:

- MUNCH DYLD: Apple cat read this file OK
- MUNCH DYLD: child wait status 0x00000000
- Continued MUNCH init: still alive messages

This exercises real Apple dyld and libSystem. It is not Apple launchd or
a complete iOS environment. Hardware success is not yet established.

## Apple file provenance

Source is the official iPhone10,3/iPhone10,6 iOS 16.7.16, build 20H392 IPSW:
https://updates.cdn-apple.com/2025FallFCS/fullrestores/122-77006/1158E502-D76D-4226-AA06-ED5E30CD1111/iPhone10,3,iPhone10,6_16.7.16_20H392_Restore.ipsw

BuildManifest selects 087-86719-047.dmg as the erase RestoreRamDisk.
Only that ZIP member was downloaded with HTTP Range. Its uncompressed
length (106954779) and ZIP CRC32 (2782172389) matched. IM4P contains a
106954752-byte unencrypted APFS image. All Apple files stay ignored under
research/munch; no Apple executable is committed or published.

The APFS reader uses pinned apfs-fuse 66b86bd525e8cb90f9012543be89b1f092b75cf3
and lzfse e634ca58b4821d9f3d560cdc6df5dec02ffc93fd. It reads the image without
FUSE, loop devices or elevated privileges. Build and extract:

```sh
python3 tools/build-munch-apfs-reader.py research/munch/apfs-fuse /tmp/munch-apfs-read
python3 tools/munch-extract-userland.py /tmp/munch-apfs-read research/munch/restore-20H392.apfs research/munch/restore-userland
```

The recursive dependency closure contains 38 plain ARM64 Mach-O files,
10472448 bytes total, with per-file SHA256 in the ignored manifest.json.
Only the optional weak /usr/local/lib/libobjc-env.dylib is unavailable;
all strong dependencies are present. No dyld shared cache is required by
this restore file set; actual runtime loading is the purpose of the test.

## Build and validation

```sh
bash tools/build-munch-init.sh dyld
python3 tools/mkmunchroot.py research/munch/hfsprogs/newfs_hfs.tproj/newfs_hfs /tmp/munch-hfsplus shim/out/munch-init-0010/init.macho shim/out/munch-init-0010/root.hfs --userland research/munch/restore-userland
bash shim/munch/build-xnu.sh research/munch/xnu-run-39582602130/kernel.development.sweet ../live.dtb shim/out/munch-init-0010/root.hfs
```

Kernel/patch set is unchanged from XNU0007. HFS root is still 16 MiB.
Every inserted userland file was extracted back and byte-compared.
RAMDisk ADT/segment/bounds, boot roundtrip, PID1 signature page hashes,
strong dependency closure, cross-build, repository validation and loader
host tests passed. The shim screen identifies itself as XNU 0010.

Image: shim/out/munch-xnu-0010/testios.img, 33206272 bytes, SHA256
`68a4a58625a2274ad00793f48531bb8e0e89a7579d6ea051d8d7577c3a687175`.

```bat
copy /Y "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\shim\out\munch-xnu-0010\testios.img" C:\platform-tools\testios.img
cd /d C:\platform-tools
fastboot boot testios.img
```

Capture the child output/status or panic. Temporary boot only. Preserve
working XNU0008/0009 images; no persistent phone storage access is needed.
