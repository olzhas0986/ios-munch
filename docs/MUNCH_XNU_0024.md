# Munch XNU 0024: extended keybag state and optional HFS relocation

Camera Roll photos WIN_20261022_10_01_18 through10_33_25 show repeated
unsupported AKS selectors35,31,10, non-display daemon crash loops and
`hfs_clonefile: cluster_write failed - 34`. The user reports an Apple logo
before these frames. The logo's origin is not established, and no kernel
panic or new MUNCH CRASH report is visible in the supplied images.

The dash in that HFS printf is a separator: error34 is Darwin ERANGE.
The function relocates an existing file's data within its allocation; its
name does not denote the user-facing clonefile syscall. HFS open-time
fragmentation optimization starts after three minutes and discards relocation
failure. These messages do not establish an ordinary UFS write failure, a
full disk, or the cause of the stalled display.

Patch0093 sets the Munch mount's automatic open-time defragmentation size
threshold to zero during bring-up. Ordinary reads/writes and storage bounds
remain active. This avoids optional relocation; it does not implement a
general repair for the observed ERANGE path.

Patch0092 adds upstream-known AKS selector35 using selector17's existing DER
extended-state dictionary, notification-state query103 and assertion consume101.
It does not implement cryptographic key wrapping or fabricate key material.
Unknown operations still fail. The first three errors per selector are printed,
followed by a suppression notice; successful calls retain their eight-note budget.

Host checks execute the actual dispatch and DER helpers with IOKit stand-ins:
17/35 return matching valid eight-field DER dictionaries, descriptor output
matches inband output, a short buffer remains untouched and returns NoSpace,
103 validates its output slot, 101 succeeds, unknown operations fail, and the
per-selector error budget is bounded. Both patches apply to their exact0023
source baseline. Hardware response remains a separate test.

Reuse installed root0020 and temporarily boot:

```bat
copy /Y "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\shim\out\munch-xnu-0024\testios.img" C:\platform-tools\testios.img
cd /d C:\platform-tools
fastboot boot testios.img
```

Capture the final screen, any MUNCH CRASH lines, or a transition to graphics.
Full iOS UI startup and the cause of the previous stall remain unverified.

CI [39729478867](https://github.com/olzhas0986/ios-munch/actions/runs/39729478867)
passed for e3c273a47cccd96a653fdfee6ae590b3ab5c460d.
Boot image SHA256:d2e424598ec362fac1c48d11d5c89b2bc77edec90cecd3b9973f6277fbe8e93c.
Kernel checksum/manifest/ARM64, compiled diagnostic markers, boot header,
embedded payload, memory audit and loader host checks passed. Actual0024
hardware behavior is not yet verified.

## Superseded graphics view

The0024 graphics profile was phone-tested and panicked while writing
protected cons_ops_index. Do not boot it again. Use the corrected profile
in [MUNCH_XNU_0025.md](MUNCH_XNU_0025.md). The normal0024 diagnostic image
remains available; its boot command above does not enable that unsafe path.
