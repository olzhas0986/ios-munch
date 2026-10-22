# Munch 0027: inspect the profile service wait

The 0026 phone snapshots show SpringBoard waiting for a synchronous XPC
reply. Earlier frames include MCProfileConnection migration/check-in calls.
The actual root contains the mobile, adaptive launchd job for profiled and
its private/public managedconfiguration Mach services. This is a lead;
the destination of the later XPC wait and the root cause remain unconfirmed.

This image reuses the verified 0026 kernel from CI 39742369848 and installed
root. No kernel rebuild or root reinstall is needed. Package with:

```sh
bash shim/munch/build-xnu.sh research/munch/xnu-run-39742369848/kernel.development.sweet ../live.dtb shim/out/munch-init-0017/root.hfs --profiles
```

The new arguments select SpringBoard/profiled for the existing two snapshots
and tee profiled stdout/stderr from /dev/null to the screen. This does not
capture os_log, add profiled to the crash allowlist, force it to launch or
change service behavior. The normal console remains enabled.

Output: `shim/out/munch-xnu-0027-profiled/testios.img`, 125628416 bytes.
SHA-256: `2f00a101895729fdb2496e3a2c99ceff96068839ad2830c930cf39c37487a077`.
All eleven kernel/RAMdisk segments match 0026 exactly. Manifest/source hashes,
live FDT, boot header, embedded payload, root arguments and ADT mapping passed;
loader harness passed five prefixes and rejected nine malformed inputs.

Photograph MUNCH SMP profiled/SpringBoard and any |profiled| output after
approximately one and two minutes. Include matched counts. A missing process
in a snapshot does not establish why it is absent. Phone result pending.
