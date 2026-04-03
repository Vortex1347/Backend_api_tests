"""
Job для синхронизации данных карты через Admin API.
Запускается отдельно, не участвует в общем цикле тестов.
"""
import os
import json
import uuid

import pytest
import requests

# Импорт данных
import data as app_data

FAILED_ACCOUNTS_OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "failed_accounts_for_sync.json")
SUCCESSFUL_ACCOUNTS_OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "successful_accounts_for_sync.json")
ADMIN_SYNC_SESSION_KEY = os.getenv("ADMIN_SESSION_KEY", app_data.ADMIN_SESSION_KEY)
FAILED_ACCOUNTS: list[str] = []
SUCCESSFUL_ACCOUNTS: list[str] = []


def register_failed_account(account_no: str):
    """Сохраняет номер счета в итоговый список упавших без дублей."""
    if account_no not in FAILED_ACCOUNTS:
        FAILED_ACCOUNTS.append(account_no)
    if account_no in SUCCESSFUL_ACCOUNTS:
        SUCCESSFUL_ACCOUNTS.remove(account_no)


def register_successful_account(account_no: str):
    """Сохраняет номер счета в итоговый список успешных, если он не падал."""
    if account_no in FAILED_ACCOUNTS:
        return
    if account_no not in SUCCESSFUL_ACCOUNTS:
        SUCCESSFUL_ACCOUNTS.append(account_no)


def write_failed_accounts_json():
    """Перезаписывает JSON-файл со списком упавших счетов текущего прогона."""
    with open(FAILED_ACCOUNTS_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(FAILED_ACCOUNTS, f, ensure_ascii=False, indent=2)


def write_successful_accounts_json():
    """Перезаписывает JSON-файл со списком успешных счетов текущего прогона."""
    with open(SUCCESSFUL_ACCOUNTS_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(SUCCESSFUL_ACCOUNTS, f, ensure_ascii=False, indent=2)


def build_admin_headers() -> dict[str, str]:
    """Собирает заголовки так же, как в Admin UI."""
    return {
        "Content-Type": "application/json",
        "device-type": "web",
        "ref-id": str(uuid.uuid4()),
        "session-key": ADMIN_SYNC_SESSION_KEY,
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36"
        ),
        "user-agent-c": "chrome",
        "accept": "*/*",
        "accept-encoding": "gzip, deflate",
        "accept-language": "ru,en-US;q=0.9,en;q=0.8,ru-RU;q=0.7",
        "connection": "keep-alive",
        "referer": f"{app_data.ADMIN_API_URL}/admin-ui/cards",
        "origin": app_data.ADMIN_API_URL,
    }


def sync_single_account(account_no: str) -> tuple[requests.Response, dict]:
    """Отправка sync cards по номеру счета через Admin API."""
    url = f"{app_data.ADMIN_API_URL}/adminApi/others/cards"
    response = requests.post(
        url,
        headers=build_admin_headers(),
        json={"accountNo": account_no},
        timeout=30.0,
    )

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    return response, payload


def get_payload_error_details(payload: dict) -> tuple[bool, str, str]:
    """Достает error из JSON-ответа Admin API."""
    error = payload.get("error")

    if error is None:
        return False, "", ""

    if isinstance(error, dict):
        return True, str(error.get("code", "") or ""), str(error.get("data", "") or "")

    return True, "", str(error)


def get_sync_cards(payload: dict) -> list:
    """Возвращает data.syncCards из JSON-ответа."""
    data = payload.get("data") or {}
    sync_cards = data.get("syncCards") or []
    return sync_cards


def count_sync_cards(sync_cards: list) -> int:
    """Считает количество карточных объектов в syncCards, даже если там вложенные списки."""
    total = 0
    for item in sync_cards:
        if isinstance(item, list):
            total += len(item)
        else:
            total += 1
    return total


def assert_sync_card_data_success(account_no: str, response: requests.Response, payload: dict):
    """Падает, если Admin API вернул прикладную ошибку или пустой результат."""
    has_error, error_code, error_data = get_payload_error_details(payload)
    sync_cards = get_sync_cards(payload)
    sync_cards_count = count_sync_cards(sync_cards)

    debug_parts = [
        f"account_no={account_no}",
        f"http_status={response.status_code}",
        f"sync_cards_count={sync_cards_count}",
    ]

    if has_error:
        debug_parts.append(f"error.code={error_code!r}")
        debug_parts.append(f"error.data={error_data!r}")

    debug_message = ", ".join(debug_parts)

    assert response.status_code == 200, f"Admin API returned non-200 response: {debug_message}"
    assert not has_error, f"Admin API returned error: {debug_message}"
    assert sync_cards_count > 0, f"Admin API returned empty syncCards: {debug_message}"


def load_accounts_from_json():
    """Загрузка счетов из JSON."""
    json_path = os.path.join(os.path.dirname(__file__), "accounts_for_sync.json")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


_ACCOUNTS_FOR_TEST = (
    load_accounts_from_json()
    if os.path.exists(os.path.join(os.path.dirname(__file__), "accounts_for_sync.json"))
    else []
)


@pytest.fixture(scope="session", autouse=True)
def persist_result_accounts_files():
    """Сохраняет файлы с успешными и упавшими счетами по завершении pytest-сессии."""
    FAILED_ACCOUNTS.clear()
    SUCCESSFUL_ACCOUNTS.clear()
    yield
    write_failed_accounts_json()
    write_successful_accounts_json()
    print(
        f"\nSaved {len(FAILED_ACCOUNTS)} failed account(s) to "
        f"{FAILED_ACCOUNTS_OUTPUT_PATH}"
    )
    print(
        f"Saved {len(SUCCESSFUL_ACCOUNTS)} successful account(s) to "
        f"{SUCCESSFUL_ACCOUNTS_OUTPUT_PATH}"
    )


@pytest.mark.parametrize("account_no", _ACCOUNTS_FOR_TEST if _ACCOUNTS_FOR_TEST else ["__no_accounts__"])
def test_sync_card_data(account_no):
    """Отправка одного запроса и проверка прикладного результата."""
    if account_no == "__no_accounts__":
        pytest.skip("Счета не загружены")

    try:
        response, payload = sync_single_account(account_no)
    except Exception:
        register_failed_account(account_no)
        raise

    has_error, error_code, error_data = get_payload_error_details(payload)
    sync_cards = get_sync_cards(payload)
    sync_cards_count = count_sync_cards(sync_cards)
    print(
        f"[{account_no}] http_status={response.status_code}, "
        f"sync_cards_count={sync_cards_count}, "
        f"has_error={has_error}, "
        f"error_code={error_code!r}, "
        f"error_data={error_data!r}"
    )
    print(f"[{account_no}] Response JSON: {payload}")

    try:
        assert_sync_card_data_success(account_no, response, payload)
    except AssertionError:
        register_failed_account(account_no)
        raise
    else:
        register_successful_account(account_no)
