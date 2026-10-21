#!/usr/bin/env python3
"""Build the APFS file reader without FUSE or a CMake installation."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path, help='apfs-fuse checkout with lzfse submodule')
    p.add_argument('output', type=Path)
    a = p.parse_args()
    root = a.source.resolve()
    pins = [(root, '66b86bd525e8cb90f9012543be89b1f092b75cf3'),
            (root / '3rdparty/lzfse', 'e634ca58b4821d9f3d560cdc6df5dec02ffc93fd')]
    for path, revision in pins:
        assert subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD']).decode().strip() == revision
    sources = list(dict.fromkeys(re.findall(r'(?:ApfsLib|Crypto)/[A-Za-z0-9]+\.cpp', (root / 'CMakeLists.txt').read_text())))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='munch-apfs-') as work:
        objects = []
        for src in sorted((root / '3rdparty/lzfse/src').glob('*.c')):
            if src.name == 'lzfse_main.c':
                continue
            obj = Path(work) / (src.stem + '.o')
            subprocess.run(['cc', '-O2', '-c', str(src), '-o', str(obj)], check=True)
            objects.append(str(obj))
        subprocess.run(['g++', '-O2', '-std=c++11', '-include', 'cstdint', '-D_FILE_OFFSET_BITS=64',
                        '-I' + str(root), '-I' + str(root / '3rdparty/lzfse/src'),
                        str(Path(__file__).with_name('munch-apfs-read.cpp')),
                        *[str(root / s) for s in sources], *objects, '-lz', '-lbz2', '-o', str(a.output)], check=True)


if __name__ == '__main__':
    main()
