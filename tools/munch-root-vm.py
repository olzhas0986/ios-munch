#!/usr/bin/env python3
"""Build an HFS root inside an isolated Linux VM; no host mounts or device access."""
import argparse
import gzip
import os
from pathlib import Path
import subprocess


def cpio(entries):
    out = bytearray()
    for inode, (name, mode, data) in enumerate([*entries, ('TRAILER!!!', 0, b'')], 1):
        fields = [inode, mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(name.encode()) + 1, 0]
        out += b'070701' + ''.join(f'{n:08x}' for n in fields).encode()
        out += name.encode() + b'\0'
        out += bytes((-len(out)) % 4)
        out += data
        out += bytes((-len(out)) % 4)
    return bytes(out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('runtime', type=Path, help='extracted QEMU/Alpine runtime')
    p.add_argument('archive', type=Path)
    p.add_argument('image', type=Path, help='existing blank HFS image file; never a device')
    p.add_argument('work', type=Path, help='new directory for initramfs and log')
    a = p.parse_args()
    runtime, archive, image = [x.resolve() for x in (a.runtime, a.archive, a.image)]
    assert image.is_file() and not image.is_symlink() and not str(image).startswith('/dev/')
    assert archive.is_file() and not a.work.exists()
    a.work.mkdir(parents=True)
    alpine = runtime / 'alpine'
    modules = alpine / 'lib/modules/6.18.58-0-lts/kernel'
    entries = [(d, 0o40755, b'') for d in ['bin', 'dev', 'proc', 'sys', 'target', 'mods']]
    entries += [('bin/busybox', 0o100755, (alpine / 'bin/busybox.static').read_bytes()),
                ('bin/sh', 0o120777, b'busybox')]
    # Dependency order is explicit; the guest sees only two virtual image files.
    depfile = modules.parent / 'modules.dep'
    deps = dict(line.split(':', 1) for line in depfile.read_text().splitlines())
    ordered = []
    def include(path):
        if path in ordered:
            return
        for dep in deps[path].split():
            include(dep)
        ordered.append(path)
    for name in ['virtio_pci', 'virtio_blk', 'nls_utf8', 'hfsplus']:
        found = list(modules.rglob(name + '.ko.gz'))
        assert len(found) == 1, (name, found)
        include(str(found[0].relative_to(modules.parent)))
    insmod = []
    for path in ordered:
        source = modules.parent / path
        name = source.name.removesuffix('.gz')
        entries.append(('mods/' + name, 0o100644, gzip.decompress(source.read_bytes())))
        insmod.append('insmod /mods/' + name)
    init = '''#!/bin/sh
/bin/busybox --install -s /bin
fail() { echo MUNCH_ROOT_VM_FAILED; dmesg | tail -25; sync; poweroff -f; }
trap fail EXIT
set -eu
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
''' + '\n'.join(insmod) + '''
sleep 2
mount -t hfsplus -o force,rw /dev/vda /target
echo MUNCH_ROOT_VM_EXTRACTING
tar -xpf /dev/vdb -C /target
sync
[ -s /target/sbin/launchd ]
[ -s /target/usr/lib/dyld ]
[ "$(readlink /target/var)" = private/var ]
[ "$(stat -c %u /target/private/var/mobile/Library/Preferences)" = 501 ]
sha256sum /target/sbin/launchd /target/usr/lib/dyld /target/System/Library/xpc/launchd.plist
df -k /target
sync
umount /target
echo MUNCH_ROOT_VM_PASS
trap - EXIT
poweroff -f
'''
    entries.append(('init', 0o100755, init.encode()))
    initrd = a.work.resolve() / 'initramfs.cpio.gz'
    initrd.write_bytes(gzip.compress(cpio(entries), mtime=0))
    qemu = runtime / 'usr/bin/qemu-system-x86_64'
    env = dict(os.environ, LD_LIBRARY_PATH=str(runtime / 'usr/lib'))
    cmd = [str(qemu), '-L', str(runtime / 'usr/share/qemu'), '-machine', 'pc',
           '-accel', 'tcg,thread=multi', '-cpu', 'max', '-smp', '2', '-m', '1536',
           '-nodefaults', '-nographic', '-serial', 'stdio', '-monitor', 'none', '-no-reboot',
           '-kernel', str(alpine / 'boot/vmlinuz-lts'), '-initrd', str(initrd),
           '-append', 'console=ttyS0 loglevel=3 panic=-1',
           '-drive', f'file={image},format=raw,if=virtio',
           '-drive', f'file={archive},format=raw,if=virtio,readonly=on']
    log = a.work / 'console.log'
    with log.open('wb') as out:
        result = subprocess.run(cmd, env=env, stdout=out, stderr=subprocess.STDOUT)
    text = log.read_text(errors='replace')
    assert result.returncode == 0 and 'MUNCH_ROOT_VM_PASS' in text and 'MUNCH_ROOT_VM_FAILED' not in text, text[-5000:]
    print('Guest extracted root, checked basic metadata and cleanly unmounted HFS:', image)


if __name__ == '__main__':
    main()
