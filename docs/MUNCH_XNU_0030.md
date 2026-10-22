# Munch 0030: integrated FT3658U digitizer

0028 reaches the iOS lock screen but has no touch input. This implementation
adds the complete SPI-to-HID path in one build, including supply votes and
reset sequencing. Hardware operation remains to be tested on the phone.

The new MunchDigitizer is an IOKit service with its own workloop and timer.
It starts independently of the root device, reads FT3658U every10ms, and
publishes coherent digitizer collections with normalized coordinates,
contact identity, move/release events and UIKit edge-tip flags. Unchanged
frames do not generate events. Portable Apple IOHIDFamily event/user-client
sources come from the project's upstream0058; the hardware driver and power
client are separate implementations based on Munch primary sources.

## Hardware integration

Reference kernel: LineageOS/android_kernel_xiaomi_sm8250 at
`6b34d24765327d746074c8e53b5ad0d24a51acc7`, particularly focaltech_3658u,
spi-geni-qcom, qcom-geni-se, gcc-kona, pinctrl-kona, rpmh-rsc, cmd-db and
rpmh-regulator. The packaging script checks the actual live FDT bindings.

SE4 at0x990000, CS0, SPI mode0 at4.8MHz; GPIO8..11 on NORTH/qup4, reset33
and interrupt39 on SOUTH. The driver validates GENI SPI firmware, clock
parent and FIFO geometry before transfers. It streams the99-byte command
through FIFO windows, validates status and CRC over all90 response bytes,
and decodes the62-byte touch section into up to ten contacts.

The supply client resolves only ldoc1 and ldoc10 in the reserved firmware
CMD DB. It validates VRM resource addresses and RSC geometry, borrows only
an idle ACTIVE TCS from the live DT's slots2..4, and votes L1C1800mV followed
by L10C3000mV with HPM mode and enable last. Busy slots are untouched.
Uncertain completion quarantines the owned slot without reset/retry.
Touch reset is held low during supply initialization, then released with
a200ms settle. There are no controller firmware flashes, direct PMIC writes,
DMA buffers or interrupts. Existing Android/root partitions are preserved.

`munchtouch=0` disables the service; `munchtouch_power=0` skips its supply
votes for a controlled inherited-power test. Missing GENI firmware or an
unsupported runtime layout stops with a MUNCH TOUCH/POWER diagnostic.

## Packaging and validation

The Munch ADT retains the previously validated exact4GiB RAM aperture.
Upstream's new panic-log carve-out is disabled only for Munch because the
loader rejects a different aperture; generic upstream behavior is retained.
Keep the existing0028 image as a recovery checkpoint.

Frame parsing, actual SPI-read functions, actual RPMh functions and actual
HID consumption passed host checks with address/undefined sanitizers.
Checks cover all90-byte CRC, FIFO streaming, retry/abort/overflow behavior,
rail voltages/order, idle-slot isolation, timeout quarantine, coordinate
endpoints, ten contacts, release, identity and edge gestures. Hardware is
mocked in these tests; a phone result is still required. Patch application,
source equality, live FDT audit, Python/shell syntax and loader preview pass.

Stage last patch98. Output after successful CI:
`shim/out/munch-xnu-0030-touch/testios.img`. No root reinstall is required.
The workflow uses standard `macos-15-intel`: previous ARM-runner attempts
failed before executing steps because no hosted runner was allocated.
CI compilation/artifact and phone tests are pending. User will notify build
completion; do not poll or start duplicate runs.
