# Stock munch image analysis — 2026-10-21

Input: `../extracted_20261021_115709/`, read without modification. The user
reports an unlocked bootloader and TWRP. A firmware dump is not proof of a
personal-data or persist/modemst backup.

## Image evidence

| Property | Observed value |
| --- | --- |
| boot header | v3; kernel 50,628,624 bytes; ramdisk 18,670,718 bytes |
| OS metadata | Android 13.0.0; patch 2025-04 |
| vendor_boot | v3; page size 4096 |
| vendor ramdisk / DTB | 2347 / 1,613,352 bytes |
| DTB bundle | kona v2.1/v2/v1 plus a separate RTIC tree |
| DTBO | 27 overlays; index 21 is xiaomi munch, board-id `<0x32 0>` |
| GIC in base-00 | GICv3; GICD `0x17a00000`; GICR `0x17a60000`; stride `0x20000` |
| Timer in base-00 | 19.2 MHz; virtual PPI 11, INTID 27 |
| PSCI | `arm,psci-1.0`, SMC |
| CPU reg | `0`, `0x100`, …, `0x700` |
| UFS host | `0x01d84000`, size `0x3000` |
| Candidate splash | `0x9c000000`, size `0x2300000` |
| Touch overlay | FocalTech SPI, max 6 MHz; reset GPIO33; IRQ GPIO39 |

DT descriptions are not physical measurements. Sweet uses virtual timer
INTID19 and Goodix I2C touch, so its configuration cannot be copied unchanged.
Shared GIC/UFS addresses do not establish driver compatibility.

Overlay21 applied to base-00 with fdtoverlay and decompiled with dtc. This is
an analysis candidate, not a verified ABL selection. Its memory reg is zero;
ABL supplies actual RAM. Multiple panel definitions require live selection data.

## Extraction and provenance

System unpack_bootimg extracted boot/vendor_boot. All 31 original trees
successfully decompiled. Results were placed under ignored
`research/munch/stock/`; selected base trees, overlay21 and the candidate
remain after cleanup. Unused overlays and ramdisk copies can be regenerated.

```text
b50d41c8a52d869e4ef96c6601279ad72ce7c6b0f341d8c155d9f8c436111bdd  boot.img
55a9f6c6fd4b77b0a05f05f4493d0ef0a4b33eae781cb743fcb0578af5511717  vendor_boot.img
666417fdf89b669791014958179294a214796163af6af0c27a9ed43ecb73f15a  dtbo.img
```

IKCONFIG was extracted to `research/munch/stock/kernel.config`. The kernel is
`4.19.157-perf-g1f9b135a6fcc`, built 2026-04-17. DEBUG_FS and DRM FBDEV
emulation are disabled. Binary strings identify SDE command-mode encoder,
continuous splash and autorefresh functions, including
`techpack/display/msm/sde/sde_encoder_phys_cmd.c`. These strings are not
recovered driver source or a verified MMIO programming sequence.

[Live DT](MUNCH_LIVE.md) and [hardware diagnostics](MUNCH_DIAG_0004.md)
subsequently confirmed the basic platform. Original images remain intact.
