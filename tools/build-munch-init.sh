#!/bin/bash
# Build a static PID1 with the GNU cross assembler; no Apple SDK required.
set -euo pipefail
cd "$(dirname "$0")/.."
flags=()
source=tools/munch-init.S
case "${1:-mockfs}" in
    mockfs) out=shim/out/munch-init-0008 ;;
    hfs) out=shim/out/munch-init-0009; flags=(-DMUNCH_HFS_PROBE=1) ;;
    dyld) out=shim/out/munch-init-0010; flags=(-DMUNCH_HFS_PROBE=1 -DMUNCH_DYLD_PROBE=1) ;;
    launchd) out=shim/out/munch-init-0012; flags=(-DMUNCH_HFS_PROBE=1 -DMUNCH_LAUNCHD_PROBE=1) ;;
    service) out=shim/out/munch-service-0014; source=tools/munch-service.S ;;
    syslog) out=shim/out/munch-service-0015; source=tools/munch-service.S; flags=(-DMUNCH_SYSLOG_PROBE=1) ;;
    *) echo "Usage: bash tools/build-munch-init.sh [mockfs|hfs|dyld|launchd|service|syslog]" >&2; exit 2 ;;
esac
mkdir -p "$out"
aarch64-linux-gnu-gcc -x assembler-with-cpp "${flags[@]}" -c "$source" -o "$out/init.o"
if aarch64-linux-gnu-readelf -r "$out/init.o" | rg -q R_AARCH64; then
    echo 'PID1 must not contain relocations' >&2; exit 1
fi
aarch64-linux-gnu-objcopy -O binary -j .text "$out/init.o" "$out/init.text"
python3 - "$out" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, 'tools')
import mkinit
p = Path(sys.argv[1])
mkinit.IDENT = b'org.munch.service\0' if 'service' in p.name else b'org.munch.init\0'
image = mkinit.build_code((p / 'init.text').read_bytes())
(p / 'init.macho').write_bytes(image)
print(f'{p}/init.macho: {len(image)} bytes, static arm64 executable')
PY
