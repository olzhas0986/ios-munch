# Munch XNU0014: launchd restart and RAM filesystem stability

XNU0013 confirmed one managed cat job. XNU0014 retains that job and adds
org.munch.stability, a static ARM64 service with raw XNU syscalls.
It reports PID, real UID and generation after writing a generation byte
to /tmp/munch-service-generation on the RAM root.

On its first invocation it prints three heartbeats (five-second select
waits), announces one requested restart and exits0. KeepAlive=true causes
launchd to start it again. The second process reads the previous byte,
reports generation2 and continues heartbeats without requesting another
exit. ThrottleInterval=5 bounds restart frequency. The job requests root
credentials; the reported UID is the hardware check for that request.

Missing state is accepted only for ENOENT. Other open/read failures, bad
state bytes and short/failed writes report RAM state I/O FAILED and block
without consuming CPU. The service never touches persistent phone storage.
This is a bounded restart probe, not a complete system-service workload.

The new service is signed with an ad-hoc SHA256 CodeDirectory. Its code is
position independent and relocation-free. /tmp and /private/var/tmp now use
mode1777. The Apple launchd/xpcproxy files, kernel and bootstrap PID1 remain
unchanged; XNU0013 and XNU0011 are preserved checkpoints.

```sh
bash tools/build-munch-init.sh service
python3 tools/mkmunchroot.py research/munch/hfsprogs/newfs_hfs.tproj/newfs_hfs /tmp/munch-hfsplus shim/out/munch-init-0012/init.macho shim/out/munch-init-0014/root.hfs --userland research/munch/launchd-userland --launchd --system-version research/munch/launchd-SystemVersion.plist --accounts research/munch/restore-accounts --service shim/out/munch-service-0014/init.macho
bash shim/munch/build-xnu.sh research/munch/xnu-run-39582602130/kernel.development.sweet ../live.dtb shim/out/munch-init-0014/root.hfs
```

Image: shim/out/munch-xnu-0014/testios.img,125480960 bytes,SHA256
`a388e15a912ee5226065cc716a6030af0ffed50e814937adc66e29fb7c2262a9`.

Checks pass: cross-build with no relocations, CodeDirectory page hashes,
service extraction byte equality, launchd job restart policy, /tmp mode,
boot roundtrip, RAM audit and loader host scenarios. Runtime state writes,
credential selection and restart behavior still require phone testing.

```bat
copy /Y "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\shim\out\munch-xnu-0014\testios.img" C:\platform-tools\testios.img
cd /d C:\platform-tools
fastboot boot testios.img
```

After the first MUNCH SERVICE line, allow about30 seconds for the planned
restart. Capture generation1, requesting one restart, generation2 and
subsequent heartbeats, or any error/panic. Temporary boot only.

## Hardware result

The user reported RAM I/O OK, PID0x5, UID0 and generation2. This confirms
root credential selection, launchd restart and state retained on the RAM
filesystem across the two service processes. This is not reboot-persistent
storage or evidence of a long-duration stress test; heartbeat duration was
not reported.
