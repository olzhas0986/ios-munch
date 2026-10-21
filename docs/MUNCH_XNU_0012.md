# Munch XNU0012: Apple launchd as PID1 and one managed service

XNU0011 successfully ran Apple dyld/libSystem and cat. This image attempts
the next step: a diagnostic static PID1 reads the HFS marker, remounts only
the memory-backed HFS root writable, connects stdout/stderr to the console,
and execs the original Apple restore launchd as PID1.

A child launchd would not validate system bootstrap. Consequently the
static supervisor is replaced on successful exec; if Apple PID1 exits,
the kernel can panic and its complete output is needed. If exec returns,
the static wrapper prints the syscall result and resumes its heartbeat.
No persistent phone storage driver is included or used.

Apple launchd is stored at /usr/libexec/munch-launchd; /sbin/launchd remains
the diagnostic bootstrap executable. Apple launchd and xpcproxy plus their
recursive dependency closure come from the same official 20H392 restore
RAMDisk as XNU0010. There are 86 plain ARM64 files, 101385616 bytes.
All strong dependencies are present; missing weak libraries are recorded
in the ignored userland manifest. Apple binaries stay outside git.

The root is 104 MiB HFS+, with 5705728 free bytes after packaging. It
contains launchd runtime directories, /var -> /private/var, minimal root
account data, the restore SystemVersion.plist and one LaunchDaemon job.
The job runs /bin/cat /etc/munch-service-test, with console stdout/stderr,
RunAtLoad and LaunchOnlyOnce. Its marker is
`MUNCH LAUNCHD: managed service ran OK`.

The wrapper uses mount(hfs, /, MNT_UPDATE, zeroed mount args). XNU consumes
the first user pointer as the device name; the remaining args reach HFS.
The NULL device pointer reuses the existing root mount. This operation
only applies to the RAMDisk. Its result is printed before exec.

The kernel and exact patch allowlist are unchanged from XNU0007.
Boot arguments retain unentitled_ios_sim_launch=1 and add
launchd_log_serial=1, a parameter present in the restore launchd binary.
This is a bootstrap probe, not a complete iOS system or SpringBoard.

## Rebuild

```sh
python3 tools/munch-extract-userland.py /tmp/munch-apfs-read research/munch/restore-20H392.apfs research/munch/launchd-userland --entry /sbin/launchd --entry /usr/libexec/xpcproxy
/tmp/munch-apfs-read research/munch/restore-20H392.apfs /System/Library/CoreServices/SystemVersion.plist research/munch/launchd-SystemVersion.plist
bash tools/build-munch-init.sh launchd
python3 tools/mkmunchroot.py research/munch/hfsprogs/newfs_hfs.tproj/newfs_hfs /tmp/munch-hfsplus shim/out/munch-init-0012/init.macho shim/out/munch-init-0012/root.hfs --userland research/munch/launchd-userland --launchd --system-version research/munch/launchd-SystemVersion.plist
bash shim/munch/build-xnu.sh research/munch/xnu-run-39582602130/kernel.development.sweet ../live.dtb shim/out/munch-init-0012/root.hfs
```

All inserted files/configs were extracted back and byte-compared.
Strong dependency closure, free space, job plist, RAMDisk segment/ADT
bounds, boot-v3 roundtrip, relocation-free cross-build and repository
checks pass. The loader host harness used a 256 MiB mapped fixture for
this larger payload and passed five prefixes and eight malformed cases.
The payload remains within the loader's 128 MiB initrd profile.
No physical XNU0012 result yet; preserve XNU0011 as the working checkpoint.

Image: shim/out/munch-xnu-0012/testios.img,125480960 bytes,SHA256
`54727150d08fe695ab367c4e8954ccc0e78dcbe0e8b7404cd9d5e2448cd44104`.

```bat
copy /Y "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\shim\out\munch-xnu-0012\testios.img" C:\platform-tools\testios.img
cd /d C:\platform-tools
fastboot boot testios.img
```

Capture the mount syscall result, Apple launchd output, service marker or
complete panic. Temporary boot only.
