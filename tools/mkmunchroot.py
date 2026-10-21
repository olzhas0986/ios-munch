#!/usr/bin/env python3
"""Build an unmounted HFS+ RAMDisk containing the static MUNCH PID1 probe."""
import argparse
import hashlib
import json
import plistlib
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
    parser.add_argument("--userland", type=Path, help="extracted restore dependency closure")
    parser.add_argument("--launchd", action="store_true", help="stage Apple launchd behind a diagnostic PID1 wrapper")
    parser.add_argument("--system-version", type=Path)
    a = parser.parse_args()
    if a.launchd:
        assert a.userland and a.system_version, "launchd requires userland and SystemVersion.plist"
    size_mib = 104 if a.launchd else 16
    formatter, editor, init = (str(p.resolve()) for p in (a.formatter, a.editor, a.init))
    program = Path(init).read_bytes()
    assert struct.unpack_from('<4I', program)[:2] == (0xfeedfacf, 0x100000c)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='munch-hfs-', dir=a.output.parent) as work:
        work = Path(work)
        image = work / 'root.hfs'
        with image.open('wb') as f:
            f.truncate(size_mib * 1024 * 1024)
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
        if a.userland:
            manifest = json.loads((a.userland / 'manifest.json').read_text())
            directories = {'/', '/sbin', '/dev', '/etc', '/usr', '/usr/lib', '/private', '/private/var', '/tmp'}
            for source_name, info in manifest['files'].items():
                name = '/usr/libexec/munch-launchd' if a.launchd and source_name == '/sbin/launchd' else source_name
                relative = Path(name)
                assert relative.is_absolute() and '..' not in relative.parts
                source = a.userland / source_name.lstrip('/')
                assert hashlib.sha256(source.read_bytes()).hexdigest() == info['sha256']
                for directory in reversed(relative.parents):
                    if str(directory) not in directories:
                        edit('mkdir', str(directory))
                        edit('chmod', '755', str(directory))
                        directories.add(str(directory))
                edit('add', str(source.resolve()), name)
                edit('chmod', '555', name)
                extracted = work / 'verify-userland'
                edit('extract', name, str(extracted))
                assert extracted.read_bytes() == source.read_bytes(), name
            marker.write_text('MUNCH DYLD: Apple cat read this file OK\n')
            edit('add', str(marker), '/etc/munch-dyld-test')
            edit('chmod', '444', '/etc/munch-dyld-test')
            if a.launchd:
                for directory in ('/System', '/System/Library', '/System/Library/CoreServices',
                                  '/System/Library/LaunchDaemons', '/System/Library/LaunchAgents',
                                  '/Library', '/Library/LaunchDaemons', '/private/var/run',
                                  '/private/var/tmp', '/private/var/log', '/private/var/db',
                                  '/private/var/log/com.apple.xpc.launchd',
                                  '/private/var/db/com.apple.xpc.launchd',
                                  '/private/var/db/launchd.db', '/private/var/mobile'):
                    if directory not in directories:
                        edit('mkdir', directory)
                        edit('chmod', '755', directory)
                        directories.add(directory)
                edit('symlink', '/var', '/private/var')

                def add_data(path, data):
                    local = work / 'config'
                    local.write_bytes(data)
                    edit('add', str(local), path)
                    edit('chmod', '444', path)
                    extracted = work / 'verify-config'
                    edit('extract', path, str(extracted))
                    assert extracted.read_bytes() == data, path

                add_data('/System/Library/CoreServices/SystemVersion.plist', a.system_version.read_bytes())
                add_data('/etc/munch-service-test', b'MUNCH LAUNCHD: managed service ran OK\n')
                add_data('/etc/passwd', b'root:*:0:0:System Administrator:/var/root:/bin/sh\n')
                add_data('/etc/group', b'wheel:*:0:root\n')
                job = {'Label': 'org.munch.probe', 'ProgramArguments': ['/bin/cat', '/etc/munch-service-test'],
                       'RunAtLoad': True, 'LaunchOnlyOnce': True,
                       'StandardOutPath': '/dev/console', 'StandardErrorPath': '/dev/console'}
                add_data('/System/Library/LaunchDaemons/org.munch.probe.plist', plistlib.dumps(job))
        header = image.read_bytes()[1024:1536]
        assert header[:2] == b'H+' and struct.unpack_from('>I', header, 40)[0] == 4096
        listing = edit('ls', '/sbin').stdout.decode()
        assert '100555' in listing and 'launchd' in listing, listing
        image.replace(a.output)
    print(f'{a.output}: {size_mib} MiB HFS+, init/marker extraction verified, executable mode 0555')
    print('SHA256:', hashlib.sha256(a.output.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
