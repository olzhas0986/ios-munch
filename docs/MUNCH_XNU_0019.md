# Munch XNU0019: writable dedicated root and full Apple userspace

The user confirmed that XNU0018 finds iosroot16GiB read-only; Android boots
from its recreated smaller Data partition, and TWRP reads the NTFS OTG drive.
Actual TWRP4.19.404R has FUSE but no HFS+ driver or formatter. Installation
therefore uses a prepared compressed HFS image on USB, written by a native
static ARM64 program running inside recovery, rather than PC flashing.

Patch0085 adapts upstream0030 with fixed iosroot bounds checked twice: at
the write API and immediately before SCSI DMA submission. No write is
allowed until readiness and ufsrw=1, and both GPT copies/CRCs, capacity and
partition35 extent must match the verified split. The GPT remains read-only.
Other opcodes are rejected; the synchronize-cache command performs no
partition-table edits. Host tests exercise the actual write/CDB guard code.

Patch0086 independently integrates upstream29/33/35/36/37/38/39/40/45 and
the rootrw mount flag. It supplies platform-signature/entitlement handling,
SHA384/512, bindfs configuration, development KeyStore/watchdog services,
and disables default coredumps. These are development substitutes for
Apple hardware services. Sweet input/USB/MMIO drivers remain excluded.
Runtime labels use MUNCH. No dirty nonjournaled root bypass is added.

The ADT now exposes audited RAM4..8GiB for the system shared cache. Fixed
and dynamic live-DT reservations do not overlap. Only CPU0 is enabled.
Static, non-placeholder /product properties come from the same official
D22AP IPSW; CPU, timer, memory, framebuffer and UFS remain Munch-specific.

The archive builder combines OS, SystemOS and AppOS exports and recreates
cryptex/cache links. Metadata is stored in PAX tar, including numeric
owners and hardlinks. Restore directories/preferences and diagnostic
launchd adjustments are added. The isolated Linux VM imports the archive
into a16GiB HFS image using the native HFS+ driver, checks selected file
hashes/metadata and unmounts before packaging. Host mounts are not needed.
Only local image files are visible as virtual disks to this VM.

The USB packer checks the VM result, critical file hashes, clean HFS state
and matching primary/alternate volume headers. It emits gzip parts at most
2GiB, an installer script, SHA256SUMS and a manifest. The installer verifies
all parts before writing, accepts only the known iosroot block device and
geometry, checks the HFS image header/length and input SHA256, then reads
back the entire installed16GiB and verifies SHA256. Interrupted installation
leaves iosroot incomplete; the program cannot target Android userdata.

CI39645652041 succeeded froma41cba6b. The root image and USB installer package are verified and ready. No full-root phone boot result yet.
Preserve known-good0017 graphics and0018 read-only storage images.

Kernel SHA256:87b77578d4fbdf0e7dee0609667973723e4fcc56015549ecc53d6e0666016e4e.
Boot image after loader profile correction:
`b025ed90a42473ed4d3bc5db54c5941f4b500bd3c8b9a9a701f9b987318f9faa`.
The local loader accepts exactly4GiB at physical4GiB; the earlier1GiB
profile would have rejected the new payload. Five prefix/alignment cases,
nine malformed inputs including the stale memory profile, and boot-v3
roundtrip pass. Root volume finalization and validation are complete as detailed below.

## Verified release artifacts

USB folder: research/munch/usb-install-0019 (approximately6.13GB including
boot image). Three gzip parts total5995844478 bytes; each is at most2GiB.
HFS raw image17179869184 bytes,SHA256:
`0755ecf46d7227dd1e5b7937d5b28bb92f40fe5498c64eb634a74ac63399f7bb`.
Boot image125628416 bytes,SHA256:
`b025ed90a42473ed4d3bc5db54c5941f4b500bd3c8b9a9a701f9b987318f9faa`.

Native fsck_hfs verifies the case-sensitive journaled HFS filesystem. The
finalizer refreshes the alternate volume header from the verified clean
primary and checks again. All package SHA256SUMS pass. Rejoining/decompressing
the three parts produces the entire16GiB image; the actual installer's C
SHA256 matches the independently generated Python digest, including the
large-input length. Kernel loader and write-boundary tests also pass.

The archive builder skips cryptex aliases below existing framework symlinks
and rejects any remaining entries below symlink ancestors. A synthetic
regression checks that layout plus numeric ownership and cache hardlinks.
The current image had its redundant aliases removed and correct symlinks
restored before final clean-unmount/checking. Its322529 intended archive
entries contain11524578512 unique data bytes. Three critical hashes match.

Install-Munch-iOS.zip is a small TWRP launcher, not a self-contained root
archive. Keep it in the complete USB folder. It pins SHA256SUMS and install.sh,
streams progress to TWRP and propagates installation failure. Mock updater
success, failed child and tampered script/checksum cases pass. Android boot
partitions, userdata and GPT are not write targets. No full-root phone
installation/boot has been reported yet.
