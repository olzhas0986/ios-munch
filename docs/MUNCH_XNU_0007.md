# Munch XNU0007: CPU driver binding and console names

XNU0006 passed SHA-1 initialization but remained at platform expert
registration for five minutes. Its CPU0 ADT compatible list omitted
`qcom,kryo470`, the match string required by the existing generic IOCPU
driver. That prevented CPU driver matching and completion notification.

The CPU compatible list now starts with `qcom,kryo585` and retains the
`qcom,kryo470` driver alias, followed by `qcom,kryo` and `ARM,v8`.
Only CPU0 is exposed, with physical ID zero. This alias selects the
shared single-CPU implementation; it does not change hardware registers.

Patch 0082 changes 28 kernel log/panic string literals from SWEET to MUNCH.
Internal configuration macros, class names and payload format remain
compatible with the existing implementation. The exact selected patch
set is 0001–0027, 0032 and 0082; no UFS/write patches are selected.

Build: https://github.com/olzhas0986/ios-munch/actions/runs/39582602130

CI succeeded. Kernel SHA256:
`cca54c9e4b782f9d50f13044378384dcaeb996e91c207f54a66e040b8c8dbd9a`.
Image: `shim/out/munch-xnu-0007/testios.img`, 16,429,056 bytes, SHA256
`95e6e5b2fd56d931afbda384cdd11a9c5f5050c44fbae1fdf181b20730261021`.
Manifest, CPU binding, binary MUNCH messages, boot roundtrip and loader
host scenarios passed. The legacy upstream workflow is now manual-only.

The expected next milestone is `MUNCH CPU: boot CPU ... registered, SGI1
verified, initialization complete`. Hardware confirmation is pending.
No root RAMDisk or complete iOS environment is supplied yet.

```sh
bash shim/munch/build-xnu.sh research/munch/xnu-run-39582602130/kernel.development.sweet ../live.dtb
```

```bat
copy /Y "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\shim\out\munch-xnu-0007\testios.img" C:\platform-tools\testios.img
cd /d C:\platform-tools
fastboot boot testios.img
```

Capture the full output after temporary boot; do not flash this image.
