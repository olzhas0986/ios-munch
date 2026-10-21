#!/bin/bash
# Produces only a temporary boot experiment; never invokes adb/fastboot.
set -euo pipefail
cd "$(dirname "$0")/.."
test_version=${1:-0004}
case "$test_version" in
    0001) extra=(); test_flags=() ;;
    0002) extra=(mmu.c munch/probe.c); test_flags=(-DMUNCH_MMU_IRQ=1) ;;
    0003) extra=(munch/smp.c); test_flags=(-DMUNCH_SMP=1) ;;
    0004) extra=(munch/smp-hold.c munch/entry.S); test_flags=(-DMUNCH_SMP=1 -DMUNCH_SMP_HOLD=1) ;;
    *) echo 'Usage: bash shim/munch/build.sh [0001|0002|0003|0004]' >&2; exit 2 ;;
esac
out=out/munch-diag-$test_version
mkdir -p "$out"
flags=(-O2 -ffreestanding -nostdlib -fno-pic -fno-pie -mgeneral-regs-only
    -mstrict-align -fno-stack-protector -Wall -Wextra -Werror -I. -Imunch "${test_flags[@]}")
objects=()
for source in start.S console.c munch/guard.c munch/diag.c "${extra[@]}"; do
    obj=$(basename "${source%.*}")
    aarch64-linux-gnu-gcc "${flags[@]}" -c "$source" -o "$out/$obj.o"
    objects+=("$out/$obj.o")
done
# Only start.o's Image header may contain a link-time absolute address.
if aarch64-linux-gnu-readelf -r "${objects[@]:1}" | rg -q 'R_AARCH64_ABS'; then
    echo 'Unexpected absolute relocation' >&2; exit 1
fi
aarch64-linux-gnu-gcc "${flags[@]}" -static -no-pie -T shim.ld \
    -Wl,--build-id=none -Wl,--no-warn-rwx-segments -Wl,-N \
    "${objects[@]}" -o "$out/diag.elf"
aarch64-linux-gnu-objcopy -O binary "$out/diag.elf" "$out/Image"
python3 - "$out" <<'PY'
import gzip, pathlib, struct, sys
p = pathlib.Path(sys.argv[1])
b = bytearray((p / 'Image').read_bytes())
size = struct.unpack_from('<Q', b, 16)[0]
assert b[56:60] == b'ARM\x64' and len(b) <= size
# Match the observed Linux Image placement hint on munch.
struct.pack_into('<Q', b, 8, 0x80000)
b.extend(bytes(size - len(b)))
(p / 'Image').write_bytes(b)
# Empty newc archive: a valid, small ramdisk (never consumed by this shim).
header = b'070701' + b''.join(f'{x:08x}'.encode() for x in
    [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 11, 0])
cpio = header + b'TRAILER!!!\0'
cpio += bytes((-len(cpio)) % 4)
(p / 'ramdisk.gz').write_bytes(gzip.compress(cpio, mtime=0))
PY
# Uses installed vendor_boot/DTBO for the ABL DT; embeds no donor DTB.
mkbootimg --header_version 3 --kernel "$out/Image" --ramdisk "$out/ramdisk.gz" \
    --os_version 13.0.0 --os_patch_level 2025-04 --cmdline '' -o "$out/testios.img"
sha256sum "$out/testios.img"
