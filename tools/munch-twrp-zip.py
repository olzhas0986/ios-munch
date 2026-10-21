#!/usr/bin/env python3
"""Create a small TWRP launcher beside a completed, checksum-pinned root package."""
import argparse
import hashlib
from pathlib import Path
import zipfile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('package', type=Path)
    a = p.parse_args()
    folder = a.package
    sums = hashlib.sha256((folder / 'SHA256SUMS').read_bytes()).hexdigest()
    installer = hashlib.sha256((folder / 'install.sh').read_bytes()).hexdigest()
    path = folder / 'Install-Munch-iOS.zip'
    assert not path.exists()
    source = '''#!/system/bin/sh
# TWRP invokes update-binary with API version, output descriptor and ZIP path.
set -eu
set -o pipefail
[ "$#" = 3 ] || exit 2
outfd=$2
case "$outfd" in ''|*[!0-9]*) exit 2 ;; esac
ui() { echo "ui_print $*" > "/proc/self/fd/$outfd"; echo ui_print > "/proc/self/fd/$outfd"; }
fail() { ui "$*"; exit 1; }
folder=$(dirname "$3")
[ -f "$folder/SHA256SUMS" ] && [ -f "$folder/install.sh" ] || fail 'Keep this ZIP inside the complete USB installer folder.'
got=$(sha256sum "$folder/SHA256SUMS")
[ "${got%% *}" = SUMS_HASH ] || fail 'Package checksum list mismatch.'
got=$(sha256sum "$folder/install.sh")
[ "${got%% *}" = SCRIPT_HASH ] || fail 'Installer script checksum mismatch.'
ui 'Munch iOS root installation'
ui 'Target: separate 16 GiB iosroot partition.'
set +e
sh "$folder/install.sh" --apply 2>&1 | while IFS= read -r line; do ui "$line"; done
result=$?
set -e
[ "$result" = 0 ] || fail 'Installation failed. Keep the output for diagnosis.'
ui 'Rootfs installation and readback verification complete.'
ui 'Next: boot the matching testios.img using fastboot.'
'''.replace('SUMS_HASH', sums).replace('SCRIPT_HASH', installer)
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for name, data, mode in [
            ('META-INF/com/google/android/update-binary', source, 0o100755),
            ('META-INF/com/google/android/updater-script', '# Handled by update-binary.\n', 0o100644)]:
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = mode << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
    print('TWRP launcher:', path, hashlib.sha256(path.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
