from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping

SUITE_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_FILE = SUITE_ROOT / "contracts" / "main.js"


@dataclass(frozen=True)
class ContractField:
    name: str
    required: bool


def _extract_method_body_params_block(method_name: str, content: str) -> str:
    marker = f"{method_name}:"
    method_pos = content.find(marker)
    if method_pos == -1:
        raise ValueError(f"Method {method_name} was not found in {CONTRACT_FILE}")

    params_pos = content.find("bodyParams", method_pos)
    if params_pos == -1:
        raise ValueError(f"bodyParams block for {method_name} was not found in {CONTRACT_FILE}")

    list_start = content.find("[", params_pos)
    if list_start == -1:
        raise ValueError(f"bodyParams list start for {method_name} was not found in {CONTRACT_FILE}")

    depth = 0
    for index in range(list_start, len(content)):
        char = content[index]
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return content[list_start : index + 1]

    raise ValueError(f"Could not extract bodyParams list for {method_name} from {CONTRACT_FILE}")


@lru_cache(maxsize=None)
def get_contract_fields(method_name: str) -> list[ContractField]:
    content = CONTRACT_FILE.read_text(encoding="utf-8")
    block = _extract_method_body_params_block(method_name, content)
    matches = re.findall(
        r'\{\s*name:\s*"([^"]+)"[^}]*required:\s*(true|false)[^}]*\}',
        block,
        flags=re.MULTILINE,
    )
    if not matches:
        raise ValueError(f"No contract fields parsed for {method_name} from {CONTRACT_FILE}")

    deduped: dict[str, ContractField] = {}
    for name, required in matches:
        if name not in deduped:
            deduped[name] = ContractField(name=name, required=(required == "true"))

    return list(deduped.values())


def validate_payload_against_contract(method_name: str, payload: Mapping[str, object]) -> None:
    fields = get_contract_fields(method_name)
    allowed_fields = {field.name for field in fields}
    required_fields = {field.name for field in fields if field.required}
    payload_fields = set(payload.keys())

    missing_required = sorted(required_fields - payload_fields)
    unexpected_fields = sorted(payload_fields - allowed_fields)

    if missing_required:
        raise AssertionError(
            f"{method_name}: payload is missing required fields from contracts/main.js: {missing_required}"
        )
    if unexpected_fields:
        raise AssertionError(
            f"{method_name}: payload contains fields absent from contracts/main.js: {unexpected_fields}"
        )
