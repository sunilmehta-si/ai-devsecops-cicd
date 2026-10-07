"""Minimal OpenAI-style chat gateway with bearer auth, backed by a deterministic mock model."""
from __future__ import annotations

import hmac
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from apps.llm_gateway.guard import ValidationError, redact_output, validate_chat_request

MAX_BODY_BYTES = 64 * 1024


def mock_model(messages: list[dict[str, str]]) -> str:
    last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    return f"Mock model reply to: {last_user[:200]}"


def make_handler(api_key: str):
    class Handler(BaseHTTPRequestHandler):
        server_version = "gateway"
        sys_version = ""

        def _send(self, status: int, body: dict) -> None:
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _authorized(self) -> bool:
            supplied = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            return hmac.compare_digest(supplied.encode(), api_key.encode())

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/healthz":
                self._send(200, {"status": "ok"})
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/v1/chat/completions":
                return self._send(404, {"error": "not found"})
            if not self._authorized():
                return self._send(401, {"error": "unauthorized"})
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY_BYTES:
                return self._send(413, {"error": "invalid body size"})
            try:
                messages = validate_chat_request(json.loads(self.rfile.read(length)))
            except (json.JSONDecodeError, ValidationError) as exc:
                return self._send(400, {"error": str(exc)})
            reply = redact_output(mock_model(messages))
            self._send(200, {"choices": [{"message": {"role": "assistant", "content": reply}}]})

        def log_message(self, fmt: str, *args) -> None:  # never log headers or bodies
            sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

    return Handler


def main() -> None:
    api_key = os.environ.get("GATEWAY_API_KEY", "")
    if len(api_key) < 16:
        raise SystemExit("GATEWAY_API_KEY must be set (16+ characters); refusing to start without auth")
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), make_handler(api_key)).serve_forever()


if __name__ == "__main__":
    main()
