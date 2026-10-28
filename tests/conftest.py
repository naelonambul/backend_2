"""Keep pytest app imports isolated from developers' local .env database."""

import logging
import os
import tempfile
from pathlib import Path


_database_environment = (
    "DATABASE_URL",
    "DB_HOST",
    "DB_PORT",
    "DB_USER",
    "DB_PASSWORD",
    "DB_NAME",
)
_original_environment = {
    key: os.environ.get(key) for key in _database_environment
}
_original_log_file = os.environ.get("LOG_FILE")
_original_directory = Path.cwd()
_settings_directory = tempfile.TemporaryDirectory(prefix="pytest-settings-")

try:
    os.chdir(_settings_directory.name)
    os.environ.update(
        {
            "DATABASE_URL": "sqlite:///:memory:",
            "DB_HOST": "",
            "DB_PORT": "3306",
            "DB_USER": "",
            "DB_PASSWORD": "",
            "DB_NAME": "",
            "LOG_FILE": str(Path(_settings_directory.name) / "app.log"),
        }
    )

    # Import before pytest imports application modules in individual test files.
    from app.main import app as _test_app  # noqa: F401
finally:
    os.chdir(_original_directory)
    for key, value in _original_environment.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    if _original_log_file is None:
        os.environ.pop("LOG_FILE", None)
    else:
        os.environ["LOG_FILE"] = _original_log_file


def pytest_unconfigure(config):
    for handler in logging.getLogger().handlers:
        if handler.name == "app_rotating_file":
            handler.close()
