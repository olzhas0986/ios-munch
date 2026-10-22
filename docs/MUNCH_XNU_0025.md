# Munch XNU 0025: safe console muting after graphics handoff

The0024 graphics-view test panicked on its first framebuffer swap. Photos
WIN_20261022_11_27_41/49 resolve against the exact0024 kernel as follows:

- PC fffffe00074560bc: switch_to_serial_console+0x1c, STR WZR,[X8].
- FAR fffffe00071775e0: cons_ops_index in protected __DATA_CONST.
- LR fffffe0007a6510c: PE_initialize_console+0x58.
- ESR9600004f: a write permission fault.

The framebuffer's old quiet path called PE_initialize_console(kPEDisableScreen),
which switches the protected late-read-only console selector after startup.
This was an unsafe existing path exposed by the proposed0024 graphics profile.
Do not boot the superseded0024-graphics image again. Normal0024 remains a
screen-diagnostic fallback.

Patch0094 adapts upstream0067's narrow fix without its persistent-log dependency.
The framebuffer sets a mutable Munch flag instead of switching consoles.
The ordinary console output helper returns while muted unless panic_active()
is true. Panic output remains enabled, and cons_ops_index stays protected.
No memory protection or storage bounds are weakened.

The host check executes the actual modified output helper: normal output,
graphics mute, panic bypass and the existing disableConsoleOutput control
all behave as intended. The modified framebuffer source has no call to
PE_initialize_console. Both changed source files accept the patch against
the unchanged baseline. Real graphics handoff still requires hardware testing.

Reuse installed root0020. Temporarily boot the corrected graphics profile:

```bat
copy /Y "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\shim\out\munch-xnu-0025-graphics\testios.img" C:\platform-tools\testios.img
cd /d C:\platform-tools
fastboot boot testios.img
```

Wait two to three minutes and capture the resulting graphics or any panic.
The normal0025 image preserves on-screen diagnostic output. This patch fixes
the identified console write; it does not repair unrelated Apple daemon crashes
or establish full iOS UI startup.

CI [39735617667](https://github.com/olzhas0986/ios-munch/actions/runs/39735617667)
passed for0df35d8a8ab10c946490af5d6769ed2926505cfe.
Graphics image SHA256:66f43665509fda83dd226e793a85d435664a584508dcca9fd78625486734fb6c.
Normal diagnostic image SHA256:4a67e436f8ff23a9e26f57682beb6b3f0d42ba26db1f55aa3a06d68e277f251a.

Compiled-symbol/section checks confirm the new flag in writable __DATA and
cons_ops_index still in read-only __DATA_CONST. The compiled swap contains
no direct call to the unsafe console-switch helpers. Both boot headers,
embedded payloads, root arguments and loader host regression pass. Phone
behavior with0025 has not yet been verified.
