#!/bin/bash
# Read-only collection from an already booted Android/recovery; never reboots.
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 ADB_SERIAL (see adb devices -l)" >&2
    exit 2
fi
command -v adb >/dev/null
serial=$1
device=$(adb -s "$serial" shell getprop ro.product.device | tr -d '\r')
if [ "$device" != munch ]; then
    echo "Expected ro.product.device=munch; got '$device'. No data collected." >&2
    exit 1
fi
out="research/munch/$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p "$out"
run() {
    local name=$1
    shift
    if ! adb -s "$serial" "$@" >"$out/$name" 2>"$out/$name.stderr"; then
        echo "Unavailable: $name (see stderr file)" >&2
    fi
}
for prop in ro.product.device ro.product.model ro.board.platform ro.boot.hardware \
    ro.build.fingerprint ro.boot.slot_suffix ro.boot.verifiedbootstate ro.boot.flash.locked; do
    printf '%s=' "$prop" >>"$out/properties.txt"
    adb -s "$serial" shell getprop "$prop" >>"$out/properties.txt"
done
run cpuinfo.txt shell cat /proc/cpuinfo
run iomem.txt shell cat /proc/iomem
run partitions.txt shell cat /proc/partitions
run by-name.txt shell ls -l /dev/block/by-name
run input.txt shell cat /proc/bus/input/devices
run framebuffer.txt shell 'for f in /sys/class/graphics/fb0/{name,virtual_size,stride,bits_per_pixel}; do echo "$f"; cat "$f"; done'
run live.dtb exec-out cat /sys/firmware/fdt
run device-tree.tar exec-out tar -C /sys/firmware/devicetree/base -cf - .
run dmesg.txt shell dmesg
echo "Saved to $out; permission errors are expected without recovery/root."
echo "Contains private device information. Keep this directory out of git."
