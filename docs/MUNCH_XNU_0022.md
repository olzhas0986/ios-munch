# Munch XNU 0022: Sandbox service calls and crash diagnostics

The six photos5391209827058522778..2783 show launchd starting Apple
SpringBoard/backboardd from root package0020. Mach service lookups fail with
`error = 159: Sandbox restriction`; SpringBoard, backboardd, configd and
mediaserverd crash and restart. No working UI is established by these photos.

The kernel has no registered policy named `Sandbox`, so libsystem_sandbox's
MAC syscalls return ENOPOLICY. Independent patch0088 adapts the existing
upstream0050 development policy: profile/check operations succeed, while
container-path and extension operations requiring output data return ENOENT.
It does not fabricate paths or extension tokens. AMFI registration remains
unchanged; the additional policy registers before user processes execute.

Patch0089 provides bounded console diagnostics for the first three crashes
of each SpringBoard/backboardd/configd process name: signal, exception code,
registers, ten frame-pointer frames, shared-cache slide, main image header
and exit-reason text. It also copies SpringBoard/backboardd stdout/stderr
writes to /dev/null onto the console. `munchnull=-` disables that copy.
The boot arguments omit `launchd_log_serial=1` to reduce lifecycle chatter.

Both patches apply to the exact0021 CI sources. Host contract checks cover
Sandbox success/output-error cases and independent per-process crash limits.
The stage allowlist adds only0088/0089; no Sweet hardware drivers are added.
The root filesystem and dedicated bounded iosroot storage driver are reused.

```bat
copy /Y "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\shim\out\munch-xnu-0022\testios.img" C:\platform-tools\testios.img
cd /d C:\platform-tools
fastboot boot testios.img
```

Do not reinstall root package0020. Capture new errors, especially lines
beginning `MUNCH CRASH`, `reason`, or `|backboardd|` / `|SpringBoard|`.
The Sandbox fix does not establish that all GUI dependencies are implemented.

CI [39720224922](https://github.com/olzhas0986/ios-munch/actions/runs/39720224922)
passed for c7b4d7b06e103e662ff7bf53c79c36dad8784352.
Boot image SHA256:59aef7271925d66b65d4edfdd5ff4097590fd8d384597da34c8d5de6de164147.
Compiled-kernel diagnostic markers, boot header/payload, memory audit and
loader host regression passed. Hardware behavior with0022 is unverified.
