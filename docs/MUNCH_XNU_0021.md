# Munch XNU 0021: bounded HFS link diagnostics

The first boot of installed root package 0020 floods the display with
`hfs: set hardlink bit on vol=MunchIOS` messages, hiding later errors.
Linux-created hard links lack an Apple catalog flag; XNU repairs it during
lookup. These messages alone do not establish a filesystem failure.

Patch 0087 places a shared atomic budget around the three HFS link-repair
printf calls. It leaves the flag and link-count repairs active and emits at
most nine notes during an ordinary boot. Other HFS diagnostics remain active.
The generic XNU configuration retains its internal SWEET macro; the new
helper and comments identify Munch.

The pinned Apple HFS source accepts the patch. A host check using XNU's
original-value OSIncrementAtomic semantics confirms nine notes across
10,000 calls. The device image requires the independent Munch allowlist
through patch 0087 and reuses the existing bounded iosroot write driver.

The output is shim/out/munch-xnu-0021/testios.img. It boots the already
installed root package 0020; do not reinstall the root filesystem or change
Android partitions. Temporary fastboot boot is sufficient.

```bat
copy /Y "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\shim\out\munch-xnu-0021\testios.img" C:\platform-tools\testios.img
cd /d C:\platform-tools
fastboot boot testios.img
```

Capture the next visible errors or panic. This change improves diagnostics;
full iOS startup and UI remain unverified.

CI run [39710590206](https://github.com/olzhas0986/ios-munch/actions/runs/39710590206)
passed for source a4025346c9421314aebf0b5d49e48ba282d690a1.
Boot image SHA256: da9b45ff18d67144c48436b0de79ca1447d098ac1909d4f01d255a6a0b31fdac.
The boot header, embedded payload and loader host regression passed.
Hardware behavior with image0021 is not yet verified.
