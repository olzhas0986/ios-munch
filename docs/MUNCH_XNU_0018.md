# Munch XNU0018: bounded read-only iosroot access

Android boots after the16GiB dual-boot split and Data recreation. This
kernel connects XNU to the separate iosroot partition without media writes.
It reuses the UFS controller left running by ABL at0x1d84000, verified
against the live Munch device tree. It does not initialize clocks or PHY.

Patch0084 derives the portable read-only portions of upstream0028 and the
64-bit DMA guard from0034. It uses a separate munch_ufs.c and /munch-ufs
ADT node. Only TEST UNIT READY, READ CAPACITY(10) and READ(10) SCSI commands
are allowed. The BSD write interfaces return EROFS. Controller register
writes configure DMA/completion polling; they are not media writes.

Before exposing the block device, the driver validates LUN0 capacity
30650368 blocks of4096 bytes, primary/backup GPT header and array CRCs,
matching disk identity and the fixed iosroot entry35: first26455808,
count4194304 blocks. Other partition names and different bounds fail closed.
The inherited DMA allocation may be above4GiB, so CAP_64AS is required.

The boot arguments select rd=ufsroot0 ufsroot=iosroot. iosroot has not yet
been formatted or populated: this first persistent-root attempt should
identify the partition and then fail to mount the still-empty filesystem.
That mount failure is expected; UFS initialization errors are not success.
The image does not contain or launch the complete system interface yet.
Known-good RAM-root graphics image0017 remains available.

Host tests compile the actual GPT parsing function with mocked block reads:
the prepared partition is accepted; userdata and six corrupted inputs are
rejected. Staging, live MMIO/ADT checks and repository validation pass.
CI39629216316 succeeded. Kernel SHA256:
`2cfecc2f54c6ed35864d6b93a8154a3a27ec2634780284bc3c237fdfafb3b38d`.
Image shim/out/munch-xnu-0018/testios.img,125554688bytes,SHA256
`e2579ef1db9aa75bb43077beb4e739b2ecc42fb18363aa9ffc6936635518bea1`.
Boot-v3 roundtrip and loader host segment/BSS/ADT/boot-args checks pass for
five prefixes; eight malformed inputs are rejected before writes/jump.
The previous104MiB RAM root remains packaged but rd=ufsroot0 selects UFS.
No physical UFS result yet. Expect MUNCH UFS iosroot/LUN0/16384MiB read-only
before the empty-volume mount error; capture a photo of any error.

## Full root preparation

The official20H392 IPSW OS and SystemOS members are being fetched by ranges.
Original prefixes and resumed suffixes are kept separately until their full
sizes and ZIP CRCs can be verified. A partial download is not a usable DMG.

The APFS exporter can read UDIF/GPT-wrapped and raw APFS without FUSE. It
exports regular-file contents and a JSONL manifest of inode, type, owner,
group, mode, flags and link targets. It deliberately records symlinks and
hardlinks without creating host links, preventing traversal outside the
output directory. It is an intermediate export, not a bootable HFS image;
attributes/ACLs beyond the recorded fields are not exported. A future
filesystem importer must handle decompressed-file flags appropriately.

Build: tools/build-munch-apfs-reader.py SOURCE /tmp/munch-apfs-export --export.
The restore-image test exported1332 entries; launchd/xpcproxy/cat/dyld match
the previously verified Apple userland byte for byte.
