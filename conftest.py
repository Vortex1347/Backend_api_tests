from __future__ import annotations

from collections import defaultdict
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Mapping

import grpc
import pytest

from data import DEVICE_TYPE, GRPC_OPTIONS, GRPC_SERVER_URL, OTP_CODE, SESSION_KEY, USER_AGENT

REPO_ROOT = Path(__file__).resolve().parent
PROTO_PATH = REPO_ROOT / "protofiles"

if str(PROTO_PATH) not in sys.path:
    sys.path.insert(0, str(PROTO_PATH))

import protofile_pb2 as webTransferApi_pb2
import protofile_pb2_grpc as webTransferApi_pb2_grpc


ROUTE_SUMMARY: dict[str, dict[str, int]] = defaultdict(
    lambda: {'passed': 0, 'skipped': 0, 'failed': 0, 'xfailed': 0}
)


def create_metadata(
    session_key: str = SESSION_KEY,
    device_type: str = DEVICE_TYPE,
    user_agent: str = USER_AGENT,
    ref_id: str | None = None,
    extra_headers: Mapping[str, Any] | None = None,
) -> tuple[tuple[str, str], ...]:
    metadata: list[tuple[str, str]] = [
        ("refid", ref_id or str(uuid.uuid4())),
        ("sessionkey", str(session_key)),
        ("device-type", str(device_type)),
        ("user-agent-c", str(user_agent)),
    ]
    if extra_headers:
        metadata.extend((str(key), str(value)) for key, value in extra_headers.items() if value is not None)
    return tuple(metadata)


def make_grpc_request(
    code: str,
    data: Mapping[str, Any] | str | None,
    metadata: tuple[tuple[str, str], ...] | None = None,
    server_url: str = GRPC_SERVER_URL,
    options: list[tuple[str, Any]] | None = None,
):
    request_data = data if isinstance(data, str) else json.dumps(data or {}, ensure_ascii=False, default=str)
    request = webTransferApi_pb2.IncomingWebTransfer(code=code, data=request_data)

    with grpc.secure_channel(
        server_url,
        grpc.ssl_channel_credentials(),
        options=options or GRPC_OPTIONS,
    ) as channel:
        client = webTransferApi_pb2_grpc.WebTransferApiStub(channel)
        return client.makeWebTransfer(request, metadata=metadata or create_metadata())


def assert_success(response: Any, step_name: str = "gRPC request") -> Any:
    if getattr(response, "success", False):
        return response

    error = getattr(response, "error", None)
    error_code = getattr(error, "code", "") or "UNKNOWN"
    error_data = getattr(error, "data", "") or ""
    response_data = getattr(response, "data", "") or ""
    raise AssertionError(
        f"{step_name} failed: error_code={error_code}, error_data={error_data}, response_data={response_data}"
    )


def confirm_operation(
    operation_id: str,
    metadata: tuple[tuple[str, str], ...] | None = None,
    otp: str = OTP_CODE,
):
    if metadata:
        metadata_map = dict(metadata)
        extra_headers = {
            key: value
            for key, value in metadata_map.items()
            if key not in {"refid", "sessionkey", "device-type", "user-agent-c"}
        }
        metadata = create_metadata(
            session_key=metadata_map.get("sessionkey", SESSION_KEY),
            device_type=metadata_map.get("device-type", DEVICE_TYPE),
            user_agent=metadata_map.get("user-agent-c", USER_AGENT),
            extra_headers=extra_headers,
        )

    confirm_data = {
        "operationId": operation_id,
        "otp": otp,
    }
    return make_grpc_request("CONFIRM_TRANSFER", confirm_data, metadata=metadata or create_metadata())


__all__ = [
    "assert_success",
    "confirm_operation",
    "create_metadata",
    "make_grpc_request",
    "webTransferApi_pb2",
    "webTransferApi_pb2_grpc",
]


def _extract_route_key(item) -> str | None:
    callspec = getattr(item, 'callspec', None)
    if callspec is None:
        return None
    case = callspec.params.get('case')
    if not isinstance(case, dict):
        return None
    return case.get('route_key')


def pytest_runtest_makereport(item, call):
    if call.when != 'call':
        return

    route_key = _extract_route_key(item)
    if not route_key:
        return

    outcome = 'failed'
    excinfo = call.excinfo
    if excinfo is None:
        outcome = 'passed'
    elif excinfo.errisinstance(pytest.skip.Exception):
        if getattr(excinfo.value, 'allow_module_level', False) and hasattr(excinfo.value, 'msg'):
            outcome = 'skipped'
        elif getattr(excinfo.value, 'msg', '').startswith('xfail'):
            outcome = 'xfailed'
        else:
            outcome = 'skipped'
    elif excinfo.errisinstance(pytest.xfail.Exception):
        outcome = 'xfailed'

    ROUTE_SUMMARY[route_key][outcome] += 1


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if not ROUTE_SUMMARY:
        return

    terminalreporter.write_sep('-', 'Live Route Summary')
    for route_key in sorted(ROUTE_SUMMARY):
        counters = ROUTE_SUMMARY[route_key]
        terminalreporter.write_line(
            f"{route_key} -> "
            f"passed={counters['passed']}, "
            f"skipped={counters['skipped']}, "
            f"failed={counters['failed']}, "
            f"xfailed={counters['xfailed']}"
        )
