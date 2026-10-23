#!/usr/bin/env python3
"""Build opt-in SMP8-preview or CPU0-only XNU ADT with bounded Munch iosroot support after checking munch live FDT RAM.

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

BASE, SIZE = 0x100000000, 0x100000000  # audited 4..8 GiB for the system shared cache


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
    print(f"RAM audit: {fixed} fixed reservations and {dynamic} dynamic pools exclude 4..8 GiB")


def setprop(node, name, data):
    node.props = [(n, f, v) for n, f, v in node.props if n != name] + [(name, 0, data)]


def audit_smp8_dtb(dtb):
    """Refuse unknown processor topology rather than guessing core IDs."""
    for core in range(8):
        node = '/cpus/cpu@' + format(core << 8, 'x')
        reg = cells(dtb, node, 'reg')
        if reg != [0, core << 8]:
            raise ValueError(f'{node}: unexpected MPIDR cells {reg}')
        proc = subprocess.check_output(['fdtget', '-t', 's', str(dtb), node, 'enable-method'], text=True).strip()
        if proc != 'psci':
            raise ValueError(f'{node}: expected PSCI, got {proc}')
    method = subprocess.check_output(['fdtget', '-t', 's', str(dtb), '/psci', 'method'], text=True).strip()
    if method != 'smc':
        raise ValueError(f'PSCI method {method} != smc')
    print('SMP8 topology audit passed: MPIDR 0x000..0x700 and PSCI SMC')


def build(smp8=False):
    # Preserve upstream's generic platform bindings, not its RAM/SoC/timer.
    mkadt.PHYS_BASE, mkadt.MEM_SIZE = BASE, SIZE
    mkadt.FB_SIZE = 0x2300000
    mkadt.VTIMER_INTID = 27
    mkadt.SWEET_ECID = 0x4d554e4348000001  # synthetic MUNCH, never a device ID
    mkadt.BOOT_MANIFEST_HASH = hashlib.sha384(b"munch early boot manifest").digest()
    root = mkadt.build()
    # Keep the verified Munch loader's exact 4GiB aperture. Upstream's new
    # panic carve-out is not part of this hardware-validated profile yet.
    root.children = [child for child in root.children if child.name != 'pram']
    chosen = next(child for child in root.children if child.name == 'chosen')
    chosen.props = [(n, f, v) for n, f, v in chosen.props if n != 'embedded-panic-log-size']
    setprop(chosen, 'dram-size', mkadt.u64(SIZE))

    # Keep sanitized D22 product identity for Apple userspace.
    for child in root.children:
        if child.name == "sweet-ufs":
            setprop(child, "name", mkadt.cstr("munch-ufs"))
    for node in root.children:
        if node.name == "cpus":
            if not smp8:
                node.children = node.children[:1]
            else:
                if len(node.children) != 8:
                    raise ValueError('mkadt did not produce eight CPU nodes')
                # Not a verified heterogeneous topology for XNU yet.
                # Label physical core IDs and keep kernel CPU0 default.
                for core, c in enumerate(node.children):
                    setprop(c, 'reg', mkadt.u32(core << 8))
                    setprop(c, 'cpu-id', mkadt.u32(core))
                    setprop(c, 'state', mkadt.cstr('running' if core == 0 else 'stopped'))
            # The current generic IOCPU driver matches this legacy alias.
            # Keep the munch CPU identity first, as with the root PE alias.
            setprop(node.children[0], "compatible",
                    mkadt.cstr("qcom,kryo585") + mkadt.cstr("qcom,kryo470") +
                    mkadt.cstr("qcom,kryo") + mkadt.cstr("ARM,v8"))
        elif node.name == "chosen":
            setprop(node, "firmware-version", mkadt.cstr("munch-early-shim"))
            setprop(node, "system-firmware-version", mkadt.cstr("munch-early-shim"))
        elif node.name == "arm-io":
            for child in node.children:
                if child.name == "disp0":
                    setprop(child, "compatible", mkadt.cstr("munch,display"))
                    setprop(child, "canvas-width", mkadt.u32(1080))
                    setprop(child, "canvas-height", mkadt.u32(2400))
    setprop(root, "compatible", b"D22AP\0iPhone10,3\0xiaomi,munch\0xiaomi,sweet\0qcom,sm8250\0AppleARM\0")
    return adt.serialize(root)


def audit_touch(dtb):
    def cells(path, prop):
        return [int(v, 16) for v in subprocess.check_output(['fdtget', '-t', 'x', str(dtb), path, prop]).split()]
    def string(path, prop):
        return subprocess.check_output(['fdtget', '-t', 's', str(dtb), path, prop]).decode().strip()
    touch = '/soc/spi@990000/focaltech@0'
    pin = cells('/soc/pinctrl@f000000', 'phandle')[0]
    expected = [
        ('/soc/spi@990000', 'reg', [0x990000, 0x4000]),
        ('/soc/pinctrl@f000000', 'reg', [0xf000000, 0x1000000]),
        (touch, 'reg', [0]), (touch, 'spi-max-frequency', [6000000]),
        (touch, 'focaltech,reset-gpio', [pin, 33, 0]),
        (touch, 'focaltech,irq-gpio', [pin, 39, 0x2008]),
        (touch, 'focaltech,display-coords', [0, 0, 10800, 24000]),
        (touch, 'focaltech,max-touch-number', [10]),
        ('/soc/rsc@18200000', 'reg', [0x18200000, 0x10000, 0x18210000, 0x10000, 0x18220000, 0x10000]),
        ('/soc/rsc@18200000', 'qcom,drv-id', [2]),
        ('/soc/rsc@18200000', 'qcom,tcs-offset', [0xd00]),
        ('/soc/rsc@18200000', 'qcom,tcs-config', [2, 2, 0, 3, 1, 3, 3, 1]),
        ('/reserved-memory/reserved-memory@80860000', 'reg', [0, 0x80860000, 0, 0x20000]),
    ]
    for path, prop, wanted in expected:
        assert cells(path, prop) == wanted, 'unexpected Munch input binding: ' + path + ':' + prop
    for rail, uv, supply in [(1, 1800000, 'vcc_i2c-supply'), (10, 3000000, 'vdd-supply')]:
        node = '/soc/rsc@18200000/rpmh-regulator-ldoc' + str(rail)
        regulator = node + '/regulator-pm8150a-l' + str(rail)
        assert string(node, 'qcom,resource-name') == 'ldoc' + str(rail)
        assert string(node, 'qcom,regulator-type') == 'pmic5-ldo'
        assert cells(regulator, 'regulator-min-microvolt') == [uv]
        assert cells(regulator, 'qcom,init-voltage') == [uv]
        assert cells(touch, supply) == cells(regulator, 'phandle')
    assert string(touch, 'compatible') == 'focaltech,fts'
    print('Input audit: Munch SE4, GPIO33/39, FT3658U extent, L1C/L10C, RPMh DRV2 ACTIVE2..4')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dtb", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--smp8-preview", action="store_true",
                        help="emit eight CPU ADT nodes for offline review; NOT a bootable SMP8 configuration")
    args = parser.parse_args()
    audit(args.dtb)
    audit_touch(args.dtb)
    regs = subprocess.check_output(['fdtget', '-t', 'x', str(args.dtb), '/soc/ufshc@1d84000', 'reg']).split()
    assert [int(v, 16) for v in regs] == [0x1d84000, 0x3000, 0x1d90000, 0x8000], "unexpected live UFS MMIO"
    if args.smp8_preview:
        audit_smp8_dtb(args.dtb)
    data = build(smp8=args.smp8_preview)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    mode = "SMP8 ADT PREVIEW (NOT BOOT-READY)" if args.smp8_preview else "CPU0 only"
    print(f"{args.output}: {len(data)} bytes, {mode}, virtual IRQ27, bounded iosroot controller node")


if __name__ == "__main__":
    main()
