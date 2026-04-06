from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any, Mapping

from support.config import get_config

PROTO_DIR = Path(__file__).resolve().parents[1] / "proto"
PROTO_DIR_STR = str(PROTO_DIR)
if PROTO_DIR_STR not in sys.path:
    sys.path.insert(0, PROTO_DIR_STR)


def _load_grpc_modules():
    import grpc
    import protofile_pb2 as web_transfer_api_pb2
    import protofile_pb2_grpc as web_transfer_api_pb2_grpc

    return grpc, web_transfer_api_pb2, web_transfer_api_pb2_grpc


def create_metadata(
    *,
    session_key: str,
    device_type: str | None = None,
    user_agent: str | None = None,
    ref_id: str | None = None,
    extra_headers: Mapping[str, Any] | None = None,
) -> tuple[tuple[str, str], ...]:
    config = get_config(validate_live=False)
    metadata: list[tuple[str, str]] = [
        ("refid", ref_id or str(uuid.uuid4())),
        ("sessionkey", str(session_key)),
        ("device-type", str(device_type or config.device_type)),
        ("user-agent-c", str(user_agent or config.user_agent)),
    ]
    if extra_headers:
        metadata.extend(
            (str(key), str(value))
            for key, value in extra_headers.items()
            if value is not None
        )
    return tuple(metadata)


def make_grpc_request(
    code: str,
    data: Mapping[str, Any] | str | None,
    metadata: tuple[tuple[str, str], ...] | None = None,
    server_url: str | None = None,
    options: tuple[tuple[str, int], ...] | None = None,
):
    config = get_config(validate_live=True)
    grpc, web_transfer_api_pb2, web_transfer_api_pb2_grpc = _load_grpc_modules()

    request_data = data if isinstance(data, str) else json.dumps(data or {}, ensure_ascii=False, default=str)
    request = web_transfer_api_pb2.IncomingWebTransfer(code=code, data=request_data)
    target_server = server_url or config.grpc_server_url
    target_options = list(options or config.grpc_options)

    with grpc.secure_channel(
        target_server,
        grpc.ssl_channel_credentials(),
        options=target_options,
    ) as channel:
        client = web_transfer_api_pb2_grpc.WebTransferApiStub(channel)
        return client.makeWebTransfer(request, metadata=metadata)


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
    *,
    metadata: tuple[tuple[str, str], ...],
    otp: str | None = None,
):
    config = get_config(validate_live=True)
    metadata_map = dict(metadata)
    extra_headers = {
        key: value
        for key, value in metadata_map.items()
        if key not in {"refid", "sessionkey", "device-type", "user-agent-c"}
    }
    normalized_metadata = create_metadata(
        session_key=metadata_map["sessionkey"],
        device_type=metadata_map.get("device-type", config.device_type),
        user_agent=metadata_map.get("user-agent-c", config.user_agent),
        extra_headers=extra_headers,
    )
    confirm_data = {
        "operationId": operation_id,
        "otp": otp or config.otp_code,
    }
    return make_grpc_request("CONFIRM_TRANSFER", confirm_data, metadata=normalized_metadata)
