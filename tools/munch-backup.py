#!/usr/bin/env python3
"""Copy Munch rollback images to a PC through root recovery ADB; never write a block device."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('destination', type=Path, help='new directory on the PC')
    ap.add_argument('--adb', default='adb')
    ap.add_argument('--serial')
    a = ap.parse_args()
    adb = [a.adb] + (['-s', a.serial] if a.serial else ['-d'])

    def shell(*args):
        return subprocess.check_output(adb + ['shell', *args], text=True).strip()

    if shell('id', '-u') != '0':
        raise SystemExit('Root TWRP ADB is required.')
    if 'munch' not in [shell('getprop', 'ro.product.device'), shell('getprop', 'ro.product.vendor.device')]:
        raise SystemExit('Not a Munch device.')
    mounts = shell('cat', '/proc/mounts').splitlines()
    blocked = [line.split()[1] for line in mounts
               if line.split()[1] in ('/data', '/sdcard', '/metadata') or line.split()[1].startswith('/data/')]
    if blocked:
        raise SystemExit('Unmount these in recovery before the raw backup: ' + ', '.join(blocked))
    names = ['userdata', 'metadata', 'boot_a', 'boot_b', 'vendor_boot_a', 'vendor_boot_b',
             'dtbo_a', 'dtbo_b', 'vbmeta_a', 'vbmeta_b', 'vbmeta_system_a', 'vbmeta_system_b',
             'persist', 'persistbak', 'modemst1', 'modemst2', 'fsg', 'fsc']
    parts = []
    for name in names:
        path = '/dev/block/by-name/' + name
        size = int(shell('blockdev', '--getsize64', path))
        if size <= 0:
            raise SystemExit('Invalid block size for ' + name)
        parts.append((name, path, size))
    geometry = {}
    for name in ('sda', 'sdb', 'sdc', 'sdd', 'sde', 'sdf'):
        size = int(shell('cat', '/sys/class/block/' + name + '/size')) * 512
        logical = int(shell('cat', '/sys/class/block/' + name + '/queue/logical_block_size'))
        if logical != 4096 or size % 4096 or size < 2 * 1048576:
            raise SystemExit('Unexpected UFS geometry: ' + name)
        geometry[name] = {'bytes': size, 'logical_block_size': logical}
    if a.destination.exists():
        raise SystemExit('Choose a new directory; existing backups are never overwritten.')
    if not a.destination.parent.is_dir():
        raise SystemExit('Destination parent does not exist.')
    required = sum(p[2] for p in parts) + 12 * 1048576 + 2 * 1024**3
    if shutil.disk_usage(a.destination.parent).free < required:
        raise SystemExit(f'Need at least {required / 1024**3:.1f} GiB free on the destination disk.')
    a.destination.mkdir()
    manifest = {'device': 'munch', 'geometry': geometry, 'images': {}}

    def save_manifest():
        (a.destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')

    def copy(name, path, size, skip=None):
        final = a.destination / name
        partial = final.with_suffix(final.suffix + '.partial')
        command = ['dd', 'if=' + path, 'bs=4194304'] if skip is None else [
            'dd', 'if=' + path, 'bs=4096', 'skip=' + str(skip), 'count=256']
        print(f'Copying {name}: {size / 1024**3:.3f} GiB', flush=True)
        process = subprocess.Popen(adb + ['exec-out', *command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        digest = hashlib.sha256()
        total = 0
        try:
            with partial.open('xb') as out:
                while chunk := process.stdout.read(4 * 1048576):
                    out.write(chunk)
                    digest.update(chunk)
                    total += len(chunk)
                    if total > size:
                        raise RuntimeError('Device returned more bytes than expected')
                out.flush()
                os.fsync(out.fileno())
            error = process.stderr.read().decode(errors='replace')
            if process.wait() != 0 or total != size:
                raise RuntimeError(f'Incomplete {name}: {total}/{size} bytes; {error}')
            local_hash = digest.hexdigest()
            if skip is None:
                print('Checking SHA256 on phone: ' + name, flush=True)
                remote_hash = shell('sha256sum', path).split()[0]
                if local_hash != remote_hash:
                    raise RuntimeError('Phone/PC SHA256 mismatch: ' + name)
            partial.rename(final)
            manifest['images'][name] = {'source': path, 'bytes': total, 'sha256': local_hash,
                                       'skip_4096_blocks': skip, 'phone_hash_verified': skip is None}
            save_manifest()
            print('Verified ' + name, flush=True)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()

    save_manifest()
    # Preserve primary/backup GPT and nearby blocks on every UFS LUN first.
    for disk, info in geometry.items():
        for suffix, skip in [('head', 0), ('tail', info['bytes'] // 4096 - 256)]:
            copy(disk + '-' + suffix + '.bin', '/dev/block/' + disk, 1048576, skip)
    # Smaller critical rollback images precede the large userdata copy.
    for name, path, size in sorted(parts, key=lambda p: p[2]):
        copy(name + '.img', path, size)
    print('Backup complete. Keep manifest.json with the images. No device partitions were written.')
    print('Raw userdata is for original-geometry rollback, not restoration into a smaller partition.')


if __name__ == '__main__':
    main()
