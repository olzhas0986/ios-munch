#!/usr/bin/env python3
"""Select early XNU patches without sweet UFS/USB/input drivers."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
LAST = 27  # 0028 adds the sweet UFS driver; later hardware is not selected.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dxb", type=Path)
    target = parser.parse_args().dxb.resolve()
    build = target / "build.sh"
    text = build.read_text()
    old = 'ARCHS="x86_64 arm64e" VALID_ARCHS="x86_64 arm64e"'
    if text.count(old) != 1:
        raise ValueError("pinned dxb firehose build command changed")
    text = text.replace(old, 'ARCHS="x86_64 arm64e arm64" VALID_ARCHS="x86_64 arm64e arm64"')
    old = '                warning "Skipping patch ${PATCH} (already upstream, previously applied, or malformed): ${APPLY_CHECK}"'
    if text.count(old) != 1:
        raise ValueError("pinned dxb patch loop changed")
    text = text.replace(old, '''                case "${PATCH##*/}" in
                    [0-9][0-9][0-9][0-9]-*)
                        error "Required munch base patch failed: ${PATCH}: ${APPLY_CHECK}"
                        exit 1 ;;
                esac
''' + old)
    selected = []
    for file in sorted((ROOT / "xnu/patches").iterdir()):
        match = re.fullmatch(r"(\d{4})-.+\.(patch|sh)", file.name)
        if match and 1 <= int(match[1]) <= LAST:
            selected.append(file)
    numbers = [int(p.name[:4]) for p in selected if p.suffix == ".patch"]
    if sorted(numbers) != list(range(1, LAST + 1)):
        raise ValueError("incomplete or duplicate early patch sequence")
    destination = target / "patches"
    destination.mkdir(exist_ok=True)
    if any(re.match(r"\d{4}-", p.name) for p in destination.iterdir()):
        raise ValueError("use a fresh dxb checkout: numbered patches already present")
    # All checks complete before mutating the pinned build script/patch directory.
    build.write_text(text)
    manifest = {"device": "munch", "stage": "early-no-ufs", "last_patch": LAST,
                "xnu_tag": "xnu-8796.141.3", "internal_machine_config": "SWEET", "files": []}
    for file in selected:
        shutil.copy2(file, destination / file.name)
        manifest["files"].append({"name": file.name,
                                  "sha256": hashlib.sha256(file.read_bytes()).hexdigest()})
    (target / "munch-patches.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Staged {LAST} patches and {len(selected) - LAST} source-provider scripts; no UFS/hardware patches after 0027")


if __name__ == "__main__":
    main()
