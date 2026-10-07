#!/usr/bin/env python3
"""Replays the AI security corpus against the gateway guard and agent policy; fails the build on regressions."""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apps.agent_tools.dispatcher import dispatch  # noqa: E402
from apps.agent_tools.policy import ToolPolicy  # noqa: E402
from apps.llm_gateway.guard import ValidationError, redact_output, validate_chat_request  # noqa: E402

CORPUS = ROOT / "tests" / "ai_security" / "corpus.json"
REPORT = ROOT / "reports" / "ai-security.json"

# Synthetic secrets are assembled here so the corpus file stays free of secret-shaped strings.
SYNTH = {"aws": "AKIA" + "ABCDEFGHIJKLMNOP", "github": "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"}


def run_case(case: dict, policy: ToolPolicy) -> tuple[str, str]:
    kind = case["kind"]
    if kind == "tool_call":
        result = dispatch(case["call"], policy)
        return ("allow" if result["ok"] else "deny"), json.dumps(result)[:120]
    if kind == "gateway_input":
        if "repeat" in case:
            messages = [{"role": "user", "content": case["repeat"]["text"] * case["repeat"]["times"]}]
        elif "flood" in case:
            messages = [{"role": "user", "content": "hi"}] * case["flood"]
        else:
            messages = case["messages"]
        try:
            validate_chat_request({"messages": messages})
            return "accept", "accepted"
        except ValidationError as exc:
            return "reject", str(exc)
    if kind == "output_leak":
        secret = SYNTH[case["synth_secret"]]
        cleaned = redact_output(f"the credential is {secret} ok")
        return ("redact" if secret not in cleaned else "leak"), "secret removed" if secret not in cleaned else "SECRET LEAKED"
    raise ValueError(f"unknown kind {kind}")


def main() -> int:
    cases = json.loads(CORPUS.read_text())["cases"]
    policy = ToolPolicy()
    results, failed = [], 0
    for case in cases:
        actual, detail = run_case(case, policy)
        passed = actual == case["expect"]
        failed += not passed
        results.append({"id": case["id"], "owasp": case["owasp"], "title": case["title"],
                        "expected": case["expect"], "actual": actual, "passed": passed})
        print(f"{'PASS' if passed else 'FAIL'} {case['id']} [{case['owasp']}] {case['title']} -> {actual}")
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps({"total": len(cases), "failed": failed, "results": results}, indent=2))
    print(f"{len(cases) - failed}/{len(cases)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
