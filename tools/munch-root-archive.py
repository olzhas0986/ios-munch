#!/usr/bin/env python3
"""Assemble an iOS root tar from APFS content/metadata exports, without host chown or mounts."""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import plistlib
import stat
import tarfile


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exports', type=Path, help='directory containing export-{OS,SystemOS,AppOS}-20H392')
    ap.add_argument('output', type=Path)
    a = ap.parse_args()
    entries = {}

    def add(path, mode=0o40755, uid=0, gid=0, data=None):
        if path not in entries:
            entries[path] = dict(path=path, mode=mode, uid=uid, gid=gid, link='', size=0)
        if data is not None:
            entries[path].update(mode=mode, uid=uid, gid=gid, data=data, size=len(data), link='')

    def parents(path):
        parent = str(Path(path).parent)
        if parent not in ('.', '/'):
            parents(parent)
            add(parent)

    for source, prefix in [('OS', ''), ('SystemOS', '/private/preboot/Cryptexes/OS'),
                           ('AppOS', '/private/preboot/Cryptexes/App')]:
        folder = a.exports / f'export-{source}-20H392'
        rows = [json.loads(s) for s in folder.with_suffix('.jsonl').read_text().splitlines()]
        for raw in rows:
            r = copy.copy(raw)
            path = prefix + r['path'] or '/'
            parents(path)
            assert path not in entries or stat.S_ISDIR(r['mode']), ('duplicate', path)
            r['path'] = path
            if stat.S_ISREG(r['mode']):
                if r['link']:
                    r['link'] = prefix + r['link']
                else:
                    r['source'] = str(folder) + raw['path']
            # Decompressed bytes must not inherit Darwin's UF_COMPRESSED flag.
            r['flags'] = r.get('flags', 0) & ~0x20
            entries[path] = r

    # Match the working upstream single-volume cryptex/shared-cache layout.
    cache = '/private/preboot/Cryptexes/OS/System/Library/Caches/com.apple.dyld/'
    for path, r in list(entries.items()):
        dest = None
        if path.startswith(cache) and stat.S_ISREG(r['mode']):
            dest = '/System/Library/Caches/com.apple.dyld/' + path[len(cache):]
        elif path.startswith('/private/preboot/Cryptexes/') and not stat.S_ISDIR(r['mode']):
            for prefix in ['/private/preboot/Cryptexes/OS', '/private/preboot/Cryptexes/App']:
                if path.startswith(prefix + '/'):
                    candidate = path[len(prefix):]
                    if candidate not in entries:
                        dest = candidate
                    break
        if dest and dest not in entries:
            # A root framework symlink already exposes its cryptex subtree.
            # Adding children below it would implicitly create a conflicting directory.
            ancestor = Path(dest).parent
            blocked = False
            while str(ancestor) not in ('.', '/'):
                record = entries.get(str(ancestor))
                if record and stat.S_ISLNK(record['mode']):
                    blocked = True
                    break
                ancestor = ancestor.parent
            if blocked:
                continue
            parents(dest)
            alias = copy.copy(r)
            alias['path'] = dest
            if stat.S_ISREG(alias['mode']):
                alias.update(link=path, size=0)
                alias.pop('source', None)
            entries[dest] = alias

    def canonical(path):
        seen = set()
        while stat.S_ISREG(entries[path]['mode']) and entries[path]['link']:
            assert path not in seen, ('link cycle', path)
            seen.add(path)
            path = entries[path]['link']
        return path

    def read(path):
        r = entries[canonical(path)]
        return r['data'] if 'data' in r else Path(r['source']).read_bytes()

    def data(path, content, uid=0, gid=0, mode=0o100644):
        parents(path)
        add(path, mode, uid, gid, content)

    # Keep crash diagnostics useful while hardware-dependent services are incomplete.
    path = '/System/Library/xpc/launchd.plist'
    launchd = plistlib.loads(read(path))
    jobs = launchd['LaunchDaemons']
    for key in list(jobs):
        job = jobs[key]
        if job.get('Label') == 'com.apple.CommCenter':
            del jobs[key]
        elif '_PanicOnCrash' in job:
            job['_PanicOnCrasX'] = job.pop('_PanicOnCrash')
    data(path, plistlib.dumps(launchd, fmt=plistlib.FMT_BINARY), gid=80)

    # Writable single-volume directories normally created during an Apple restore.
    for path, uid, gid, mode in [
        ('/private/var/containers/Bundle', 33, 33, 0o40755),
        ('/private/var/containers/Data/System', 0, 0, 0o40755),
        ('/private/var/containers/Shared/SystemGroup', 0, 0, 0o40755),
        ('/private/var/containers/Temp', 0, 0, 0o40755),
        ('/private/var/tmp', 0, 0, 0o41777),
        ('/private/var/mobile/Library/Preferences', 501, 501, 0o40755),
        ('/private/var/keybags', 0, 0, 0o40700),
        ('/private/var/db/diagnostics', 272, 272, 0o40751),
        ('/private/var/db/uuidtext', 272, 272, 0o40755),
        ('/private/var/db/diagnostics/timesync', 272, 272, 0o40755)]:
        parents(path)
        add(path)
        entries[path].update(mode=mode, uid=uid, gid=gid)
    for path in ['diagnostics', 'uuidtext', 'diagnostics/timesync']:
        data('/private/var/db/' + path + '/.migrated', b'', 272, 272)
    data('/private/var/keybags/systembag.kb', plistlib.dumps({'KeyBagKeys': b'SWEET'}), mode=0o100600)
    preferences = {
        'com.apple.migration': {'LastSystemVersion': '20H392', 'DMUserDataDisposition': {'SyntheticDidUpgrade': False, 'buildVersion': '20H392'}},
        'com.apple.springboard': {'BKNoWatchdogs': True, 'MCForceShowCloudConfigurationUI': False},
        'com.apple.purplebuddy': {'SetupDone': True, 'SetupFinishedAllSteps': True, 'SetupVersion': 11, 'daemonizeNeedsToRun': False},
    }
    for name, values in preferences.items():
        path = '/private/var/mobile/Library/Preferences/' + name + '.plist'
        current = plistlib.loads(read(path)) if path in entries else {}
        current.update(values)
        data(path, plistlib.dumps(current, fmt=plistlib.FMT_BINARY), 501, 501, 0o100600)
    data('/private/etc/munch-release', b'MUNCH iOS 16.7.16 20H392 full-root preparation\n')

    # Directories, real files, hardlinks, then symlinks: no write traverses a link.
    def order(r):
        mode = r['mode']
        group = 0 if stat.S_ISDIR(mode) else 1 if stat.S_ISREG(mode) and not r['link'] else 2 if stat.S_ISREG(mode) else 3
        return group, r['path'].count('/'), r['path']

    for path in entries:
        parent = Path(path).parent
        while str(parent) not in ('.', '/'):
            record = entries.get(str(parent))
            assert not record or not stat.S_ISLNK(record['mode']), ('entry below symlink', path, str(parent))
            parent = parent.parent
    assert not a.output.exists(), 'refusing to overwrite archive'
    count = payload = 0
    partial = a.output.with_suffix(a.output.suffix + '.partial')
    assert not partial.exists()
    with partial.open('xb') as raw, tarfile.open(fileobj=raw, mode='w|', format=tarfile.PAX_FORMAT) as tar:
        for r in sorted(entries.values(), key=order):
            path, mode = r['path'], r['mode']
            assert path.startswith('/') and '..' not in Path(path).parts
            info = tarfile.TarInfo(path.lstrip('/') or '.')
            info.uid, info.gid, info.mode, info.mtime = r['uid'], r['gid'], mode & 0o7777, 0
            src = None
            if stat.S_ISDIR(mode):
                info.type = tarfile.DIRTYPE
            elif stat.S_ISLNK(mode):
                info.type, info.linkname = tarfile.SYMTYPE, r['link']
            elif stat.S_ISREG(mode) and r['link']:
                target = canonical(path)
                assert stat.S_ISREG(entries[target]['mode'])
                info.type, info.linkname = tarfile.LNKTYPE, target.lstrip('/')
            elif stat.S_ISREG(mode):
                info.size = r['size']
                src = io.BytesIO(r['data']) if 'data' in r else open(r['source'], 'rb')
                payload += info.size
            else:
                raise ValueError(('unsupported special node', path, oct(mode)))
            try:
                tar.addfile(info, src)
            finally:
                if src:
                    src.close()
            count += 1
            if count % 25000 == 0:
                print(f'Archived {count} entries', flush=True)
    partial.rename(a.output)
    critical = {path: hashlib.sha256(read(path)).hexdigest() for path in
                ['/sbin/launchd', '/usr/lib/dyld', '/System/Library/xpc/launchd.plist']}
    a.output.with_suffix('.complete.json').write_text(json.dumps(
        {'entries': count, 'payload_bytes': payload, 'archive_bytes': a.output.stat().st_size,
         'critical_sha256': critical}, indent=2) + '\n')
    print(f'{a.output}: {count} entries, {payload} data bytes', flush=True)


if __name__ == '__main__':
    main()
