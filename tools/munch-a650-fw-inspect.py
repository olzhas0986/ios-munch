#!/usr/bin/env python3
"""Inspect Adreno A650 GMU firmware blocks without writing hardware."""
import hashlib
import json
import struct
import sys
import zipfile
from pathlib import Path

EXPECTED_SHA = (
    "df79fa8482fcc7587bb239b9c9e2b24"
    "bce4729893b990fe3f82b30da8175b01c"
)

HEADER = struct.Struct("<IIII")

TCM = {
    "ITCM": (0x00000000, 0x00004000),
    "DTCM": (0x10004000, 0x10008000),
}

def main():
    archive = Path.home() / "uefi/pmos-munch/a650zap.zip"

    if not archive.is_file():
        raise SystemExit(f"Missing archive: {archive}")

    with zipfile.ZipFile(archive) as z:
        data = z.read("a650_gmu.bin")

    sha = hashlib.sha256(data).hexdigest()
    assert sha == EXPECTED_SHA, "Firmware SHA256 mismatch"

    blocks = []
    offset = 0

    print("=== A650 GMU FIRMWARE ===")
    print("Size:", len(data))
    print("SHA256:", sha)
    print()
    print("=== BLOCK MAP ===")

    while offset < len(data):
        remaining = len(data) - offset
        assert remaining >= HEADER.size, (
            f"Truncated header at offset 0x{offset:x}"
        )

        addr, size, kind, value = HEADER.unpack_from(data, offset)

        payload_start = offset + HEADER.size
        payload_end = payload_start + size

        assert payload_end <= len(data), (
            f"Block at 0x{offset:x} exceeds firmware size"
        )

        region = "EXTERNAL/UNKNOWN"

        if size:
            matches = []
            for name, (start, end) in TCM.items():
                if start <= addr < end:
                    assert addr + size <= end, (
                        f"{name} boundary exceeded"
                    )
                    matches.append(name)

            if matches:
                region = matches[0]
        else:
            region = "METADATA/EMPTY"

        entry = {
            "index": len(blocks),
            "file_offset": offset,
            "destination": addr,
            "size": size,
            "type": kind,
            "value": value,
            "region": region,
            "payload_sha256": hashlib.sha256(
                data[payload_start:payload_end]
            ).hexdigest(),
        }

        blocks.append(entry)

        print(
            f"#{entry['index']:02d} "
            f"offset=0x{offset:05x} "
            f"addr=0x{addr:08x} "
            f"size={size:5d} "
            f"type={kind:3d} "
            f"value=0x{value:08x} "
            f"{region}"
        )

        offset = payload_end

    assert offset == len(data)
    assert blocks, "No blocks found"

    # Check overlaps in known TCM regions.
    for region in TCM:
        spans = sorted(
            (b["destination"], b["destination"] + b["size"])
            for b in blocks
            if b["region"] == region and b["size"]
        )
        for previous, current in zip(spans, spans[1:]):
            assert previous[1] <= current[0], (
                f"{region}: overlapping blocks"
            )

    result = {
        "device": "POCO F4 / munch",
        "gpu": "Adreno 650",
        "firmware": "a650_gmu.bin",
        "firmware_sha256": sha,
        "firmware_size": len(data),
        "blocks": blocks,
        "hardware_writes": False,
    }

    output = Path("research/munch/smp/a650-gmu-layout.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")

    print()
    print(f"PASS: parsed {len(blocks)} blocks")
    print("PASS: payloads stay within firmware")
    print("PASS: known TCM regions checked")
    print("NOTE: external IOVA targets not yet validated")
    print("NOTE: no firmware uploaded to GPU")
    print("Layout:", output)

if __name__ == "__main__":
    main()
