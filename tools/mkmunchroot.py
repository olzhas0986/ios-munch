#!/usr/bin/env python3
"""Build an unmounted HFS+ RAMDisk containing the static MUNCH PID1 probe."""
import argparse
import hashlib
from pathlib import Path
import struct
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('formatter', type=Path)
    parser.add_argument('editor', type=Path)
    parser.add_argument('init', type=Path)
    parser.add_argument('output', type=Path)
    a = parser.parse_args()
    formatter, editor, init = (str(p.resolve()) for p in (a.formatter, a.editor, a.init))
    program = Path(init).read_bytes()
    assert struct.unpack_from('<4I', program)[:2] == (0xfeedfacf, 0x100000c)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='munch-hfs-', dir=a.output.parent) as work:
        work = Path(work)
        image = work / 'root.hfs'
        with image.open('wb') as f:
            f.truncate(16 * 1024 * 1024)
        subprocess.run([formatter, '-U', '0', '-G', '0', '-M', '755', '-v', 'MunchRoot', str(image)], check=True)

        def edit(*args):
            return subprocess.run([editor, str(image), *args], check=True, capture_output=True)

        for name in ('sbin', 'dev', 'etc', 'usr', 'usr/lib', 'private', 'private/var', 'tmp'):
            edit('mkdir', '/' + name)
            edit('chmod', '755', '/' + name)
        edit('add', init, '/sbin/launchd')
        edit('chmod', '555', '/sbin/launchd')
        marker = work / 'munch-release'
        marker.write_text('MUNCH HFS: /etc/munch-release read OK\n')
        edit('add', str(marker), '/etc/munch-release')
        edit('chmod', '444', '/etc/munch-release')
        for source, destination in ((Path(init), '/sbin/launchd'), (marker, '/etc/munch-release')):
            extracted = work / 'extracted'
            edit('extract', destination, str(extracted))
            assert extracted.read_bytes() == source.read_bytes(), destination
        header = image.read_bytes()[1024:1536]
        assert header[:2] == b'H+' and struct.unpack_from('>I', header, 40)[0] == 4096
        listing = edit('ls', '/sbin').stdout.decode()
        assert '100555' in listing and 'launchd' in listing, listing
        image.replace(a.output)
    print(f'{a.output}: 16 MiB HFS+, init/marker extraction verified, executable mode 0555')
    print('SHA256:', hashlib.sha256(a.output.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
