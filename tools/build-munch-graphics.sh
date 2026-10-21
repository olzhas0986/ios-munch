#!/bin/bash
# Build the dyld-bound display probe using GNU assembly and the Mach-O writer.
set -euo pipefail
cd "$(dirname "$0")/.."
out=shim/out/munch-graphics-0016
mkdir -p "$out"
aarch64-linux-gnu-gcc -x assembler-with-cpp -c tools/munch-graphics.S -o "$out/probe.o"
if aarch64-linux-gnu-readelf -r "$out/probe.o" | rg -q R_AARCH64; then
    echo 'Graphics code must not contain relocations' >&2; exit 1
fi
aarch64-linux-gnu-objcopy -O binary -j .text "$out/probe.o" "$out/probe.text"
python3 tools/mkmunchgraphics.py "$out/probe.text" "$out/probe.macho"
