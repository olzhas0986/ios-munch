#!/usr/bin/env python3
"""Recover deferred hard links after an interrupted BusyBox tar extraction."""
import argparse
import json
from pathlib import Path
import shlex
import tarfile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive', type=Path)
    p.add_argument('repair_plan', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    dropped = set(json.loads(a.repair_plan.read_text())['drop_archive_entries'])
    checks = ['#!/bin/sh', 'set -eu']
    count = 0
    with tarfile.open(a.archive) as src, tarfile.open(a.output, 'x') as dst:
        for entry in src:
            if entry.name in dropped or not (entry.islnk() or entry.issym()):
                continue
            dst.addfile(entry)
            target = '/target/' + entry.name
            if entry.islnk():
                checks.append('[ ' + shlex.quote(target) + ' -ef ' +
                              shlex.quote('/target/' + entry.linkname) + ' ]')
                count += 1
    checks.append(f'echo MUNCH_ROOT_HARDLINKS_PASS_{count}')
    a.output.with_suffix('.verify.sh').write_text('\n'.join(checks) + '\n')
    print(f'Repair archive: {count} hard links plus symlinks; no file payloads.')


if __name__ == '__main__':
    main()
