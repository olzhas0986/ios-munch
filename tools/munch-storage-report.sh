#!/system/bin/sh
# Read-only storage inventory. Run as root inside TWRP; output stays on stdout.
set -u
if [ "$(id -u)" != 0 ]; then
    echo 'ERROR: run this script inside TWRP with root ADB.' >&2
    exit 1
fi
device=$(getprop ro.product.device)
vendor_device=$(getprop ro.product.vendor.device)
if [ "$device" != munch ] && [ "$vendor_device" != munch ]; then
    echo "ERROR: expected munch, found '$device' / '$vendor_device'." >&2
    exit 1
fi
echo 'MUNCH STORAGE REPORT v1 — inventory only, not a backup'
echo '=== Identity and encryption ==='
for prop in ro.product.device ro.product.vendor.device ro.boot.slot_suffix ro.crypto.state ro.crypto.type ro.twrp.version; do
    echo "$prop=$(getprop "$prop")"
done
echo '=== Partition aliases ==='
ls -l /dev/block/by-name /dev/block/bootdevice/by-name 2>&1
echo '=== Kernel partition list ==='
cat /proc/partitions
echo '=== UFS geometry ==='
# sysfs size/start always use 512-byte units, independently of logical block size.
for node in /sys/class/block/sd*; do
    [ -e "$node" ] || continue
    echo "BLOCK ${node##*/}"
    for field in size start partition queue/logical_block_size queue/physical_block_size; do
        if [ -r "$node/$field" ]; then
            echo "$field=$(cat "$node/$field")"
        fi
    done
    if [ -r "$node/partition" ]; then
        continue
    fi
    block="/dev/block/${node##*/}"
    if command -v sgdisk >/dev/null 2>&1; then
        sgdisk --print "$block" 2>&1
    elif command -v fdisk >/dev/null 2>&1; then
        fdisk -l "$block" 2>&1
    fi
done
echo '=== Filesystem signatures ==='
if command -v blkid >/dev/null 2>&1; then
    blkid 2>&1
fi
echo '=== Existing mounts (no mounts requested) ==='
cat /proc/mounts
echo '=== Space on currently mounted filesystems ==='
df -k /data /metadata /sdcard 2>&1
echo '=== Recovery filesystem configuration ==='
for file in /etc/recovery.fstab /etc/twrp.fstab /vendor/etc/fstab.* /odm/etc/fstab.*; do
    [ -f "$file" ] || continue
    echo "FILE $file"
    cat "$file"
done
echo '=== Available inspection/backup tools ==='
for tool in sgdisk fdisk blockdev dd tar sha256sum resize2fs fsck.f2fs dump.f2fs; do
    command -v "$tool" 2>/dev/null || true
done
echo '=== END MUNCH STORAGE REPORT ==='
