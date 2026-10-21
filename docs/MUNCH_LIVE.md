# Rooted Android evidence — 2026-10-21

The user copied files with root from Android, not TWRP. Inputs remain in the
parent workspace and must not be committed.

`live.dtb` is valid FDT v17, 810920 bytes. It decompiled to ignored
`research/munch/live/live.dts`: model xiaomi munch, msm-id `<0x164 0x20001>`,
board-id `<0x32 0>`.

## Findings

- DDR banks are `[0x80000000, 0xbcc00000)` and
  `[0xc0000000, 0x200000000)`. These are not free-memory declarations;
  reserved-memory and protected carve-outs must be excluded separately.
- `/proc/iomem` contains real addresses and reservations above 4 GiB.
  Sweet's upper-bank size cannot be reused.
- cont_splash reserves `0x9c000000 + 0x2300000`. Reservation alone does not
  establish scanout address/format; subsequent diagnostics showed visible
  writes using 1080×2400, 32-bit pixels, stride4320.
- Bootargs select `qcom,mdss_dsi_l11r_38_08_0a_dsc_cmd`, an OLED DSC
  command-mode panel. No explicit DSI trigger was needed in the diagnostics;
  continuous updates under XNU are not yet established.
- FocalTech touch uses active GENI SPI SE4 at `0x990000`, chip-select0,
  max6MHz, resetGPIO33 and IRQGPIO39. Input lists `fts_ts`.
- Timer: 19.2MHz, virtualINTID27 and physicalINTID30, later hardware verified.
- Current bootargs use DTB0/DTBO0; stock munch is overlay21. The custom kernel
  ZIP explains the difference: it contains a single munch overlay.
  Slot numbers and private identifiers are deliberately omitted here.

## Input quality

`dt.tar` is an additional tree archive inspected without extraction. The
small device-tree.tar was corrupt/truncated and was removed during approved
cleanup; valid live.dtb suffices. dmesg starts around uptime26962s and lacks
early panel/framebuffer messages, so it is not a full startup log.

The custom kernel disables debugfs and DRM fbdev emulation. Do not repeatedly
request absent fb0/debugfs paths. See [custom kernel analysis](MUNCH_CUSTOM.md).
