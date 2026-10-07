#!/usr/bin/env python3
"""Create and verify a SHA-256 manifest for a model directory.

The manifest is what gets signed in CI (cosign sign-blob / OpenSSF model-signing), so a deploy can
prove the weights it loads are byte-identical to the ones that were scanned and approved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

UNSAFE_SUFFIXES = {".pkl", ".pickle", ".pt", ".pth", ".bin", ".joblib"}


def digest(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def files_in(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(p for p in root.rglob("*") if p.is_file() and p.name != "MANIFEST.json")


def create(root: pathlib.Path) -> dict:
    unsafe = [p.name for p in files_in(root) if p.suffix.lower() in UNSAFE_SUFFIXES]
    if unsafe:
        raise ValueError(f"unsafe serialization formats refused: {', '.join(unsafe)}")
    return {"version": 1, "files": {str(p.relative_to(root)): digest(p) for p in files_in(root)}}


def verify(root: pathlib.Path, manifest: dict) -> list[str]:
    expected, actual = manifest["files"], {str(p.relative_to(root)): digest(p) for p in files_in(root)}
    problems = [f"modified: {n}" for n in expected if n in actual and actual[n] != expected[n]]
    problems += [f"missing: {n}" for n in expected if n not in actual]
    problems += [f"unexpected: {n}" for n in actual if n not in expected]
    return sorted(problems)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("create", "verify"):
        p = sub.add_parser(name)
        p.add_argument("directory", type=pathlib.Path)
    args = parser.parse_args(argv)
    manifest_path = args.directory / "MANIFEST.json"
    if args.cmd == "create":
        try:
            manifest_path.write_text(json.dumps(create(args.directory), indent=2, sort_keys=True))
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1
        print(f"wrote {manifest_path}")
        return 0
    problems = verify(args.directory, json.loads(manifest_path.read_text()))
    for problem in problems:
        print(problem, file=sys.stderr)
    print("manifest verified" if not problems else "manifest verification FAILED")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
