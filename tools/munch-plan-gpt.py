#!/usr/bin/env python3
"""Validate captured Munch GPT copies and prepare a guarded 16 GiB split offline."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import uuid
import zlib

BLOCK = 4096
DISK_BLOCKS = 30650368
CAPTURE = 1048576
TAIL_BASE = DISK_BLOCKS - CAPTURE // BLOCK


def capture(path):
    raw = path.read_bytes()
    assert len(raw) >= CAPTURE, 'Truncated capture'
    trailer = raw[CAPTURE:]
    assert not trailer or re.fullmatch(rb'256\+0 records in\r?\n256\+0 records out\r?\n1048576 bytes[^\n]*\r?\n', trailer), 'Unexpected capture trailer'
    return raw[:CAPTURE]


def parse(blob, base, current):
    off = (current - base) * BLOCK
    h = blob[off:off + BLOCK]
    assert h[:8] == b'EFI PART'
    rev, size, crc, reserved = struct.unpack_from('<4I', h, 8)
    assert rev == 0x10000 and size == 92 and reserved == 0
    test = bytearray(h[:size]); struct.pack_into('<I', test, 16, 0)
    assert zlib.crc32(test) == crc, 'GPT header CRC mismatch'
    cur, other, first, last = struct.unpack_from('<4Q', h, 24)
    lba, count, stride, array_crc = struct.unpack_from('<QIII', h, 72)
    assert cur == current and other == (DISK_BLOCKS - 1 if cur == 1 else 1)
    assert (first, last, count, stride) == (6, DISK_BLOCKS - 6, 64, 128)
    assert lba == (2 if cur == 1 else DISK_BLOCKS - 5)
    off = (lba - base) * BLOCK
    entries = blob[off:off + count * stride]
    assert len(entries) == count * stride and zlib.crc32(entries) == array_crc, 'GPT array CRC mismatch'
    used = []
    for i in range(count):
        e = entries[i * stride:(i + 1) * stride]
        if e[:16] == bytes(16):
            assert e == bytes(stride), 'Nonzero unused GPT entry'
            continue
        start, end = struct.unpack_from('<QQ', e, 32)
        assert first <= start <= end <= last
        name = e[56:128].decode('utf-16le').rstrip('\0')
        used.append((start, end, i + 1, name))
    for a, b in zip(sorted(used), sorted(used)[1:]):
        assert a[1] < b[0], 'Overlapping GPT entries'
    return h, entries, used


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('head', type=Path)
    ap.add_argument('tail', type=Path)
    ap.add_argument('output', type=Path)
    a = ap.parse_args()
    head, tail = capture(a.head), capture(a.tail)
    ph, pe, used = parse(head, 0, 1)
    bh, be, other_used = parse(tail, TAIL_BASE, DISK_BLOCKS - 1)
    assert pe == be and used == other_used and ph[56:72] == bh[56:72]
    assert len(used) == 34 and used[-1] == (2949120, 30650362, 34, 'userdata')
    assert not any(p[3] == 'iosroot' for p in used)
    ios_blocks = 16 * 1024**3 // BLOCK
    ios_start = ((used[-1][1] + 1 - ios_blocks) // 256) * 256
    ios_end = ios_start + ios_blocks - 1
    assert (ios_start, ios_end) == (26455808, 30650111)
    entries = bytearray(pe)
    struct.pack_into('<Q', entries, 33 * 128 + 40, ios_start - 1)
    e = bytearray(128)
    e[:16] = uuid.UUID('48465300-0000-11aa-aa11-00306543ecac').bytes_le
    e[16:32] = uuid.uuid4().bytes_le
    struct.pack_into('<QQQ', e, 32, ios_start, ios_end, 0)
    label = 'iosroot'.encode('utf-16le'); e[56:56 + len(label)] = label
    entries[34 * 128:35 * 128] = e
    assert entries[:33 * 128] == pe[:33 * 128]
    assert entries[33 * 128:33 * 128 + 40] == pe[33 * 128:33 * 128 + 40]
    assert entries[33 * 128 + 48:34 * 128] == pe[33 * 128 + 48:34 * 128]
    assert entries[35 * 128:] == pe[35 * 128:]

    def header(old):
        h = bytearray(old)
        struct.pack_into('<I', h, 88, zlib.crc32(entries))
        struct.pack_into('<I', h, 16, 0)
        struct.pack_into('<I', h, 16, zlib.crc32(h[:92]))
        return bytes(h)

    new_ph, new_bh = header(ph), header(bh)
    new_head, new_tail = bytearray(head), bytearray(tail)
    new_head[BLOCK:2 * BLOCK] = new_ph
    new_head[2 * BLOCK:4 * BLOCK] = entries
    new_tail[-5 * BLOCK:-3 * BLOCK] = entries
    new_tail[-BLOCK:] = new_bh
    assert parse(new_head, 0, 1)[1] == parse(new_tail, TAIL_BASE, DISK_BLOCKS - 1)[1]
    a.output.mkdir(parents=True, exist_ok=False)
    items = [('backup-entries', DISK_BLOCKS - 5, be, bytes(entries)),
             ('backup-header', DISK_BLOCKS - 1, bh, new_bh),
             ('primary-entries', 2, pe, bytes(entries)), ('primary-header', 1, ph, new_ph)]
    manifest = {'block_size': BLOCK, 'disk_blocks': DISK_BLOCKS,
                'userdata': {'start': 2949120, 'end': ios_start - 1},
                'iosroot': {'number': 35, 'start': ios_start, 'end': ios_end, 'bytes': ios_blocks * BLOCK},
                'regions': []}
    checks, writes, verifies = [], [], []
    for name, lba, old, new in items:
        (a.output / (name + '.bin')).write_bytes(new)
        (a.output / (name + '.original.bin')).write_bytes(old)
        old_hash, new_hash = hashlib.sha256(old).hexdigest(), hashlib.sha256(new).hexdigest()
        count = len(new) // BLOCK
        manifest['regions'].append(dict(name=name, lba=lba, count=count, original_sha256=old_hash, new_sha256=new_hash))
        read = f'dd if=/dev/block/sda bs=4096 skip={lba} count={count} 2>/dev/null'
        checks += [f'check_hash "$(sha256sum "$work/{name}.bin")" {new_hash}',
                   f'check_hash "$({read} | sha256sum)" {old_hash}']
        writes += [f'dd if="$work/{name}.bin" of=/dev/block/sda bs=4096 seek={lba} count={count} conv=notrunc', 'sync']
        verifies += [f'check_hash "$({read} | sha256sum)" {new_hash}']
    script = '''#!/system/bin/sh
# Apply only the previously validated Munch GPT plan. This invalidates old userdata.
set -eu
[ "${1:-}" = --apply ] || { echo 'Usage: sh apply.sh --apply'; exit 1; }
[ "$(id -u)" = 0 ] || { echo 'Root recovery required'; exit 1; }
[ "$(getprop ro.product.device)" = munch ] || { echo 'Not munch'; exit 1; }
[ "$(cat /sys/class/block/sda/size)" = 245202944 ] || exit 1
[ "$(cat /sys/class/block/sda/queue/logical_block_size)" = 4096 ] || exit 1
if awk '$2 == "/data" || $2 == "/sdcard" || $2 == "/metadata" || index($2,"/data/")==1 {busy=1} END {exit !busy}' /proc/mounts; then
    echo 'Unmount /sdcard, /data and /metadata first. No changes made.'; exit 1
fi
work=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
check_hash() {
    got=${1%% *}
    [ "$got" = "$2" ] || { echo 'Hash mismatch. Stop; do not format or boot Android.'; exit 1; }
}
'''
    script += '\n'.join(checks) + '\n'
    script += "echo 'Original GPT and all input files verified. Applying 16 GiB split.'\n"
    script += '\n'.join(writes + verifies) + '\n'
    script += "echo 'GPT verified. Reboot directly into recovery, then inspect new partition sizes before Format Data.'\n"
    (a.output / 'apply.sh').write_text(script)
    (a.output / 'plan.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({k: v for k, v in manifest.items() if k != 'regions'}, indent=2))
    print('Both GPT CRCs and arrays verified; only userdata end/new iosroot entry change. No device writes.')


if __name__ == '__main__':
    main()
