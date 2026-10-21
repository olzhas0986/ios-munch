# Munch dual boot preparation

The user requests keeping Android and reserving16 GiB for iOS. This
supersedes the earlier plan to overwrite userdata. No disk geometry has
been collected for this munch yet. Sweet partition numbers in the upstream
notes are not evidence for munch and must never be used as write targets.

Current milestone: prepare an inventory using tools/munch-storage-report.sh
from root TWRP ADB on Windows. The script reads block geometry, partition
aliases, filesystem signatures, existing mounts and recovery fstab. It does
not mount, format, resize or write a partition. Its output is not a backup.
The script itself may be pushed to /tmp in recovery. Reports contain private
storage identifiers and must stay outside git.

The stock image collection lacks GPT, current userdata and encryption
metadata. It cannot restore the current Android installation's user data.
Before any partition edit, collect and verify backups to a PC, including
personal files from internal storage, supported recovery application-data
backup, actual GPT copies for relevant LUNs and current boot/recovery and
encryption metadata as appropriate for this device. A TWRP Data backup must
not be assumed to include /data/media. Restoring encrypted application data
after reformatting is not guaranteed; establish a recovery strategy first.
Raw userdata is a rollback artifact for the original geometry, not an image
to write into a smaller partition. Do not promise it survives key deletion.

Next, inspect real geometry and filesystem type, determine whether the data
filesystem must be recreated, and calculate an aligned iosroot of exactly
17179869184 bytes. Leave GPT backup structures intact. Keep bootloaders,
modem, persist, recovery and Android system partitions intact. Do not derive
write commands until backup verification and geometry checks are complete.

Initial boot selection can retain normal Android boot and use temporary
fastboot boot for the iOS image. A separate root partition still requires
Munch UFS driver integration and verification; current XNU0017 uses a RAM
root and does not establish working persistent storage. A boot menu is later
work. Partition changes need explicit confirmation of the concrete plan.

## Latest user decision

The user explicitly waives the userdata backup because Android was installed
 today and authorizes proceeding with data loss. Do not require a large
backup or repeat the storage-space question. The backup tool is optional.
Read and validate actual GPT bytes first; preserve Android system and other
protected partitions. No GPT edits or formatting have occurred yet.

## Validated on-device GPT and prepared split

Both captured GPT headers and arrays pass CRC checks and match. The capture
files have an appended dd statistics trailer, recognized separately from
exactly1MiB of binary data. The disk has30650368 native4096-byte blocks.

| Partition | Start LBA | End LBA | Result |
| --- | ---: | ---: | --- |
| userdata34 | 2949120 | 26455807 | approximately89.67 GiB |
| iosroot35 | 26455808 | 30650111 | exactly16 GiB |

The last251 usable blocks remain free for alignment. All first33 partitions
and userdata's start, type, GUID and attributes are preserved. No protective
MBR, bootloader, system or other-LUN writes are part of this plan.

Generate offline with tools/munch-plan-gpt.py HEAD TAIL OUTPUT. The ignored
research/munch/dualboot-16g directory contains original/updated GPT regions
and a guarded apply.sh. It rejects mounted data/metadata, wrong hardware,
wrong geometry, changed source GPT and wrong input file hashes. Writes use
backup entries/header first, then primary entries/header, then verify all
four regions. This is not a filesystem shrink: recreate Data using TWRP
only after rebooting directly into recovery and verifying new sizes.
Do not boot Android or allow mounting the old oversized F2FS after the split.
If any application check fails, stay in recovery and inspect before retrying.
No actual disk write has been observed yet.

## GPT application reported

The user supplied successful application output: all four GPT regions were
written and readback hashes verified, followed by the chained recovery
reboot command. TWRP still decrypts Data. This alone does not verify that
F2FS fits the reduced partition; encryption metadata and the filesystem
were not resized by this GPT-only operation. Post-reboot kernel partition
sizes and mount state remain to be checked before formatting Data.

Post-reboot blockdev results match exactly: userdata96283394048 bytes,
iosroot17179869184 bytes. The user unmounted /sdcard and /data with no
reported error. Next: recreate Data using TWRP Format Data and inspect its
log and capacity after rebooting recovery. No formatting result yet.

## Installation transport preference

The user requests installing the root filesystem on the phone and has a
16GB USB flash drive available. Prepare a file archive plus a device-side
installer, transported through USB OTG, targeting internal iosroot. This
is separate from booting XNU off USB, which is not implemented here.
Account for actual USB free space and FAT32's per-file limit using archive
chunks smaller than4GiB. Do not format the USB drive without authorization.
The saved Android configs disable HFS+ but enable FUSE; inspect actual
recovery support before choosing a device-side filesystem writer.
