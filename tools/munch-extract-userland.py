#!/usr/bin/env python3
"""Extract the dependency closure of restore /bin/cat and dyld with an APFS reader."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('reader', type=Path)
    p.add_argument('image', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument("--entry", action="append", help="additional executable path")
    a = p.parse_args()
    queue = [('/bin/cat', False), ('/usr/lib/dyld', False)] + [(name, False) for name in (a.entry or [])]
    seen, missing = {}, set()
    while queue:
        name, weak = queue.pop(0)
        assert name.startswith('/') and '..' not in Path(name).parts
        if name in seen:
            continue
        target = a.output / name.lstrip('/')
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            r = subprocess.run([str(a.reader.resolve()), str(a.image.resolve()), name, str(target.resolve())], capture_output=True)
            if r.returncode:
                if weak:
                    missing.add(name)
                    continue
                raise RuntimeError(f'cannot extract required image {name}: {r.stderr.decode()}')
        b = target.read_bytes()
        magic, cpu, sub = struct.unpack_from('<III', b)
        assert magic == 0xfeedfacf and cpu == 0x100000c and sub & 0xffffff in (0, 1), name
        deps, off = [], 32
        for _ in range(struct.unpack_from('<I', b, 16)[0]):
            cmd, size = struct.unpack_from('<II', b, off)
            assert size >= 8 and off + size <= len(b)
            if cmd in (0xc, 0x80000018, 0x8000001f, 0x80000023):
                start = struct.unpack_from('<I', b, off + 8)[0]
                dep = b[off + start:off + size].split(b'\0')[0].decode()
                deps.append({'path': dep, 'weak': cmd == 0x80000018})
                queue.append((dep, cmd == 0x80000018))
            off += size
        seen[name] = {'size': len(b), 'sha256': hashlib.sha256(b).hexdigest(), 'dependencies': deps}
    manifest = {'source': 'iPhone10,3 iOS 16.7.16 20H392 RestoreRamDisk 087-86719-047.dmg',
                'files': seen, 'missing_weak': sorted(missing - seen.keys())}
    (a.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'{len(seen)} plain ARM64 files, {sum(x["size"] for x in seen.values())} bytes')
    print('Unavailable weak dependencies:', manifest['missing_weak'])


if __name__ == '__main__':
    main()
