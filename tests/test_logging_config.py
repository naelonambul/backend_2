import os
import subprocess
import sys
from pathlib import Path


def test_application_and_uvicorn_logs_are_written_once_and_rotate(tmp_path):
    log_file = tmp_path / "app.log"
    env = os.environ.copy()
    env["LOG_FILE"] = str(log_file)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    env["DATABASE_URL"] = "sqlite:///:memory:"
    env["DB_HOST"] = ""
    script = """
import logging
import uvicorn

# Uvicorn configures its loggers before importing the application.
uvicorn.Config('app.main:app')
from app.main import app

# The app entrypoint initializes logging without a separate caller.
logging.getLogger('app.example').info('startup-configured message')
from app.core.logging_config import configure_logging

# Initializing the logging configuration twice must not duplicate records.
configure_logging()
logging.getLogger('app.example').info('application message')
logging.getLogger('uvicorn.error').warning('server message')
logging.getLogger('uvicorn.access').info(
    '%s - "%s %s HTTP/%s" %d', '127.0.0.1:1234', 'GET', '/', '1.1', 200
)

file_handler = next(
    handler for handler in logging.getLogger().handlers
    if handler.name == 'app_rotating_file'
)
file_handler.maxBytes = 1024
logging.getLogger('app.example').warning('rotation-marker-' + 'x' * 2048)
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    rotated = log_file.with_name("app.log.1").read_text(encoding="utf-8")
    assert rotated.count("startup-configured message") == 1
    assert rotated.count("application message") == 1
    assert rotated.count("server message") == 1
    assert rotated.count('GET / HTTP/1.1') == 1
    assert "rotation-marker-" in log_file.read_text(encoding="utf-8")


def test_importing_settings_does_not_modify_root_logging(tmp_path):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    script = """
import logging
root = logging.getLogger()
existing_handler = logging.StreamHandler()
root.addHandler(existing_handler)
root.setLevel(logging.ERROR)
before_handlers = list(root.handlers)
from app.core.config import settings
assert root.handlers == before_handlers
assert root.level == logging.ERROR
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_default_log_path_is_var_log_app_log(tmp_path):
    env = os.environ.copy()
    env.pop("LOG_FILE", None)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    result = subprocess.run(
        [sys.executable, "-c", "from app.core.config import settings; print(settings.LOG_FILE)"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "/var/log/app.log"
