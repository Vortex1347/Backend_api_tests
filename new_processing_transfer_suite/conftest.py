from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path

import pytest

SUITE_ROOT = Path(__file__).resolve().parent
PROTO_DIR = SUITE_ROOT / "proto"

for path in (SUITE_ROOT, PROTO_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

ROUTE_SUMMARY: dict[str, dict[str, int]] = defaultdict(
    lambda: {"passed": 0, "skipped": 0, "failed": 0, "xfailed": 0}
)


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live_new_processing: live tests for isolated new processing transfer suite",
    )


def pytest_collection_modifyitems(config, items):
    if os.getenv("RUN_LIVE_NEW_PROCESSING") == "1":
        return

    skip_marker = pytest.mark.skip(
        reason="Set RUN_LIVE_NEW_PROCESSING=1 to run the isolated live suite"
    )
    for item in items:
        if item.get_closest_marker("live_new_processing"):
            item.add_marker(skip_marker)


def _extract_route_key(item) -> str | None:
    callspec = getattr(item, "callspec", None)
    if callspec is None:
        return None

    case = callspec.params.get("case")
    if not isinstance(case, dict):
        return None

    return case.get("route_key")


def pytest_runtest_makereport(item, call):
    if call.when != "call":
        return

    route_key = _extract_route_key(item)
    if not route_key:
        return

    outcome = "failed"
    excinfo = call.excinfo
    if excinfo is None:
        outcome = "passed"
    elif excinfo.errisinstance(pytest.skip.Exception):
        if getattr(excinfo.value, "msg", "").startswith("xfail"):
            outcome = "xfailed"
        else:
            outcome = "skipped"
    elif excinfo.errisinstance(pytest.xfail.Exception):
        outcome = "xfailed"

    ROUTE_SUMMARY[route_key][outcome] += 1


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if not ROUTE_SUMMARY:
        return

    terminalreporter.write_sep("-", "New Processing Route Summary")
    for route_key in sorted(ROUTE_SUMMARY):
        counters = ROUTE_SUMMARY[route_key]
        terminalreporter.write_line(
            f"{route_key} -> "
            f"passed={counters['passed']}, "
            f"skipped={counters['skipped']}, "
            f"failed={counters['failed']}, "
            f"xfailed={counters['xfailed']}"
        )
