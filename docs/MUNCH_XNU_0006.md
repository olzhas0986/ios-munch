# Munch XNU0006: portable SHA-1 for platform UUID

XNU0005 reached scheduler and kernel-debugger initialization on the phone,
then panicked at PC `0xfffffe000797a250` (`SHA1Init+0x34`),
LR `0xfffffe00079e4748` (`IOPlatformExpertDevice::generatePlatformUUID+0x10c`),
ESR `0x96000005`, FAR `0x28`. SHA1Init used the absent corecrypto dispatch table.

The selected patch set is exactly 0001–0027 plus 0032. The latter supplies
BearSSL SHA-1 behind the existing SHA1Init/Update/Final API. The pinned
0020 source provider already supplies SHA-1 and the big-endian codecs.
Patches 0028–0031 remain excluded, including UFS and write support.

The SHA-1 wrapper passed 65 comparisons against Python hashlib, including
empty input, block boundaries, incremental updates and a million-byte input.
Patch 0032 applies cleanly after 0027; staging verifies the exact allowlist.

Build run: https://github.com/olzhas0986/ios-munch/actions/runs/39579078956

CI completed successfully. Kernel artifact 12335717511 matched SHA256SUMS:
`90399777a86c0835c1d526d791134193709bddc58983c9c24eb704a890954e06`.

Boot image: `shim/out/munch-xnu-0006/testios.img`, 16,429,056 bytes, SHA256
`2179a30d7d1afbf620913cb4a4bb74aae4623e943c926636efeaf1466cdcb8ed`.
Boot-v3 roundtrip and the loader host harness passed with the new payload.

The loader, CPU0-only ADT, 4..5 GiB RAM audit and temporary boot procedure
are described in MUNCH_XNU_0005.md. No root RAMDisk is supplied yet.
The new shim screen identifies itself as XNU 0006. Physical testing is pending.

```sh
bash shim/munch/build-xnu.sh research/munch/xnu-run-39579078956/kernel.development.sweet ../live.dtb
```

```bat
copy /Y "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\shim\out\munch-xnu-0006\testios.img" C:\platform-tools\testios.img
cd /d C:\platform-tools
fastboot boot testios.img
```

Capture the full screen after temporary boot. Do not flash the image.
