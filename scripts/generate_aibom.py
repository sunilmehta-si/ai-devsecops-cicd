#!/usr/bin/env python3
"""Generates a CycloneDX 1.6 AI bill of materials from models.yaml."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHA256 = re.compile(r"^[0-9a-f]{64}$")
UNSAFE_SERIALIZATION = {"pickle", "pt", "bin", "joblib"}
TRUSTED_SOURCES = ("first-party", "huggingface.co/")


def sha256_of(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(entry: dict) -> list[str]:
    problems, ident = [], entry.get("id", "<missing id>")
    for key in ("id", "name", "version", "source", "license", "serialization"):
        if not entry.get(key):
            problems.append(f"{ident}: missing {key}")
    source = str(entry.get("source", ""))
    if source and not source.startswith(TRUSTED_SOURCES):
        problems.append(f"{ident}: source {source!r} is not in the trusted list")
    if entry.get("serialization") in UNSAFE_SERIALIZATION:
        problems.append(f"{ident}: unsafe serialization {entry['serialization']!r}; use safetensors or gguf")
    if "path" not in entry and not SHA256.match(str(entry.get("sha256", ""))):
        problems.append(f"{ident}: external models must pin a 64-character sha256")
    return problems


def build_bom(entries: list[dict]) -> dict:
    components = []
    for entry in entries:
        digest = sha256_of(ROOT / entry["path"]) if "path" in entry else entry["sha256"]
        components.append({
            "type": "machine-learning-model",
            "bom-ref": entry["id"],
            "name": entry["name"],
            "version": str(entry["version"]),
            "licenses": [{"license": {"id": entry["license"]}}],
            "hashes": [{"alg": "SHA-256", "content": digest}],
            "properties": [
                {"name": "source", "value": entry["source"]},
                {"name": "serialization", "value": entry["serialization"]},
                {"name": "purpose", "value": entry.get("purpose", "")},
            ],
        })
    return {"bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1, "components": components}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", default=str(ROOT / "models.yaml"))
    parser.add_argument("--output", default=str(ROOT / "reports" / "aibom.cdx.json"))
    args = parser.parse_args(argv)
    entries = (yaml.safe_load(pathlib.Path(args.inventory).read_text()) or {}).get("models", [])
    problems = [p for e in entries for p in validate(e)]
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build_bom(entries), indent=2))
    print(f"AI-BOM written to {out} ({len(entries)} model(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
