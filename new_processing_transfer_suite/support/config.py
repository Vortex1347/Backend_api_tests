from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

SUITE_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(SUITE_ROOT / ".env")
load_dotenv()


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return int(value)


def live_mode_enabled() -> bool:
    return _env_flag("RUN_LIVE_NEW_PROCESSING", False)


@dataclass(frozen=True)
class AppConfig:
    run_live_new_processing: bool
    grpc_server_url: str | None
    admin_api_url: str | None
    admin_session_key: str | None
    db_host: str | None
    db_port: str | None
    db_name: str | None
    db_user: str | None
    db_password: str | None
    db_schema: str | None
    otp_code: str
    device_type: str
    user_agent: str
    session_retry_limit: int
    poll_interval_seconds: int
    balance_sync_timeout_seconds: int
    transaction_timeout_seconds: int
    grpc_options: tuple[tuple[str, int], ...]
    admin_browser_user_agent: str
    admin_browser_user_agent_c: str

    def validate_live_settings(self) -> None:
        required = {
            "GRPC_SERVER_URL": self.grpc_server_url,
            "ADMIN_API_URL": self.admin_api_url,
            "ADMIN_SESSION_KEY": self.admin_session_key,
            "DB_HOST": self.db_host,
            "DB_PORT": self.db_port,
            "DB_NAME": self.db_name,
            "DB_USER": self.db_user,
            "DB_PASSWORD": self.db_password,
            "DB_SCHEMA": self.db_schema,
        }
        missing = [name for name, value in required.items() if value is None or str(value).strip() == ""]
        if missing:
            raise RuntimeError(
                "Missing required live settings for new_processing_transfer_suite: "
                + ", ".join(missing)
            )


def get_config(*, validate_live: bool | None = None) -> AppConfig:
    config = AppConfig(
        run_live_new_processing=live_mode_enabled(),
        grpc_server_url=os.getenv("GRPC_SERVER_URL"),
        admin_api_url=os.getenv("ADMIN_API_URL"),
        admin_session_key=os.getenv("ADMIN_SESSION_KEY"),
        db_host=os.getenv("DB_HOST"),
        db_port=os.getenv("DB_PORT"),
        db_name=os.getenv("DB_NAME"),
        db_user=os.getenv("DB_USER"),
        db_password=os.getenv("DB_PASSWORD"),
        db_schema=os.getenv("DB_SCHEMA"),
        otp_code=os.getenv("OTP_CODE", "111111"),
        device_type=os.getenv("DEVICE_TYPE", "ios"),
        user_agent=os.getenv("USER_AGENT", "12; iPhone12MaxProDan"),
        session_retry_limit=_env_int("SESSION_RETRY_LIMIT", 10),
        poll_interval_seconds=_env_int("POLL_INTERVAL_SECONDS", 2),
        balance_sync_timeout_seconds=_env_int("BALANCE_SYNC_TIMEOUT_SECONDS", 90),
        transaction_timeout_seconds=_env_int("TRANSACTION_TIMEOUT_SECONDS", 90),
        grpc_options=(
            ("grpc.enable_http_proxy", 0),
            ("grpc.keepalive_timeout_ms", 10000),
        ),
        admin_browser_user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36"
        ),
        admin_browser_user_agent_c="chrome",
    )

    should_validate = config.run_live_new_processing if validate_live is None else validate_live
    if should_validate:
        config.validate_live_settings()

    return config
