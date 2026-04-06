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
        SUITE_ROOT / "data" / "bank_client_transfer" / "card_to_card.json",
        SUITE_ROOT / "data" / "bank_client_transfer" / "account_to_card.json",
        SUITE_ROOT / "data" / "bank_client_transfer" / "card_to_account.json",
        SUITE_ROOT / "data" / "bank_client_transfer" / "account_to_account.json",
    ],
    allowed_codes={"MAKE_BANK_CLIENT_TRANSFER"},
)


@pytest.mark.parametrize("case", TEST_CASES, ids=[case["name"] for case in TEST_CASES])
def test_bank_client_transfer_live(case: dict):
    run_live_case(case)
