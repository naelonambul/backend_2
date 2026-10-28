import json
import logging
from urllib.parse import parse_qs, urlsplit

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import Response, StreamingResponse

from app.core.http_logging import HttpAccessLogMiddleware
from app.main import app


def _last_http_entry(caplog):
    record = next(item for item in reversed(caplog.records) if item.name == "app.http")
    return json.loads(record.getMessage().removeprefix("http_response "))


def test_http_log_records_request_and_redacted_response(caplog):
    caplog.set_level(logging.INFO, logger="app.http")

    with TestClient(app, client=("203.0.113.17", 50000)) as client:
        response = client.post("/user/kakao/state?access_token=query-secret")

    assert response.status_code == 200
    records = [item for item in caplog.records if item.name == "app.http"]
    assert len(records) == 1
    record = records[0]

    entry = json.loads(record.getMessage().removeprefix("http_response "))
    logged_url = urlsplit(entry["url"])

    assert entry["method"] == "POST"
    assert logged_url.path == "/user/kakao/state"
    assert parse_qs(logged_url.query)["access_token"] == ["[REDACTED]"]
    assert entry["client_ip"] == "203.0.113.17"
    assert entry["status_code"] == 200
    assert entry["response_body"] == {"state": "[REDACTED]"}
    assert response.json()["state"] != "[REDACTED]"
    assert "query-secret" not in record.getMessage()


def test_http_log_redacts_signed_url_query_values(caplog):
    caplog.set_level(logging.INFO, logger="app.http")
    upload_url = (
        "https://storage.example/upload?X-Amz-Credential=private-credential"
        "&X-Amz-Signature=private-signature&X-Amz-Expires=300"
    )
    api = FastAPI()

    @api.get("/upload-url")
    async def get_upload_url():
        return {"upload_url": upload_url}

    with TestClient(HttpAccessLogMiddleware(api)) as client:
        response = client.get("/upload-url")

    entry = _last_http_entry(caplog)
    assert response.json()["upload_url"] == upload_url
    logged_url = entry["response_body"]["upload_url"]
    query = parse_qs(urlsplit(logged_url).query)
    assert query["X-Amz-Credential"] == ["[REDACTED]"]
    assert query["X-Amz-Signature"] == ["[REDACTED]"]
    assert query["X-Amz-Expires"] == ["300"]


def test_http_log_captures_streamed_body_without_changing_response(caplog):
    caplog.set_level(logging.INFO, logger="app.http")
    api = FastAPI()

    @api.get("/stream")
    async def stream():
        async def body():
            yield b'{"part":'
            yield b'"one","password":"stream-secret"}'

        return StreamingResponse(body(), media_type="application/json")

    with TestClient(HttpAccessLogMiddleware(api)) as client:
        response = client.get("/stream")

    entry = _last_http_entry(caplog)
    assert response.content == b'{"part":"one","password":"stream-secret"}'
    assert entry["response_body"] == {
        "part": "one",
        "password": "[REDACTED]",
    }


def test_http_log_limits_large_body_and_still_returns_it(caplog):
    caplog.set_level(logging.INFO, logger="app.http")
    large_body = b"x" * (64 * 1024 + 1)
    api = FastAPI()

    @api.get("/large")
    async def large():
        return Response(content=large_body, media_type="text/plain")

    with TestClient(HttpAccessLogMiddleware(api)) as client:
        response = client.get("/large")

    entry = _last_http_entry(caplog)
    assert response.content == large_body
    assert entry["response_body_bytes"] == len(large_body)
    assert entry["response_body"] == "[omitted: response body exceeded 65536 bytes]"


def test_http_log_captures_unhandled_500_response_body(caplog):
    caplog.set_level(logging.INFO, logger="app.http")
    api = FastAPI()

    @api.get("/error")
    async def error():
        raise RuntimeError("request failed")

    with TestClient(
        HttpAccessLogMiddleware(api), raise_server_exceptions=False
    ) as client:
        response = client.get("/error")

    entry = _last_http_entry(caplog)
    assert response.status_code == 500
    assert entry["status_code"] == 500
    assert entry["response_body"] == "Internal Server Error"
