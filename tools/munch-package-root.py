#!/usr/bin/env python3
"""Package a verified HFS root for installation from USB entirely inside TWRP."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess


class SplitOutput:
    def __init__(self, folder):
        self.folder = folder
        self.parts = []
        self.file = None
        self.used = 0
        self.hash = None

    def write(self, data):
        full = len(data)
        while data:
            if self.file is None:
                name = f'rootfs.hfs.gz.{len(self.parts):03}'
                self.file = (self.folder / name).open('xb')
                self.hash, self.used = hashlib.sha256(), 0
                self.parts.append(dict(name=name))
            n = min(len(data), 2 * 1024**3 - self.used)
            self.file.write(data[:n])
            self.hash.update(data[:n])
            self.used += n
            data = data[n:]
            if self.used == 2 * 1024**3:
                self.finish_part()
        return full

    def flush(self):
        if self.file:
            self.file.flush()

    def finish_part(self):
        if self.file:
            self.file.close()
            self.parts[-1].update(bytes=self.used, sha256=self.hash.hexdigest())
            self.file = None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('image', type=Path)
    p.add_argument('writer', type=Path)
    p.add_argument('vm_log', type=Path)
    p.add_argument('archive_manifest', type=Path)
    p.add_argument('output', type=Path, help='new USB package directory')
    p.add_argument('--boot', type=Path, required=True, help='matching verified testios.img')
    a = p.parse_args()
    log = a.vm_log.read_text(errors='replace')
    assert 'MUNCH_ROOT_VM_PASS' in log and 'MUNCH_ROOT_VM_FAILED' not in log, 'image build is not verified complete'
    assert 'MUNCH_ROOT_HARDLINKS_PASS_' in log, 'hard-link verification is required'
    assert 'MUNCH_ROOT_CACHE_PASS' in log, 'shared-cache installation was not checked'
    archive = json.loads(a.archive_manifest.read_text())
    for path, value in archive['critical_sha256'].items():
        assert value + '  /target' + path in log, ('guest file hash mismatch', path)
    assert a.image.stat().st_size == 16 * 1024**3
    with a.image.open('rb') as f:
        f.seek(1024)
        header = f.read(512)
        assert header[:2] in (b'H+', b'HX') and struct.unpack_from('>II', header, 40) == (4096, 4194304)
        assert struct.unpack_from('>I', header, 4)[0] & 0x100, 'HFS volume not cleanly unmounted'
        f.seek(-1024, 2)
        backup = f.read(512)
        assert header == backup, 'HFS primary/alternate volume headers differ'
    writer = a.writer.read_bytes()
    assert writer[:4] == b'\x7fELF' and struct.unpack_from('<H', writer, 18)[0] == 183
    boot = a.boot.read_bytes()
    assert boot[:8] == b'ANDROID!' and struct.unpack_from('<I', boot, 40)[0] == 3
    assert not a.output.exists()
    a.output.mkdir(parents=True)
    split = SplitOutput(a.output)
    rawhash = hashlib.sha256()
    with a.image.open('rb') as source, gzip.GzipFile(fileobj=split, mode='wb', compresslevel=3, mtime=0) as compressed:
        total = 0
        while block := source.read(4 * 1024**2):
            rawhash.update(block)
            compressed.write(block)
            total += len(block)
            if total % (1024**3) == 0:
                print(f'Packaged {total // 1024**3}/16 GiB', flush=True)
    split.finish_part()
    rawhash = rawhash.hexdigest()
    shutil.copyfile(a.writer, a.output / 'munch-root-write')
    shutil.copyfile(a.boot, a.output / 'testios.img')
    names = [p['name'] for p in split.parts]
    script = '''#!/system/bin/sh
# Install the prepared iOS HFS image into Munch iosroot only.
set -eu
set -o pipefail
case "${1:-}" in --check|--apply) ;; *) echo 'Usage: sh install.sh --check|--apply'; exit 2 ;; esac
[ "$(id -u)" = 0 ] || { echo 'Root TWRP required'; exit 1; }
[ "$(getprop ro.product.device)" = munch ] || { echo 'Not munch'; exit 1; }
[ -n "$(getprop ro.twrp.version)" ] || { echo 'Run inside TWRP'; exit 1; }
cd "$(dirname "$0")"
sha256sum -c SHA256SUMS
cp munch-root-write /tmp/munch-root-write-0019
chmod 700 /tmp/munch-root-write-0019
/tmp/munch-root-write-0019 --check
[ "$1" = --apply ] || { echo 'Package verified; no device writes'; exit 0; }
echo 'Installing iOS into the separate 16 GiB iosroot partition.'
'''
    script += 'cat ' + ' '.join(names) + ' | gzip -dc | /tmp/munch-root-write-0019 --apply ' + rawhash + '\n'
    script += "sync\necho 'Installation complete. Boot the matching XNU0019 testios.img.'\n"
    (a.output / 'install.sh').write_text(script)
    manifest = dict(image_bytes=16 * 1024**3, image_sha256=rawhash,
                    target='munch iosroot sda35', parts=split.parts, boot_sha256=hashlib.sha256(boot).hexdigest(),
                    archive=archive)
    (a.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    sums = []
    for name in [*names, 'munch-root-write', 'install.sh', 'manifest.json', 'testios.img']:
        digest = next((p['sha256'] for p in split.parts if p['name'] == name), None)
        if digest is None:
            digest = hashlib.sha256((a.output / name).read_bytes()).hexdigest()
        sums.append(f'{digest}  {name}\n')
    (a.output / 'SHA256SUMS').write_text(''.join(sums))
    subprocess.run(['python3', str(Path(__file__).with_name('munch-twrp-zip.py')), str(a.output)], check=True)
    print('USB package complete:', a.output, 'compressed bytes:', sum(p['bytes'] for p in split.parts))


if __name__ == '__main__':
    main()
