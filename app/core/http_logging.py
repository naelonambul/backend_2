import json
import logging
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from starlette.datastructures import URL
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_MAX_LOGGED_BODY_BYTES = 64 * 1024
_REDACTED = "[REDACTED]"
_SENSITIVE_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "client_secret",
    "code",
    "cookie",
    "credential",
    "password",
    "refresh_token",
    "secret",
    "sessionid",
    "signature",
    "state",
    "token",
}
_NORMALIZED_SENSITIVE_KEYS = {
    re.sub(r"[^a-z0-9]", "", key.lower()) for key in _SENSITIVE_KEYS
}
_URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+")
_TEXT_CONTENT_TYPES = {
    "application/json",
    "application/xml",
    "application/x-www-form-urlencoded",
}


def _is_sensitive_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", key.lower())
    return normalized in _NORMALIZED_SENSITIVE_KEYS or any(
        marker in normalized
        for marker in (
            "password",
            "secret",
            "token",
            "authorization",
            "cookie",
            "signature",
            "credential",
        )
    )


def _redact_url(url: str) -> str:
    parts = urlsplit(url)
    if not parts.query:
        return url

    query = [
        (key, _REDACTED if _is_sensitive_key(key) else value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
    ]
    return urlunsplit(parts._replace(query=urlencode(query)))


def _redact_urls_in_text(value: str) -> str:
    return _URL_PATTERN.sub(lambda match: _redact_url(match.group(0)), value)


def _redact_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _REDACTED if _is_sensitive_key(str(key)) else _redact_json(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_json(item) for item in value]
    if isinstance(value, str):
        return _redact_urls_in_text(value)
    return value


def _is_text_content_type(content_type: str) -> bool:
    media_type = content_type.split(";", maxsplit=1)[0].strip().lower()
    return (
        media_type.startswith("text/")
        or media_type in _TEXT_CONTENT_TYPES
        or media_type.endswith("+json")
        or media_type.endswith("+xml")
    )


def _response_body_for_log(
    body: bytearray,
    body_size: int,
    content_type: str,
    content_encoding: str,
    exceeded_limit: bool,
) -> Any:
    if body_size == 0:
        return None
    if exceeded_limit:
        return f"[omitted: response body exceeded {_MAX_LOGGED_BODY_BYTES} bytes]"
    if not _is_text_content_type(content_type):
        return f"[omitted: non-text response; {body_size} bytes]"
    if content_encoding and content_encoding.lower() != "identity":
        return f"[omitted: encoded response; {body_size} bytes]"

    text = body.decode("utf-8", errors="replace")
    media_type = content_type.split(";", maxsplit=1)[0].strip().lower()
    if media_type == "application/json" or media_type.endswith("+json"):
        try:
            return _redact_json(json.loads(text))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    return _redact_urls_in_text(text)


class HttpAccessLogMiddleware:
    """Log HTTP request metadata and a safe, bounded view of each response body."""

    def __init__(self, app: ASGIApp):
        self.app = app
        self.logger = logging.getLogger("app.http")

    def __getattr__(self, name: str) -> Any:
        # Preserve FastAPI attributes such as `openapi` and `dependency_overrides`.
        return getattr(self.app, name)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_status = 500
        content_type = ""
        content_encoding = ""
        body = bytearray()
        body_size = 0
        exceeded_limit = False
        client = scope.get("client")
        client_ip = str(client[0]) if client else "unknown"
        request_url = _redact_url(str(URL(scope=scope)))

        async def send_logged(message: Message) -> None:
            nonlocal response_status, content_type, content_encoding
            nonlocal body_size, exceeded_limit

            if message["type"] == "http.response.start":
                response_status = message["status"]
                headers = {
                    key.lower(): value for key, value in message.get("headers", [])
                }
                content_type = headers.get(b"content-type", b"").decode(
                    "latin-1"
                )
                content_encoding = headers.get(b"content-encoding", b"").decode(
                    "latin-1"
                )
            elif message["type"] == "http.response.body":
                chunk = message.get("body", b"")
                body_size += len(chunk)
                if not exceeded_limit:
                    if len(body) + len(chunk) <= _MAX_LOGGED_BODY_BYTES:
                        body.extend(chunk)
                    else:
                        exceeded_limit = True
                        body.clear()

            await send(message)

        try:
            await self.app(scope, receive, send_logged)
        finally:
            entry = {
                "method": scope.get("method", ""),
                "url": request_url,
                "client_ip": client_ip,
                "status": response_status,
                "status_code": response_status,
                "response_body_bytes": body_size,
                "response_body": _response_body_for_log(
                    body,
                    body_size,
                    content_type,
                    content_encoding,
                    exceeded_limit,
                ),
            }
            self.logger.info(
                "http_response %s",
                json.dumps(entry, ensure_ascii=False, separators=(",", ":")),
            )
