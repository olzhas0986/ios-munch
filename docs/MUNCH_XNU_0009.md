# Munch XNU0009: a real HFS+ RAMDisk root

XNU0008 confirmed static PID1 execution through mockfs. This next test
places the same static probe in /sbin/launchd on a real 16 MiB HFS+ volume.
PID1 opens and reads a separate /etc/munch-release catalog file. Its output
must include `MUNCH HFS: /etc/munch-release read OK`, followed by heartbeats.
This tests real filesystem lookup/read before dyld and Apple userland.
It does not yet include dyld or Apple launchd.

The existing kernel from run 39582602130 is unchanged. No UFS driver or
persistent storage is involved. The root is unjournaled HFS+ in RAM;
/dev is present for devfs. Only CPU0 is exposed. XNU0008 is preserved.

## Host tools

The local tools were built from these pinned source revisions:

- https://github.com/planetbeing/xpwn at 20c32e5c12d1b22a9d55a59a0ff6267f539b77f4
- https://github.com/Artoria2e5/hfsprogs at 8caed30fc3609537ecf5f5ebcccf10509ac7d8f2

The xpwn hfs editor was built using its hfs/*.c, common/abstractfile.c and
common/base64.c, include path includes, -O2 -fcommon -D_FILE_OFFSET_BITS=64,
and -lz. Binary: /tmp/munch-hfsplus (rebuild if /tmp is cleared).

For hfsprogs all patches listed in debian/patches/series were applied in
order. Two host-only compatibility changes were needed for current glibc:
remove bsd/string.h from include/missing.h (string.h supplies the interfaces),
and guard sys/sysctl.h in newfs_hfs.tproj/makehfs.c with #if !LINUX.
Built newfs_hfs.tproj/Makefile.lnx with CFLAGS=-O2, the absolute include
path to its include directory, -DDEBUG_BUILD=0 -D_FILE_OFFSET_BITS=64
-DLINUX=1 -DBSD=1 -Wno-implicit-function-declaration. OpenSSL and zlib
headers/libraries are required. These host builds do not install anything.

## Image construction

```sh
bash tools/build-munch-init.sh hfs
python3 tools/mkmunchroot.py research/munch/hfsprogs/newfs_hfs.tproj/newfs_hfs /tmp/munch-hfsplus shim/out/munch-init-0009/init.macho shim/out/munch-init-0009/root.hfs
bash shim/munch/build-xnu.sh research/munch/xnu-run-39582602130/kernel.development.sweet ../live.dtb shim/out/munch-init-0009/root.hfs
```

The HFS builder operates on a new regular temporary file and inserts files
without mounting, loop devices or elevated permissions. It extracts init
and marker back and compares their bytes, checks the HFS volume header
and executable mode 0555, then replaces the generated output image.
The RAMDisk is at PA 0x102078000, length 0x1000000. ADT/boot-args follow it.

Output: shim/out/munch-xnu-0009/testios.img, 33,206,272 bytes, SHA256
`84acbd564885ad26230707561ba51655f69f160525d092e9acccc09ed0258582`.
Verified boot-v3 Image/payload roundtrip, RAMDisk ADT/segment/bounds,
loader host tests with five prefixes and eight malformed inputs, cross-build,
RAM audit and repository validation. Physical HFS mount/read is pending.

```bat
copy /Y "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\shim\out\munch-xnu-0009\testios.img" C:\platform-tools\testios.img
cd /d C:\platform-tools
fastboot boot testios.img
```

Capture the HFS marker or the complete panic. Temporary boot only.
