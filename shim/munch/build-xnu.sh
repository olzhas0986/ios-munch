#!/bin/bash
# Package an audited early CI kernel for temporary boot; never access a phone.
set -euo pipefail
if [ "$#" -lt 3 ] || [ "$#" -gt 4 ]; then
    echo 'Usage: bash shim/munch/build-xnu.sh KERNEL LIVE.dtb INIT_RAMDISK [--graphics|--profiles]' >&2; exit 2
fi
mode=normal
if [ "$#" -eq 4 ]; then
    case "$4" in
        --graphics) mode=graphics ;;
        --profiles) mode=profiles ;;
        --smp8) mode=smp8 ;;
        *) echo 'Unknown option; expected --graphics or --profiles' >&2; exit 2 ;;
    esac
fi
kernel=$(realpath "$1")
live_dtb=$(realpath "$2")
init_ramdisk=$(realpath "$3")
cd "$(dirname "$0")/.."
out=out/munch-xnu-0030-touch
if [ "$mode" = graphics ]; then out="${out}-graphics"; fi
if [ "$mode" = profiles ]; then out=out/munch-xnu-0030-touch-profiled; fi
if [ "$mode" = smp8 ]; then out=out/munch-xnu-smp8-experimental; fi
mkdir -p "$out"
python3 - "$kernel" <<'PY'
from pathlib import Path
import hashlib, json, struct, sys
p = Path(sys.argv[1]); b = p.read_bytes()
lines = (p.parent / 'SHA256SUMS').read_text().splitlines()
expected = next(line.split()[0] for line in lines if line.split()[1] == p.name)
assert hashlib.sha256(b).hexdigest() == expected, 'kernel checksum mismatch'
magic, cpu, subtype = struct.unpack_from('<III', b)
assert magic == 0xfeedfacf and cpu == 0x0100000c and subtype & 0xffffff in (0, 1)
manifest = json.loads((p.parent / 'munch-patches.json').read_text())
assert manifest['stage'] == 'munch-full-root' and manifest['last_patch'] == 102
repo = Path.cwd().parent
for item in manifest['files']:
    assert int(item['name'][:4]) in (*range(1, 28), 32, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102)
    assert hashlib.sha256((repo / 'xnu/patches' / item['name']).read_bytes()).hexdigest() == item['sha256']
assert sorted(int(i['name'][:4]) for i in manifest['files'] if i['name'].endswith('.patch')) == [*range(1, 28), 32, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102]
print('Verified bounded iosroot full-root ARM64 CI kernel:', expected)
PY
if [ "$mode" = smp8 ]; then
    python3 ../tools/mkmunchadt.py "$live_dtb" "$out/munch.adt" --smp8-preview
else
    python3 ../tools/mkmunchadt.py "$live_dtb" "$out/munch.adt"
fi
cmdline='debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0 ufsroot=iosroot ufsrw=1 rootrw=1 ignition_level=1 launchd_unsecure_cache=1 wdt=-1 unentitled_ios_sim_launch=1 muncha650probe=1'
if [ "$mode" = graphics ]; then cmdline+=' sweetfb_noconsole=1'; fi
if [ "$mode" = smp8 ]; then cmdline="${cmdline/cpus=1/cpus=8}"; fi
if [ "$mode" = profiles ]; then
    cmdline+=' munchsample=SpringBoard,profiled munchnull=profiled'
fi
python3 ../tools/mkpayload.py "$kernel" "$out/munch.adt" "$out/payload.bin" \
    --ramdisk "$init_ramdisk" \
    --cmdline "$cmdline" > "$out/payload-info.txt"
flags=(-O2 -ffreestanding -nostdlib -fno-pic -fno-pie -mgeneral-regs-only
    -mstrict-align -fno-stack-protector -Wall -Wextra -Werror -I. -Imunch -DMUNCH_XNU=1)
objects=()
for source in start.S console.c fdt.c loader.c munch/guard.c munch/xnu-entry.c; do
    obj=$(basename "${source%.*}")
    aarch64-linux-gnu-gcc "${flags[@]}" -c "$source" -o "$out/$obj.o"
    objects+=("$out/$obj.o")
done
if aarch64-linux-gnu-readelf -r "${objects[@]:1}" | rg -q 'R_AARCH64_ABS'; then
    echo 'Unexpected absolute relocation' >&2; exit 1
fi
aarch64-linux-gnu-gcc "${flags[@]}" -static -no-pie -T shim.ld \
    -Wl,--build-id=none -Wl,--no-warn-rwx-segments -Wl,-N "${objects[@]}" -o "$out/shim.elf"
aarch64-linux-gnu-objcopy -O binary "$out/shim.elf" "$out/Image"
python3 - "$out/Image" <<'PY'
from pathlib import Path
import struct, sys
p = Path(sys.argv[1]); b = bytearray(p.read_bytes())
size = struct.unpack_from('<Q', b, 16)[0]
assert len(b) <= size and b[56:60] == b'ARM\x64'
struct.pack_into('<Q', b, 8, 0x80000)
b.extend(bytes(size - len(b))); p.write_bytes(b)
PY
mkbootimg --header_version 3 --kernel "$out/Image" --ramdisk "$out/payload.bin" \
    --os_version 13.0.0 --os_patch_level 2025-04 --cmdline '' -o "$out/testios.img"
sha256sum "$out/testios.img"
