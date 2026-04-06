from __future__ import annotations

from pathlib import Path

import pytest

from support.cases import load_case_files
from support.live_runner import run_live_case
from support.matrix_builder import ensure_generated_matrices

pytestmark = pytest.mark.live_new_processing

SUITE_ROOT = Path(__file__).resolve().parents[1]
ensure_generated_matrices()
TEST_CASES = load_case_files(
    [
        SUITE_ROOT / "data" / "own_accounts_transfer" / "same_currency.json",
        SUITE_ROOT / "data" / "own_accounts_transfer" / "fx.json",
    ],
    allowed_codes={"MAKE_OWN_ACCOUNTS_TRANSFER"},
)


@pytest.mark.parametrize("case", TEST_CASES, ids=[case["name"] for case in TEST_CASES])
def test_own_accounts_transfer_live(case: dict):
    run_live_case(case)
