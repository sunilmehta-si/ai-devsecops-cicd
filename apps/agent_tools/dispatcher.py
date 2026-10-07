"""Executes agent tool calls only after policy approval. Network and disk access are simulated."""
from __future__ import annotations

from typing import Any

from apps.agent_tools.policy import PolicyDenied, ToolPolicy


def dispatch(call: dict[str, Any], policy: ToolPolicy, approved: bool = False) -> dict[str, Any]:
    tool, args = call.get("tool"), call.get("args") or {}
    if not isinstance(tool, str) or not isinstance(args, dict):
        return {"ok": False, "error": "malformed tool call"}
    try:
        policy.check_tool(tool, approved)
        if tool == "read_file":
            return {"ok": True, "result": f"read {policy.resolve_path(str(args.get('path', '')))}"}
        if tool == "write_file":
            return {"ok": True, "result": f"wrote {policy.resolve_path(str(args.get('path', '')))}"}
        if tool == "http_get":
            policy.check_url(str(args.get("url", "")))
            return {"ok": True, "result": f"fetched {args['url']}"}
    except PolicyDenied as exc:
        return {"ok": False, "error": f"denied: {exc}"}
    return {"ok": False, "error": "denied: unknown tool"}
