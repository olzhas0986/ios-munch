# Munch XNU0013: restore account database for launchd

XNU0012 photo 5386382558695726529.jpg confirms Apple launchd running as
PID1, libignition completion, Darwin Bootstrapper logging and restore boot
task processing. It then exits with reason namespace7/subcode1:
`unable to resolve 'mobile': 114 - The specified username does not exist`.
The kernel panics because PID1 exited. No managed-service success was shown.
The remount result is not visible in this photo.

The minimal root previously contained only a root passwd record and wheel
group. The restore image has /private/etc/master.passwd and group, including
mobile UID/GID501. libsystem_info contains /etc/master.passwd as its lookup
path. This image supplies the unmodified restore master.passwd (mode0600),
the restore group file and a generated seven-field passwd view with password
fields hidden as *. All account inputs remain ignored outside git.

```sh
mkdir -p research/munch/restore-accounts
/tmp/munch-apfs-read research/munch/restore-20H392.apfs /private/etc/master.passwd research/munch/restore-accounts/master.passwd
/tmp/munch-apfs-read research/munch/restore-20H392.apfs /private/etc/group research/munch/restore-accounts/group
python3 tools/mkmunchroot.py research/munch/hfsprogs/newfs_hfs.tproj/newfs_hfs /tmp/munch-hfsplus shim/out/munch-init-0012/init.macho shim/out/munch-init-0013/root.hfs --userland research/munch/launchd-userland --launchd --system-version research/munch/launchd-SystemVersion.plist --accounts research/munch/restore-accounts
bash shim/munch/build-xnu.sh research/munch/xnu-run-39582602130/kernel.development.sweet ../live.dtb shim/out/munch-init-0013/root.hfs
```

Kernel, Apple executables and diagnostic PID1 are unchanged. Output uses
XNU0013 shim identification. HFS builder validates root/mobile IDs, account
record shapes and mobile group before insertion. File extraction compares
master.passwd/group exactly to source and checks generated passwd/mobile
and mode0600. Loader host scenarios, boot roundtrip, RAM audit, cross-build
and repository validation pass. Runtime account lookup is not yet confirmed.

Image: shim/out/munch-xnu-0013/testios.img,125480960 bytes,SHA256
`59e38e1e3fa11471cbbe1675ae61555eb2224f5e0aab25a1bfad66a8cb7b4561`.

```bat
copy /Y "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\shim\out\munch-xnu-0013\testios.img" C:\platform-tools\testios.img
cd /d C:\platform-tools
fastboot boot testios.img
```

Capture output after the boot tasks, especially the managed-service marker
or complete panic. Temporary boot only. Preserve successful XNU0011.

## Hardware result

Photo 5386693037586587026.jpg confirms successful account lookup, xpcproxy
execution, launchd-managed org.munch.probe, the service marker and exit(0).
The one-shot service is then removed as configured. No panic is visible.
Missing AppleInternal directories, system-event logging/persona warnings
and empty shared-region probes remain; they did not prevent this test.
This validates one service lifecycle, not the complete iOS service set.
