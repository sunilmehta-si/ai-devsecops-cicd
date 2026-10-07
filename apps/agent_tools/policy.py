"""Deny-by-default permission policy for agent tool calls."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from urllib.parse import urlparse


class PolicyDenied(PermissionError):
    """Raised when a tool call violates policy."""


@dataclass(frozen=True)
class ToolPolicy:
    workspace: str = "/workspace"
    allowed_tools: frozenset[str] = frozenset({"read_file", "http_get"})
    approval_required: frozenset[str] = frozenset({"write_file"})
    allowed_hosts: frozenset[str] = frozenset({"api.github.com"})
    blocked_names: tuple[str, ...] = field(default=(".env", "id_rsa", "credentials", ".aws", ".kube", ".git"))

    def check_tool(self, tool: str, approved: bool = False) -> None:
        if tool in self.approval_required:
            if not approved:
                raise PolicyDenied(f"{tool} requires human approval")
            return
        if tool not in self.allowed_tools:
            raise PolicyDenied(f"tool {tool!r} is not allowed")

    def resolve_path(self, requested: str) -> str:
        if "\x00" in requested:
            raise PolicyDenied("invalid path")
        root = PurePosixPath(self.workspace)
        candidate = PurePosixPath(requested)
        parts: list[str] = []
        for part in (candidate if candidate.is_absolute() else root / candidate).parts[1:]:
            if part == "..":
                if parts:
                    parts.pop()
            elif part != ".":
                parts.append(part)
        resolved = PurePosixPath("/", *parts)
        if resolved != root and root not in resolved.parents:
            raise PolicyDenied("path escapes the workspace")
        if any(part in self.blocked_names or part.startswith(".env") for part in resolved.parts):
            raise PolicyDenied("path targets a protected file")
        return str(resolved)

    def check_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise PolicyDenied("only https is allowed")
        if parsed.username or parsed.password:
            raise PolicyDenied("credentials in URLs are not allowed")
        if parsed.hostname not in self.allowed_hosts:
            raise PolicyDenied(f"host {parsed.hostname!r} is not allowlisted")
