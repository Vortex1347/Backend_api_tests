from __future__ import annotations

from pathlib import Path

import pytest

from support.cases import load_case_file
from support.live_runner import run_live_case
from support.matrix_builder import ensure_generated_matrices

pytestmark = pytest.mark.live_new_processing

SUITE_ROOT = Path(__file__).resolve().parents[1]
ensure_generated_matrices()
TEST_CASES = load_case_file(
    SUITE_ROOT / "data" / "qr_payment" / "static_qr.json",
    allowed_codes={"MAKE_QR_PAYMENT"},
)


@pytest.mark.parametrize("case", TEST_CASES, ids=[case["name"] for case in TEST_CASES])
def test_qr_payment_live(case: dict):
    run_live_case(case)
