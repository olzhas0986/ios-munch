# iOS 16 on POCO F4 (munch)

Based on https://github.com/dipa-studio/ios-sweet at `4c7cc91`.
The munch hardware diagnostics pass; iOS has not booted on this device yet.
Historical sweet device state and destructive permissions in NOTES.md apply
only to the original owner's phone.

## Confirmed progress

- Stock boot/vendor_boot v3 and DTBO parsed: [stock evidence](docs/MUNCH_STOCK.md).
- Rooted Android live DT and memory map inspected: [live evidence](docs/MUNCH_LIVE.md).
- CPU0 splash output and 16K MMU verified on the phone.
- Virtual/physical timers each delivered 30 IRQs; self-SGI delivered 10.
- CPU1–CPU7 entered C and powered off through PSCI with the held-core test.
- The first early ARM64 XNU kernel built in [GitHub Actions](docs/MUNCH_ACTIONS.md).

## Device data and collection

The user reports an unlocked bootloader, TWRP and a full stock firmware dump.
That does not establish a backup of personal data or device-specific calibration.
Keep dumps in ignored `backup/`, `dtb/` or `research/munch/`. Use the system
`unpack_bootimg` for v3/v4 images; `tools/unpack_bootv2.py` only supports v0–v2.

For read-only collection from an already booted Android/recovery:

```sh
adb devices -l
bash tools/munch-collect.sh SERIAL
```

The script selects the explicit serial, checks `munch`, and does not invoke
root, reboot or partition writes. Missing permissions are recorded. Valid
rooted Android files have already been supplied; WSL ADB is unavailable,
while Windows ADB works. Do not publish raw device trees containing identifiers.

## Next steps

Prepare a CPU0-only Apple DT and an isolated boot-v3 XNU loader, then observe
early XNU before adding RAMDisk/userland or hardware drivers. Port UFS, power,
display and input separately. See [the XNU plan](docs/MUNCH_XNU_NEXT.md).

Upstream hardware assumptions are in `shim/console.h`, `shim/mmu.h`,
`shim/shim.c`, `shim/ufs.c`, `shim/build.sh`, `tools/mkadt.py`,
`tools/mkpayload.py` and `xnu/patches/`. A matching screen resolution does not
prove matching scanout behavior. The full sweet kernel supports UFS writes
and persistent logging; temporary fastboot boot alone does not prevent writes.
Any userdata erase requires separate approval and a verified backup.

All boot images must be named **testios.img**, with versions kept in directory
names and screen text. All new GitHub-facing content must be in English.
