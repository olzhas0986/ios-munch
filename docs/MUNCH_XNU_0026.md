# Munch XNU 0026: bounded UI diagnostics

The fixed 0025 graphics image stays on the Apple logo after 20 minutes on
the phone. No new panic has been reported. The UI blocker is not identified.

Patch 0095 adds two best-effort kernel snapshots of SpringBoard and
backboardd, approximately 60 and 120 seconds after UFS initialization.
Each snapshot prints the PID, shared-cache slide, main Mach-O header and
up to four thread register sets with up to eight frame-pointer entries.
Targets keep running; stacks are diagnostic samples, not atomic snapshots.
Thread references are retained and the task lock is released before user
memory reads. The sampler exits after the second snapshot. The boot argument
`munchsample=-` disables it.

Crash reports now cover the first three exits per boot of analyticsd,
installcoord* and mobileactivat*, alongside the existing display processes
and configd. Corpse-limit messages stop after twelve notes and one suppression
notice; corpse handling is unchanged.

Use the normal console profile for this test. It retains the 0025 console
panic fix, the existing installed root and bounded iosroot storage access.
No root reinstall or partition changes are needed.

CI run 39742369848 succeeded for source
`d0ff73bf638aad026080c03f8beb7f0b695d3525`; kernel artifact 12410322719.
Kernel SHA-256:
`74954ee6ff81df2ced5f7775f145db6334e47471ef63a237572f079757d57a17`.

Image: `shim/out/munch-xnu-0026/testios.img` (125628416 bytes).
SHA-256: `d9cad98fcdee8a8fb2886cfde1c0cf721b20825291d8ac280dd6f4b61f510d29`.

Manifest and source hashes, compiled diagnostic markers, safe console layout,
boot v3 header, embedded payload, physical-root arguments and ADT mapping
verified. Loader host harness passed five vendor prefixes and rejected nine
malformed inputs. The initial CI failed on a missing BSD-visible declaration
of the Mach-private thread termination entry; the published source fixes it.

Temporary boot from Windows:

```bat
fastboot boot "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\shim\out\munch-xnu-0026\testios.img"
```

Photograph `MUNCH SMP` and `MUNCH CRASH` output after approximately one and
two minutes. Allow three minutes for this test; include the `matched` line
if neither UI process is found. The 0026 phone result is pending.
