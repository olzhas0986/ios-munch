# Munch XNU 0023: root file exchange compatibility and readable logs

The photos5391209827058522788..2801 show the Sandbox policy receiving calls
and Apple daemons continuing startup. They do not show a kernel panic or a
MUNCH CRASH report. The user manually rebooted while messages were scrolling;
this is not evidence of a kernel hang.

Photo2790 shows usermanagerd failing to save persona.kb: atomic file swapping
returns ENOTSUP (45). Patch0090 adapts upstream0052's compatibility path:
after VNOP_RENAMEX returns ENOTSUP for exactly VFS_RENAME_SWAP, two regular
files on the same mounted root volume can use VNOP_EXCHANGE. This supports
the single-volume Foundation temporary-file replacement path; it is not a
complete implementation of arbitrary rename-swap semantics. Existing access
checks remain active, and exchange errors propagate. The first four fallback
results appear as `MUNCH HFS: root file exchange fallback result N`.

Patch0091 bounds routine success messages: four iOS-spawn messages per path,
four DYLD unnest console notes, eight successful AKS calls. It changes logging
only. Spawn admission, VM operations and AKS return values remain unchanged.
AKS errors and existing bounded MUNCH CRASH reports remain enabled. Unsupported
AKS selector103, visible in photo2800, is not implemented by this change.

Patch application to the exact baseline source passes. A host check executes
the fallback block with stubbed vnode operations: other errors/flags, missing
targets, nonregular files, different mounts and nonroot mounts do not trigger
an exchange; an exchange backend failure is returned to the caller. Actual
persona-file persistence still requires a phone boot test.

Reuse installed root package0020. Temporary boot only:

```bat
copy /Y "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\shim\out\munch-xnu-0023\testios.img" C:\platform-tools\testios.img
cd /d C:\platform-tools
fastboot boot testios.img
```

Capture the final screen after the initial startup burst, especially root
exchange results, MUNCH CRASH/exit reasons and backboardd/SpringBoard stderr.
Full iOS UI startup remains unverified.

CI [39722455160](https://github.com/olzhas0986/ios-munch/actions/runs/39722455160)
passed for55d4c61694248135b066ec5cfe8e28a649a31f88.
Boot image SHA256:4efc231f6ecc83d4b204f802bc3b01cd51f1531cf2c88f0a17b5b78275d82140.
The compiled fallback marker and log-budget counter symbols, boot header,
embedded payload, memory audit and loader host regression passed. Actual
phone behavior with0023 remains unverified.
