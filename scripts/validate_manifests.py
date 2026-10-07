#!/usr/bin/env python3
"""Offline check that Kubernetes manifests satisfy the same rules the Kyverno policies enforce at admission.

This is a fast shift-left mirror for pull requests; Kyverno remains the enforcement point in the cluster.
"""
from __future__ import annotations

import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
REGISTRY_PREFIX = "ghcr.io/sunilmehta-si/"
WORKLOAD_KINDS = {"Pod", "Deployment", "StatefulSet", "DaemonSet", "Job"}


def pod_spec(doc: dict) -> dict | None:
    if doc.get("kind") == "Pod":
        return doc.get("spec")
    if doc.get("kind") in WORKLOAD_KINDS:
        return ((doc.get("spec") or {}).get("template") or {}).get("spec")
    return None


def check_workload(doc: dict) -> list[str]:
    spec = pod_spec(doc)
    if spec is None:
        return []
    name = f"{doc['kind']}/{doc['metadata']['name']}"
    problems = []
    if not (spec.get("securityContext") or {}).get("runAsNonRoot"):
        problems.append(f"{name}: pod securityContext.runAsNonRoot must be true")
    for key in ("hostNetwork", "hostPID", "hostIPC"):
        if spec.get(key):
            problems.append(f"{name}: {key} is not allowed")
    for c in spec.get("containers", []):
        cname, sc = f"{name}/{c['name']}", c.get("securityContext") or {}
        image = c.get("image", "")
        if not image.startswith(REGISTRY_PREFIX):
            problems.append(f"{cname}: image must come from {REGISTRY_PREFIX}")
        if image.endswith(":latest") or (":" not in image.rsplit("/", 1)[-1] and "@" not in image):
            problems.append(f"{cname}: image must use an immutable tag or digest, not latest")
        if sc.get("privileged") is not False:
            problems.append(f"{cname}: privileged must be explicitly false")
        if sc.get("allowPrivilegeEscalation") is not False:
            problems.append(f"{cname}: allowPrivilegeEscalation must be false")
        if sc.get("readOnlyRootFilesystem") is not True:
            problems.append(f"{cname}: readOnlyRootFilesystem must be true")
        if "ALL" not in ((sc.get("capabilities") or {}).get("drop") or []):
            problems.append(f"{cname}: capabilities must drop ALL")
        res = c.get("resources") or {}
        if not (res.get("requests") or {}).get("cpu") or not (res.get("requests") or {}).get("memory"):
            problems.append(f"{cname}: cpu and memory requests are required")
        if not (res.get("limits") or {}).get("cpu") or not (res.get("limits") or {}).get("memory"):
            problems.append(f"{cname}: cpu and memory limits are required")
    return problems


def main(argv: list[str]) -> int:
    base = pathlib.Path(argv[0]) if argv else ROOT / "deploy" / "base"
    docs = [d for f in sorted(base.glob("*.yaml")) for d in yaml.safe_load_all(f.read_text()) if d]
    workloads = [d for d in docs if pod_spec(d) is not None]
    if not workloads:
        print(f"no workloads found under {base}", file=sys.stderr)
        return 1
    problems = [p for d in workloads for p in check_workload(d)]
    for problem in problems:
        print(problem, file=sys.stderr)
    print(f"Validated {len(workloads)} workload(s): {'FAILED' if problems else 'ok'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
