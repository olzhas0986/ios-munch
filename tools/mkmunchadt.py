#!/usr/bin/env python3
"""Build CPU0-only, no-UFS early XNU ADT after checking munch live FDT RAM.

Usage: python3 tools/mkmunchadt.py LIVE.dtb OUT.adt
Requires fdtget (dtc package). Does not read/write a connected phone.
"""
import argparse
import hashlib
from pathlib import Path
import struct
import subprocess

import adt
import mkadt

BASE, SIZE = 0x100000000, 0x40000000  # restricted 4..5 GiB early aperture


def cells(dtb, node, name, optional=False):
    result = subprocess.run(["fdtget", "-t", "x", str(dtb), node, name],
                            capture_output=True, text=True)
    if result.returncode:
        if optional:
            return None
        raise ValueError(f"missing/invalid FDT property {node}/{name}")
    return [int(n, 16) for n in result.stdout.split()]


def ranges(values):
    if len(values) % 4:
        raise ValueError("expected 64-bit address/size tuples")
    return [((values[i] << 32) | values[i + 1],
             (values[i + 2] << 32) | values[i + 3]) for i in range(0, len(values), 4)]


def overlaps(start, length):
    return start < BASE + SIZE and BASE < start + length


def audit(dtb):
    raw = dtb.read_bytes()
    if len(raw) < 40 or raw[:4] != b"\xd0\x0d\xfe\xed":
        raise ValueError("invalid FDT header")
    total = struct.unpack_from(">I", raw, 4)[0]
    if total > len(raw) or total < 40:
        raise ValueError("truncated FDT")
    if cells(dtb, "/", "qcom,board-id") != [0x32, 0]:
        raise ValueError("expected munch board-id 0x32/0")
    for node in ("/", "/reserved-memory"):
        if cells(dtb, node, "#address-cells") != [2] or cells(dtb, node, "#size-cells") != [2]:
            raise ValueError("unsupported FDT cell layout")
    memory = ranges(cells(dtb, "/memory", "reg"))
    if not any(start <= BASE and BASE + SIZE <= start + length for start, length in memory):
        raise ValueError("early XNU aperture lies outside DDR")
    children = subprocess.check_output(["fdtget", "-l", str(dtb), "/reserved-memory"], text=True).splitlines()
    fixed, dynamic = 0, 0
    for child in children:
        node = "/reserved-memory/" + child
        reg = cells(dtb, node, "reg", optional=True)
        if reg is not None:
            if not reg:
                raise ValueError(f"empty reservation for {node}")
            for start, length in ranges(reg):
                if overlaps(start, length):
                    raise ValueError(f"XNU aperture overlaps {node}")
                fixed += 1
        else:
            allocation = cells(dtb, node, "alloc-ranges", optional=True)
            if not allocation:
                raise ValueError(f"unknown allocation constraint for {node}")
            for start, length in ranges(allocation):
                if overlaps(start, length):
                    raise ValueError(f"dynamic reservation may overlap XNU: {node}")
            dynamic += 1
    offset = struct.unpack_from(">I", raw, 16)[0]
    if offset < 40 or offset & 7:
        raise ValueError("invalid FDT memreserve offset")
    while offset + 16 <= total:
        start, length = struct.unpack_from(">QQ", raw, offset)
        offset += 16
        if not start and not length:
            break
        if overlaps(start, length):
            raise ValueError("FDT memreserve overlaps XNU")
        fixed += 1
    else:
        raise ValueError("unterminated FDT reservation map")
    print(f"RAM audit: {fixed} fixed reservations and {dynamic} dynamic pools exclude 4..5 GiB")


def setprop(node, name, data):
    node.props = [(n, f, v) for n, f, v in node.props if n != name] + [(name, 0, data)]


def build():
    # Preserve upstream's generic platform bindings, not its RAM/SoC/timer.
    mkadt.PHYS_BASE, mkadt.MEM_SIZE = BASE, SIZE
    mkadt.FB_SIZE = 0x2300000
    mkadt.VTIMER_INTID = 27
    mkadt.SWEET_ECID = 0x4d554e4348000001  # synthetic MUNCH, never a device ID
    mkadt.BOOT_MANIFEST_HASH = hashlib.sha384(b"munch early boot manifest").digest()
    root = mkadt.build()
    root.children = [n for n in root.children if n.name not in ("sweet-ufs", "product")]
    for node in root.children:
        if node.name == "cpus":
            node.children = node.children[:1]
            setprop(node.children[0], "compatible", mkadt.cstr("qcom,kryo") + mkadt.cstr("ARM,v8"))
        elif node.name == "chosen":
            setprop(node, "firmware-version", mkadt.cstr("munch-early-shim"))
            setprop(node, "system-firmware-version", mkadt.cstr("munch-early-shim"))
        elif node.name == "arm-io":
            node.children = [n for n in node.children if n.name != "disp0"]
    setprop(root, "compatible", b"D22AP\0iPhone10,3\0xiaomi,munch\0xiaomi,sweet\0qcom,sm8250\0AppleARM\0")
    return adt.serialize(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dtb", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    audit(args.dtb)
    data = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    print(f"{args.output}: {len(data)} bytes, CPU0 only, virtual IRQ27, no UFS node")


if __name__ == "__main__":
    main()
