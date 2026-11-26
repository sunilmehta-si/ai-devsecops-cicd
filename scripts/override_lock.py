"""Pin a hash-locked requirements file to the versions an overrides file names, with their hashes from PyPI.

pip-compile resolves what a tool's own pins allow; when a tool pins a dependency to a version with a security
advisory and no release of the tool allows the fix, the fix goes in an overrides file and this script writes it into
the lock. The lock is then installed with --no-deps, so pip keeps the overridden versions.

    python3 scripts/override_lock.py .github/requirements/semgrep.overrides .github/requirements/semgrep.txt
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

PIN = re.compile(r"^([A-Za-z0-9._-]+)==(\S+)\s*$")


def overrides(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        m = PIN.match(line.strip())
        if m:
            out[m.group(1).lower()] = m.group(2)
    return out


def hashes(name: str, version: str) -> list[str]:
    with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/{version}/json", timeout=30) as r:
        files = json.load(r)["urls"]
    if not files:
        raise SystemExit(f"{name}=={version}: no files on PyPI")
    return sorted(f["digests"]["sha256"] for f in files)


def block(name: str, version: str, digests: list[str], source: str, old: str = "") -> str:
    """The lock entry for name==version; the old entry's "# via" lines are kept, and the override noted."""
    lines = [f"{name}=={version} \\"] + [f"    --hash=sha256:{d} \\" for d in digests]
    lines[-1] = lines[-1].rstrip(" \\")
    lines += [l for l in old.splitlines() if l.lstrip().startswith("#") and "# overridden by" not in l]
    lines.append(f"    # overridden by {source}: a security fix the resolved pins hold back")
    return "\n".join(lines) + "\n"


def apply(lock: str, wanted: dict[str, str], get_hashes=hashes, source: str = "overrides") -> str:
    parts = re.split(r"^(?=[A-Za-z0-9._-]+==)", lock, flags=re.M)
    head, blocks = parts[0], parts[1:]
    done = set()
    for i, b in enumerate(blocks):
        name = b.split("==", 1)[0].lower()
        if name in wanted:
            blocks[i] = block(name, wanted[name], get_hashes(name, wanted[name]), source, b)
            done.add(name)
    missing = set(wanted) - done
    if missing:
        raise SystemExit(f"not in the lock, so nothing to override: {', '.join(sorted(missing))}")
    return head + "".join(blocks)


def main() -> None:
    over, lock = Path(sys.argv[1]), Path(sys.argv[2])
    lock.write_text(apply(lock.read_text(), overrides(over.read_text()), source=over.name))


if __name__ == "__main__":
    main()
