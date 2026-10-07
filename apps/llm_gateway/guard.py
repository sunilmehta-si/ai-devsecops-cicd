"""Request validation and output redaction for the sample LLM gateway."""
from __future__ import annotations

import re
from typing import Any

MAX_MESSAGES = 32
MAX_CHARS_PER_MESSAGE = 4000
ALLOWED_ROLES = {"system", "user", "assistant"}
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Output redaction: credentials must never leave the gateway, even if a model emits one.
OUTPUT_SECRETS = [
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_\-]{20,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]
REDACTION = "[REDACTED]"


class ValidationError(ValueError):
    """Raised when a chat request does not meet the gateway contract."""


def validate_chat_request(payload: Any) -> list[dict[str, str]]:
    if not isinstance(payload, dict):
        raise ValidationError("body must be a JSON object")
    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ValidationError("messages must be a non-empty list")
    if len(messages) > MAX_MESSAGES:
        raise ValidationError(f"at most {MAX_MESSAGES} messages are allowed")
    clean = []
    for item in messages:
        if not isinstance(item, dict):
            raise ValidationError("each message must be an object")
        role, content = item.get("role"), item.get("content")
        if role not in ALLOWED_ROLES:
            raise ValidationError("unsupported role")
        if not isinstance(content, str) or not content.strip():
            raise ValidationError("content must be a non-empty string")
        if len(content) > MAX_CHARS_PER_MESSAGE:
            raise ValidationError("message too long")
        clean.append({"role": role, "content": CONTROL_CHARS.sub("", content)})
    return clean


def redact_output(text: str) -> str:
    for pattern in OUTPUT_SECRETS:
        text = pattern.sub(REDACTION, text)
    return text
