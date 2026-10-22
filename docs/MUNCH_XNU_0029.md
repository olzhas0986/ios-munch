# Munch 0029: FT3658U touch bring-up

The 0028 phone boots to the iOS lock screen, but has no input driver.
This change connects a portable HID event service to a Munch-specific
GENI SPI FIFO worker. Hardware operation is not yet verified on the phone.

## Sources and scope

Portable HID event/user-client code comes from upstream Sweet patch0058
(Apple IOHIDFamily1915.140.3); Munch service names and native1080x2400
coordinates are retained. Contacts starting near an edge carry the upstream
0071 edge-tip bit needed by UIKit home/unlock gestures. No Sweet Goodix,
I2C, PMIC, button or power driver is enabled.

Hardware references: the local live FDT and LineageOS/android_kernel_xiaomi_sm8250
commit6b34d24765327d746074c8e53b5ad0d24a51acc7, specifically focaltech_3658u,
spi-geni-qcom.c, qcom-geni-se.c, gcc-kona.c and pinctrl-kona.c. The audit in
[danya2271/ios-munch patch0085](https://github.com/danya2271/ios-munch/blob/68d2ede/xnu/patches/0085-munch-focaltech-report-parser.patch)
helpfully highlighted the normal90-byte response. Its repository has a pure
parser, not a proven Munch SPI input driver. This implementation requests the
same99-byte full-duplex transaction as Android and validates CRC over all90
response bytes before decoding the62-byte touch section.

## Hardware behavior

SE4 at0x990000, CS0, SPI mode0 at4.8MHz, chip ID56:52. SPI pins8..11 are
NORTH/qup4; reset33 and interrupt39 are SOUTH. GCC votes/configuration use
SM8250 registers. FIFO polling handles transfers across FIFO windows;
no DMA addresses or interrupts are installed. Reset is kept high without a
reset pulse. Controller writes are SPI read commands, not firmware/config
writes. There are no PMIC/RPMh votes or firmware flashing.

The first test assumes ABL left touch rails and SPI sequencer firmware
available. It verifies the sequencer protocol, idle state, FIFO shape,
clock parent and CRC-valid chip ID, then stops with diagnostics if a
prerequisite is missing. Five bad reports release contacts and stop the
worker. All MMIO polling/transfer/abort loops are bounded. This can expose a
missing firmware/power prerequisite rather than immediately enable touch.
`munchtouch=0` disables the hardware worker. The packaging tool audits live
DT SPI/GPIO bindings before generating an image.

## Validation and next step

Host decoder and actual SPI-read helper checks pass under address/undefined
sanitizers (leak checks disabled because ptrace prevents LeakSanitizer).
Checks cover CRC, all90 payload bytes,99-byte framing, retry/status handling,
ten contacts, coordinate edges, release and malformed reports. Final patches
apply independently; Python/shell syntax and live DT audit pass.

Stage last patch98. CI compile and phone validation pending. Keep0028 as the
working display checkpoint; installed root does not need replacement. After
successful CI, package the normal0029 image and photograph MUNCH TOUCH /
MUNCH HID messages while testing taps and a swipe from the bottom edge.
