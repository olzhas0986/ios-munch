# RE404 custom kernel ZIP analysis

Input: `RE404-POCO_F4-261010-1555 (1).zip`.
SHA256: `55c08c60030072f9e58e392b57d3934690f8c6b5dfc4204daab548f60fe97db6`.
The installer and bundled programs were not executed. Selected extracted
results/config remain in ignored `research/munch/custom/`; the original ZIP
is retained, while disposable binary copies were removed during cleanup.

## Contents

- MUNCH-Image: raw ARM64 Linux Image, 29,036,568 bytes.
- Embedded version: Linux4.19.404R, Project113, NeutronClang/LLD24.0.0,
  built2026-10-10. This identifies the ZIP binary, not a separate uname check.
- MUNCH-dtb: one kona-v2.1 base DTB.
- MUNCH-dtbo.img: one overlay, index0, xiaomi munch, board-id `<0x32 0>`.
  The index agrees with live bootargs.
- dtc decompiled both trees and fdtoverlay produced merged.dtb.
  ABL adds RAM/bootargs and other properties, so raw equality is not expected.
- IKCFG_ST yielded the gzip IKCONFIG saved as kernel.config.

## Missing framebuffer/debug paths

```text
# CONFIG_DEBUG_FS is not set
# CONFIG_DRM_FBDEV_EMULATION is not set
# CONFIG_FB_MSM is not set
# CONFIG_FB_SIMPLE is not set
```

Mounting debugfs cannot restore a compiled-out feature. A working display
need not expose fb0 when DRM fbdev emulation is disabled; CONFIG_FB=y alone
does not create a usable framebuffer device.

## Installer behavior

This is AnyKernel3, not a complete boot.img backup. anykernel.sh reuses
boot/vendor_boot, replaces the kernel/DTB/DTBO and adds e404_args. On A/B
munch it also processes vendor_boot. Display-driver source is not included.
Android scanout does not prove ABL leaves an identical configuration; the
separate splash test provided the first bare-metal display evidence.
