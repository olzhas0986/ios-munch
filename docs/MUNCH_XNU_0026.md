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
No root reinstall or partition changes are needed. Build/artifact validation
and the phone result are pending.
