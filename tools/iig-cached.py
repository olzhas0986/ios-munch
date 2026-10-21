#!/usr/bin/env python3
"""Replay pinned DriverKit-286 output for unchanged xnu-8796 .iig inputs.

This is deliberately not a general IIG replacement. Changed/unknown inputs
fail instead of silently substituting generated code from a different ABI.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "xnu/munch"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest = json.loads((CACHE / "iig-8796.json").read_text())
    if sys.argv[1:] == ["--version"]:
        print(manifest["generator"] + " (verified source snapshot)")
        return
    args = sys.argv[1:]
    separator = args.index("--") if "--" in args else len(args)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--def", dest="source", type=Path, required=True)
    parser.add_argument("--header", type=Path, required=True)
    parser.add_argument("--impl", type=Path, required=True)
    parser.add_argument("--framework-name", choices=["DriverKit"], required=True)
    options = parser.parse_args(args[:separator])
    source = options.source.resolve()
    if source.name not in manifest["sources"]:
        raise ValueError(f"no pinned IIG output for {source.name}")
    files = {p.name for p in source.parent.glob("*.iig")}
    if files != set(manifest["sources"]):
        raise ValueError("DriverKit .iig file set changed")
    for name, expected in manifest["sources"].items():
        if digest((source.parent / name).read_bytes()) != expected:
            raise ValueError(f"IIG input changed: {name}")
    if options.header.name != source.stem + ".h" or options.impl.name != source.name + ".cpp":
        raise ValueError("unexpected IIG output filenames")
    data = (CACHE / "iig-8796.tar.gz").read_bytes()
    if digest(data) != manifest["archive_sha256"]:
        raise ValueError("IIG snapshot archive checksum mismatch")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        members = archive.getmembers()
        if (len(members) != len(manifest["outputs"]) or
                {m.name for m in members} != set(manifest["outputs"]) or
                any(not m.isfile() or Path(m.name).name != m.name for m in members)):
            raise ValueError("unexpected archive contents")
        for target in (options.header, options.impl):
            output = archive.extractfile(target.name).read()
            if digest(output) != manifest["outputs"][target.name]:
                raise ValueError(f"generated file checksum mismatch: {target.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as tmp:
                tmp.write(output)
                temporary = Path(tmp.name)
            temporary.replace(target)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, tarfile.TarError) as error:
        sys.exit(f"IIG snapshot: {error}")
