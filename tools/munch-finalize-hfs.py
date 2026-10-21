#!/usr/bin/env python3
"""Verify a local HFS image, refresh its alternate header, and verify again."""
import argparse
import os
from pathlib import Path
import stat
import struct
import subprocess


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('checker', type=Path)
    p.add_argument('image', type=Path)
    p.add_argument('log_directory', type=Path)
    a = p.parse_args()
    assert not a.image.is_symlink() and stat.S_ISREG(a.image.stat().st_mode)
    assert a.image.stat().st_size == 16 * 1024**3
    a.log_directory.mkdir(parents=True, exist_ok=False)

    def check(name):
        result = subprocess.run([str(a.checker.resolve()), '-fn', str(a.image.resolve())], capture_output=True)
        data = result.stdout + result.stderr
        (a.log_directory / name).write_bytes(data)
        assert result.returncode == 0 and b'appears to be OK' in data, data[-3000:]

    check('before.log')
    with a.image.open('r+b') as image:
        image.seek(1024)
        header = image.read(512)
        assert header[:2] in (b'H+', b'HX')
        assert struct.unpack_from('>II', header, 40) == (4096, 4194304)
        assert struct.unpack_from('>I', header, 4)[0] & 0x100
        image.seek(-1024, 2)
        backup = image.read(512)
        assert backup[:2] == header[:2]
        if backup != header:
            # Linux's last primary-header update can leave the alternate at a prior checkpoint.
            # Only copy the verified, clean primary into the alternate slot of this local file.
            image.seek(-1024, 2)
            assert image.write(header) == 512
            image.flush()
            os.fsync(image.fileno())
    check('after.log')
    print('Native HFS checks pass; clean primary/alternate volume headers synchronized.')


if __name__ == '__main__':
    main()
