from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SUITE_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = SUITE_ROOT / "data"


def _resolve_path(path: str | Path) -> Path:
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = SUITE_ROOT / resolved
    return resolved


def validate_cases(
    cases: list[dict[str, Any]],
    *,
    source: Path | None = None,
    allowed_codes: set[str] | None = None,
) -> list[dict[str, Any]]:
    seen_names: set[str] = set()
    for case in cases:
        name = case.get("name")
        route_key = case.get("route_key")
        operation_code = ((case.get("operation") or {}).get("code"))
        if not name:
            raise ValueError(f"Each live case must define a non-empty name. source={source}")
        if name in seen_names:
            raise ValueError(f"Duplicate live case name detected: {name}. source={source}")
        if not route_key:
            raise ValueError(f"Case {name} is missing required route_key. source={source}")
        if not operation_code:
            raise ValueError(f"Case {name} is missing operation.code. source={source}")
        if allowed_codes is not None and operation_code not in allowed_codes:
            raise ValueError(
                f"Case {name} has unsupported operation.code={operation_code}. "
                f"Allowed codes: {sorted(allowed_codes)}. source={source}"
            )
        if case.get("expected_error"):
            raise ValueError(
                f"Case {name} still contains expected_error. "
                "Active new processing suite must contain only pass-backed routes."
            )
        seen_names.add(name)
    return cases


def load_case_file(path: str | Path, *, allowed_codes: set[str] | None = None) -> list[dict[str, Any]]:
    resolved = _resolve_path(path)
    with resolved.open("r", encoding="utf-8") as file:
        cases = json.load(file)
    return validate_cases(cases, source=resolved, allowed_codes=allowed_codes)


def load_case_files(
    paths: list[str | Path],
    *,
    allowed_codes: set[str] | None = None,
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for path in paths:
        cases = load_case_file(path, allowed_codes=allowed_codes)
        for case in cases:
            name = case["name"]
            if name in seen_names:
                raise ValueError(f"Duplicate live case name detected across files: {name}")
            seen_names.add(name)
            merged.append(case)
    return merged
