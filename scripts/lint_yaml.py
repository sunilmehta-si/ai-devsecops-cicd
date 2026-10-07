#!/usr/bin/env python3
"""Parses every YAML file and applies repo rules (no tabs, workflows declare permissions)."""
from __future__ import annotations

import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKIP = {".git", "node_modules", ".venv", "reports"}


def yaml_files():
    for path in ROOT.rglob("*"):
        if path.suffix in {".yml", ".yaml"} and not SKIP & set(path.relative_to(ROOT).parts):
            yield path


def check(path: pathlib.Path) -> list[str]:
    text = path.read_text()
    rel = path.relative_to(ROOT)
    problems = []
    if "\t" in text:
        problems.append(f"{rel}: contains tab characters")
    try:
        docs = [d for d in yaml.safe_load_all(text) if d is not None]
    except yaml.YAMLError as exc:
        return problems + [f"{rel}: invalid YAML ({exc.__class__.__name__})"]
    if rel.parts[:2] == (".github", "workflows"):
        for doc in docs:
            if "permissions" not in doc:
                problems.append(f"{rel}: workflow must declare top-level permissions")
    return problems


def main() -> int:
    files = list(yaml_files())
    problems = [p for f in files for p in check(f)]
    for problem in problems:
        print(problem, file=sys.stderr)
    print(f"Checked {len(files)} YAML file(s): {'FAILED' if problems else 'ok'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
