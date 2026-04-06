from __future__ import annotations

import json
import time
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest

from support.admin_api import sync_account_view
from support.config import get_config
from support.contracts import validate_payload_against_contract
from support.database import DataCollector, DatabaseConfig
from support.grpc_client import assert_success, confirm_operation, create_metadata, make_grpc_request

COMMON_CREATE_SKIP_ERROR_CODES = {
    "INVALID_SESSION_KEY",
    "NOT_ENOUGH_FUNDS",
    "INSUFFICIENT_FUNDS",
    "AMOUNT_EXCEEDS_BALANCE",
    "SP_ERROR_TRY_AGAIN_LATER",
}

SENTINEL_TOMORROW = "__TOMORROW__"
SENTINEL_NEXT_BUSINESS_DAY = "__NEXT_BUSINESS_DAY__"


def _digits_only(value: str | None) -> str:
    return "".join(char for char in value or "" if char.isdigit())


def _extract_visible_pan_edges(masked_pan: str | None) -> tuple[str, str]:
    prepared = "".join(char for char in masked_pan or "" if char.isdigit() or char == "*")

    prefix = []
    for char in prepared:
        if char.isdigit():
            prefix.append(char)
            continue
        break

    suffix = []
    for char in reversed(prepared):
        if char.isdigit():
            suffix.append(char)
            continue
        break

    return "".join(prefix), "".join(reversed(suffix))


def _pan_hint_matches(masked_pan: str | None, hint: str | None) -> bool:
    masked_digits = _digits_only(masked_pan)
    hint_digits = _digits_only(hint)
    if not masked_digits or not hint_digits:
        return False

    prefix, suffix = _extract_visible_pan_edges(masked_pan)
    if prefix and not hint_digits.startswith(prefix):
        return False
    if suffix and not hint_digits.endswith(suffix):
        return False

    if "*" not in (masked_pan or ""):
        return masked_digits == hint_digits
    return True


def _format_accounts(accounts: list[dict[str, Any]]) -> str:
    return "; ".join(
        (
            f"id={account['id']}, account_no={account['account_no']}, ccy={account['ccy']}, "
            f"processor={account['processor']}, account_kind={account['account_kind']}, "
            f"card_system={account['card_system']}, is_default={account['is_default']}, "
            f"ipc_card_pan={account['ipc_card_pan']}"
        )
        for account in accounts
    )


def _parse_decimal(value: Decimal | str | int | float | None) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _as_status_set(value: str | list[str] | tuple[str, ...] | None, *, default: str) -> set[str]:
    if value is None:
        return {default}
    if isinstance(value, str):
        return {value}
    return {item for item in value if item}


def _future_date(days: int = 1) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def _next_business_date(days: int = 1) -> str:
    candidate = date.today() + timedelta(days=days)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate.isoformat()


def _normalize_request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in payload.items():
        if value == SENTINEL_TOMORROW:
            normalized[key] = _future_date(1)
        elif value == SENTINEL_NEXT_BUSINESS_DAY:
            normalized[key] = _next_business_date(1)
        else:
            normalized[key] = value
    return normalized


def _build_case_metadata(case: dict[str, Any], session_key: str):
    config = get_config(validate_live=True)
    return create_metadata(
        session_key=session_key,
        device_type=case.get("device_type", config.device_type),
        user_agent=case.get("user_agent", config.user_agent),
    )


def _resolve_account(
    collector: DataCollector,
    *,
    customer_no: str,
    account_no: str,
    card_hint: str | None,
    role: str,
) -> dict[str, Any]:
    accounts = collector.get_accounts_by_customer_and_account_no(customer_no, account_no)
    if not accounts:
        pytest.fail(f"{role}: no accounts found for customer_no={customer_no}, account_no={account_no}")

    if card_hint:
        matched_accounts = [account for account in accounts if _pan_hint_matches(account.get("ipc_card_pan"), card_hint)]
        if not matched_accounts:
            pytest.fail(f"{role}: no account matches card hint {card_hint}. Candidates: {_format_accounts(accounts)}")
        accounts = matched_accounts

    if len(accounts) == 1:
        return accounts[0]

    default_accounts = [account for account in accounts if account.get("is_default")]
    if not card_hint and len(default_accounts) == 1:
        return default_accounts[0]

    pytest.fail(f"{role}: ambiguous account selection. Candidates: {_format_accounts(accounts)}")


def _assert_account_expectations(account: dict[str, Any], expected: dict[str, Any] | None, role: str):
    if not expected:
        return

    expected_map = {
        "currency": "ccy",
        "account_kind": "account_kind",
        "processor": "processor",
        "card_system": "card_system",
    }
    for expected_key, actual_key in expected_map.items():
        expected_value = expected.get(expected_key)
        if expected_value is None:
            continue

        actual_value = account.get(actual_key)
        assert actual_value == expected_value, (
            f"{role}: expected {expected_key}={expected_value}, got {actual_value}. "
            f"Account snapshot={json.dumps(account, ensure_ascii=False, default=str)}"
        )


def _get_session_key_with_retry(collector: DataCollector, customer_no: str, offset: int = 0) -> str | None:
    return collector.get_valid_session_key_by_customer_no(customer_no=customer_no, offset=offset)


def _get_transaction_error_code(response: Any) -> str:
    return getattr(getattr(response, "error", None), "code", "") or "UNKNOWN"


def _get_transaction_error_data(response: Any) -> str:
    return getattr(getattr(response, "error", None), "data", "") or ""


def _create_request_with_session_retry(
    collector: DataCollector,
    *,
    case: dict[str, Any],
    payload: dict[str, Any],
) -> tuple[str, Any]:
    config = get_config(validate_live=True)
    sender_customer_no = case["sender"]["customer_no"]
    last_response = None
    skip_error_codes = set(COMMON_CREATE_SKIP_ERROR_CODES) | set(case.get("skip_on_create_error_codes", []))

    for offset in range(config.session_retry_limit):
        session_key = _get_session_key_with_retry(collector, sender_customer_no, offset=offset)
        if not session_key:
            if offset == 0:
                pytest.skip(f"No valid session_key found for customer_no={sender_customer_no}")
            break

        metadata = _build_case_metadata(case, session_key)
        print(f"[create] session_offset={offset}, session_key={session_key[:10]}...")
        response = make_grpc_request(case["operation"]["code"], payload, metadata)
        last_response = response
        print(f"[create] response={response}")

        if getattr(response, "success", False):
            return session_key, response

        error_code = _get_transaction_error_code(response)
        if error_code == "INVALID_SESSION_KEY":
            print(f"[create] INVALID_SESSION_KEY for offset={offset}, trying next session")
            continue

        if error_code in skip_error_codes:
            pytest.skip(
                f"{case['name']}: create skipped by runtime guard, error_code={error_code}, "
                f"error_data={_get_transaction_error_data(response)}"
            )

        return session_key, response

    if last_response is None:
        pytest.skip(f"Could not find a usable session_key for customer_no={sender_customer_no}")

    return "", last_response


def _resolve_sender_account(collector: DataCollector, case: dict[str, Any]) -> dict[str, Any]:
    sender = case["sender"]
    return _resolve_account(
        collector,
        customer_no=sender["customer_no"],
        account_no=sender["account_no"],
        card_hint=sender.get("card_no") or sender.get("card_mask"),
        role="sender",
    )


def _resolve_recipient_account(collector: DataCollector, case: dict[str, Any]) -> dict[str, Any] | None:
    recipient = case.get("recipient")
    if not recipient or not recipient.get("customer_no") or not recipient.get("account_no"):
        return None

    return _resolve_account(
        collector,
        customer_no=recipient["customer_no"],
        account_no=recipient["account_no"],
        card_hint=recipient.get("card_no") or recipient.get("card_mask"),
        role="recipient",
    )


def _prepare_case_accounts(
    collector: DataCollector,
    case: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None, Decimal, Decimal | None]:
    sender_account = _resolve_sender_account(collector, case)
    recipient_account = _resolve_recipient_account(collector, case)

    _assert_account_expectations(sender_account, case["sender"].get("expected"), "sender")
    if recipient_account:
        _assert_account_expectations(recipient_account, case.get("recipient", {}).get("expected"), "recipient")

    sender_sync_payload = sync_account_view(sender_account)
    recipient_sync_payload = sync_account_view(recipient_account) if recipient_account else None
    if sender_sync_payload:
        print(f"[sender-card-sync] {json.dumps(sender_sync_payload, ensure_ascii=False, default=str)}")
    if recipient_sync_payload:
        print(f"[recipient-card-sync] {json.dumps(recipient_sync_payload, ensure_ascii=False, default=str)}")

    sender_balance_before = _parse_decimal(collector.get_account_balance(account_id=sender_account["id"]))
    recipient_balance_before = (
        _parse_decimal(collector.get_account_balance(account_id=recipient_account["id"]))
        if recipient_account
        else None
    )

    if sender_balance_before is None:
        pytest.fail(f"{case['name']}: could not read sender balance before create")

    if sender_account.get("record_stat") != "O":
        pytest.skip(
            f"{case['name']}: sender account record_stat={sender_account.get('record_stat')} is not open"
        )
    if sender_account.get("ac_stat_dormant"):
        pytest.skip(f"{case['name']}: sender account is dormant")
    if sender_account.get("ac_stat_frozen"):
        pytest.skip(f"{case['name']}: sender account is frozen")
    if sender_account.get("ac_stat_no_dr"):
        pytest.skip(f"{case['name']}: sender account is marked no-debit")

    requested_debit_amount = _parse_decimal(
        case["request"].get("amountDebit")
        or case["request"].get("amountCredit")
        or case["request"].get("amount")
    )
    if requested_debit_amount is not None and sender_balance_before < requested_debit_amount:
        pytest.skip(
            f"{case['name']}: sender balance {sender_balance_before} is below requested amount {requested_debit_amount}"
        )

    return sender_account, recipient_account, sender_balance_before, recipient_balance_before


def _build_payload(
    case: dict[str, Any],
    *,
    operation_id: str,
    sender_account: dict[str, Any],
    recipient_account: dict[str, Any] | None,
) -> dict[str, Any]:
    code = case["operation"]["code"]
    request = _normalize_request_payload(dict(case["request"]))

    if code == "MAKE_BANK_CLIENT_TRANSFER":
        prop_type = request["accountCreditPropType"]
        if prop_type == "CARD_NO":
            if not case.get("recipient", {}).get("card_no"):
                pytest.fail(f"{case['name']}: recipient.card_no is required for CARD_NO transfer")
            account_credit_prop_value = case["recipient"]["card_no"]
        elif prop_type == "ACCOUNT_NO":
            if not recipient_account:
                pytest.fail(f"{case['name']}: recipient account is required for ACCOUNT_NO transfer")
            account_credit_prop_value = recipient_account["account_no"]
        else:
            pytest.fail(f"{case['name']}: unsupported accountCreditPropType={prop_type}")

        payload = {
            "operationId": operation_id,
            "accountIdDebit": sender_account["id"],
            "accountCreditPropValue": account_credit_prop_value,
        }
        payload.update(request)
        return payload

    if code == "MAKE_OWN_ACCOUNTS_TRANSFER":
        if not recipient_account:
            pytest.fail(f"{case['name']}: recipient account is required for own accounts transfer")
        payload = {
            "operationId": operation_id,
            "accountIdDebit": sender_account["id"],
            "accountIdCredit": recipient_account["id"],
        }
        payload.update(request)
        return payload

    if code in {"MAKE_OTHER_BANK_TRANSFER", "MAKE_SWIFT_TRANSFER", "MAKE_GENERIC_PAYMENT_V2", "MAKE_QR_PAYMENT"}:
        payload = {
            "operationId": operation_id,
            "accountIdDebit": sender_account["id"],
        }
        payload.update(request)
        if code == "MAKE_SWIFT_TRANSFER" and not payload.get("commissionAccountId"):
            payload["commissionAccountId"] = str(sender_account["id"])
        return payload

    pytest.fail(f"{case['name']}: unsupported operation code={code}")


def _wait_for_expected_transaction(
    collector: DataCollector,
    *,
    case: dict[str, Any],
    operation_id: str,
) -> dict[str, Any]:
    config = get_config(validate_live=True)
    verification = case.get("verification", {})
    expected_internal = _as_status_set(verification.get("expected_status_internal"), default="SUCCESS")
    expected_external = _as_status_set(verification.get("expected_status_external"), default="SUCCESS")
    timeout_seconds = int(verification.get("transaction_timeout_seconds", config.transaction_timeout_seconds))
    stop_on_first_expected_status = bool(verification.get("stop_on_first_expected_status"))
    pass_on_timeout_if_last_status_matches = bool(
        verification.get("pass_on_timeout_if_last_status_matches")
    )

    deadline = time.time() + timeout_seconds
    last_transaction = None
    while time.time() < deadline:
        last_transaction = collector.get_transaction_by_operation_id(operation_id)
        if last_transaction:
            internal_status = last_transaction.get("txn_status_internal")
            external_status = last_transaction.get("txn_status_external")
            print(
                f"[txn-poll] operation_id={operation_id}, "
                f"internal={internal_status}, external={external_status}, "
                f"txn_code={last_transaction.get('txn_code')}"
            )
            if internal_status == "FAILURE" or external_status == "FAILURE":
                pytest.fail(
                    "Transaction reached FAILURE state: "
                    f"{json.dumps(last_transaction, ensure_ascii=False, default=str, indent=2)}"
                )
            if internal_status in expected_internal and external_status in expected_external:
                if stop_on_first_expected_status or (
                    internal_status == "SUCCESS" and external_status == "SUCCESS"
                ):
                    return last_transaction
                if expected_internal == {"SUCCESS"} and expected_external == {"SUCCESS"}:
                    return last_transaction
            if internal_status == "SUCCESS" and external_status == "SUCCESS":
                return last_transaction
        time.sleep(config.poll_interval_seconds)

    if last_transaction:
        internal_status = last_transaction.get("txn_status_internal")
        external_status = last_transaction.get("txn_status_external")
        if (
            pass_on_timeout_if_last_status_matches
            and internal_status in expected_internal
            and external_status in expected_external
        ):
            print(
                "[txn-poll] timeout reached, but last observed status matches configured expectation: "
                f"internal={internal_status}, external={external_status}"
            )
            return last_transaction

    pytest.fail(
        "Timed out waiting for expected transaction state. "
        f"Last transaction={json.dumps(last_transaction, ensure_ascii=False, default=str, indent=2)}"
    )


def _expected_sender_delta(case: dict[str, Any], transaction: dict[str, Any]) -> Decimal:
    code = case["operation"]["code"]
    request = case["request"]
    amount_debit = _parse_decimal(transaction.get("amount_debit"))
    amount_debit_total = _parse_decimal(transaction.get("amount_debit_total"))

    if code in {"MAKE_OTHER_BANK_TRANSFER", "MAKE_SWIFT_TRANSFER", "MAKE_GENERIC_PAYMENT_V2"}:
        return amount_debit_total or amount_debit or Decimal(str(request.get("amountCredit") or "0"))
    if code == "MAKE_QR_PAYMENT":
        return amount_debit or Decimal(str(request.get("amount") or "0"))
    return amount_debit or Decimal(str(request.get("amountDebit") or request.get("amountCredit") or "0"))


def _expected_recipient_delta(case: dict[str, Any], transaction: dict[str, Any]) -> Decimal:
    code = case["operation"]["code"]
    amount_credit = _parse_decimal(transaction.get("amount_credit"))
    if code in {"MAKE_BANK_CLIENT_TRANSFER", "MAKE_OWN_ACCOUNTS_TRANSFER"}:
        if amount_credit is not None:
            return amount_credit
        request = case["request"]
        fallback = request.get("amountDebit") or request.get("amountCredit") or "0"
        return Decimal(str(fallback))
    return Decimal("0")


def _wait_for_expected_balances(
    collector: DataCollector,
    *,
    case: dict[str, Any],
    transaction: dict[str, Any],
    sender_account: dict[str, Any],
    sender_balance_before: Decimal,
    recipient_account: dict[str, Any] | None,
    recipient_balance_before: Decimal | None,
) -> tuple[Decimal | None, Decimal | None]:
    config = get_config(validate_live=True)
    verification = case.get("verification", {})
    require_sender_balance = bool(verification.get("sender_balance_observable", True))
    require_recipient_balance = bool(verification.get("recipient_balance_observable")) and recipient_account is not None
    allow_statement_fallback = bool(verification.get("statement_fallback_allowed"))
    skip_for_processing_state = bool(verification.get("skip_balance_check_for_processing_state"))
    transaction_is_terminal_success = (
        transaction.get("txn_status_internal") == "SUCCESS" and transaction.get("txn_status_external") == "SUCCESS"
    )

    if skip_for_processing_state and not transaction_is_terminal_success:
        print(
            "[balance-poll] skipping strict balance verification because transaction is still in processing state: "
            f"internal={transaction.get('txn_status_internal')}, "
            f"external={transaction.get('txn_status_external')}"
        )
        sender_balance_after = _parse_decimal(collector.get_account_balance(account_id=sender_account["id"]))
        recipient_balance_after = (
            _parse_decimal(collector.get_account_balance(account_id=recipient_account["id"]))
            if recipient_account
            else None
        )
        return sender_balance_after, recipient_balance_after

    sender_expected = sender_balance_before - _expected_sender_delta(case, transaction)
    recipient_expected = None
    if require_recipient_balance and recipient_balance_before is not None:
        recipient_expected = recipient_balance_before + _expected_recipient_delta(case, transaction)

    deadline = time.time() + config.balance_sync_timeout_seconds
    last_sender_balance = sender_balance_before
    last_recipient_balance = recipient_balance_before

    while time.time() < deadline:
        sync_account_view(sender_account)
        if recipient_account and require_recipient_balance:
            sync_account_view(recipient_account)

        last_sender_balance = _parse_decimal(collector.get_account_balance(account_id=sender_account["id"]))
        if recipient_account and require_recipient_balance:
            last_recipient_balance = _parse_decimal(collector.get_account_balance(account_id=recipient_account["id"]))

        sender_ready = (not require_sender_balance) or (last_sender_balance == sender_expected)
        recipient_ready = (not require_recipient_balance) or (last_recipient_balance == recipient_expected)
        print(
            f"[balance-poll] sender={last_sender_balance}/{sender_expected}, "
            f"recipient={last_recipient_balance}/{recipient_expected}, "
            f"sender_ready={sender_ready}, recipient_ready={recipient_ready}"
        )
        if sender_ready and recipient_ready:
            return last_sender_balance, last_recipient_balance

        time.sleep(config.poll_interval_seconds)

    statement_rows: list[dict[str, Any]] = []
    cbs_reference = transaction.get("cbs_reference")
    if cbs_reference:
        statement_rows = collector.get_transaction_statement_by_reference(cbs_reference)
        sender_debit = _expected_sender_delta(case, transaction)
        sender_row = next(
            (
                row for row in statement_rows
                if row["account_no"] == sender_account["account_no"] and _parse_decimal(row["dr"]) == sender_debit
            ),
            None,
        )
        recipient_row = None
        if recipient_account and require_recipient_balance:
            recipient_credit = _expected_recipient_delta(case, transaction)
            recipient_row = next(
                (
                    row for row in statement_rows
                    if row["account_no"] == recipient_account["account_no"] and _parse_decimal(row["cr"]) == recipient_credit
                ),
                None,
            )
        if allow_statement_fallback and sender_row and (not require_recipient_balance or recipient_row):
            print(
                "[balance-poll] balances stayed stale in accounts table, "
                "but transaction_statement confirms expected postings"
            )
            return last_sender_balance, last_recipient_balance

    pytest.fail(
        "Timed out waiting for balance sync. "
        f"sender_expected={sender_expected}, last_sender_balance={last_sender_balance}, "
        f"recipient_expected={recipient_expected}, last_recipient_balance={last_recipient_balance}, "
        f"statement_rows={json.dumps(statement_rows, ensure_ascii=False, default=str, indent=2)}"
    )


def _verify_success_transaction(
    case: dict[str, Any],
    *,
    sender_account: dict[str, Any],
    recipient_account: dict[str, Any] | None,
    transaction: dict[str, Any],
):
    code = case["operation"]["code"]
    request = case["request"]

    assert transaction["account_debit_id"] == sender_account["id"]
    assert transaction["account_debit_no"] == sender_account["account_no"]
    assert transaction["customer_no_debit"] == case["sender"]["customer_no"]

    if code == "MAKE_BANK_CLIENT_TRANSFER":
        assert recipient_account is not None
        assert transaction["account_credit_no"] == recipient_account["account_no"]
        assert transaction["customer_no_credit"] == case["recipient"]["customer_no"]
        assert transaction["account_credit_prop_type"] == request["accountCreditPropType"]
        if request["accountCreditPropType"] == "ACCOUNT_NO":
            assert transaction["account_credit_prop_value"] == recipient_account["account_no"]
        if request.get("paymentPurpose"):
            assert transaction["payment_purpose"] == request["paymentPurpose"]
        return

    if code == "MAKE_OWN_ACCOUNTS_TRANSFER":
        assert recipient_account is not None
        assert transaction["account_credit_id"] == recipient_account["id"]
        assert transaction["account_credit_no"] == recipient_account["account_no"]
        assert transaction["customer_no_credit"] == case["recipient"]["customer_no"]
        return

    if code == "MAKE_OTHER_BANK_TRANSFER":
        assert transaction["recipient_bank_bic"] == request["recipientBankBic"]
        assert transaction["recipient_name"] == request["recipientName"]
        assert transaction["clearing_recipient_acc_no"] == request["accountCreditNumber"]
        return

    if code == "MAKE_QR_PAYMENT":
        assert transaction["txn_code"] == "MAKE_QR_PAYMENT"
        if transaction.get("account_credit_prop_value") and request.get("qrAccount"):
            assert transaction["account_credit_prop_value"] == request["qrAccount"]
        return

    if code == "MAKE_SWIFT_TRANSFER":
        assert transaction["recipient_bank_swift"] == request["recipientBankSwift"]
        assert transaction["swift_recipient_acc_no"] == request["recipientAccNo"]
        assert transaction["swift_transfer_ccy"] == request["transferCcy"]
        assert transaction["swift_commission_type"] == request["commissionType"]
        return

    pytest.fail(f"{case['name']}: unsupported verification for operation code={code}")


def run_live_case(case: dict[str, Any]) -> None:
    config = get_config(validate_live=True)
    collector = DataCollector(DatabaseConfig.from_env())
    sender_user_id = collector.get_user_id_by_customer_no(case["sender"]["customer_no"])
    if sender_user_id is None:
        pytest.skip(f"No user found for sender customer_no={case['sender']['customer_no']}")

    sender_account, recipient_account, sender_balance_before, recipient_balance_before = _prepare_case_accounts(
        collector,
        case,
    )

    operation_id = str(uuid.uuid4())
    payload = _build_payload(
        case,
        operation_id=operation_id,
        sender_account=sender_account,
        recipient_account=recipient_account,
    )
    validate_payload_against_contract(case["operation"]["code"], payload)

    print(f"\n=== {case['name']} ===")
    print(f"route_key={case['route_key']}")
    print(f"operation_code={case['operation']['code']}")
    print(f"operation_id={operation_id}")
    print(f"sender_user_id={sender_user_id}")
    print(f"sender_account={json.dumps(sender_account, ensure_ascii=False, default=str, indent=2)}")
    if recipient_account:
        print(f"recipient_account={json.dumps(recipient_account, ensure_ascii=False, default=str, indent=2)}")
    print(f"sender_balance_before={sender_balance_before}")
    print(f"recipient_balance_before={recipient_balance_before}")
    print(f"payload={json.dumps(payload, ensure_ascii=False, default=str, indent=2)}")

    session_key, create_response = _create_request_with_session_retry(
        collector,
        case=case,
        payload=payload,
    )

    assert_success(create_response, f"{case['name']} - create")

    confirm_metadata = _build_case_metadata(case, session_key)
    confirm_response = confirm_operation(
        operation_id,
        metadata=confirm_metadata,
        otp=case.get("otp", config.otp_code),
    )
    print(f"[confirm] response={confirm_response}")
    assert_success(confirm_response, f"{case['name']} - confirm")

    transaction = _wait_for_expected_transaction(
        collector,
        case=case,
        operation_id=operation_id,
    )
    sender_balance_after, recipient_balance_after = _wait_for_expected_balances(
        collector,
        case=case,
        transaction=transaction,
        sender_account=sender_account,
        sender_balance_before=sender_balance_before,
        recipient_account=recipient_account,
        recipient_balance_before=recipient_balance_before,
    )

    print(f"sender_balance_after={sender_balance_after}")
    print(f"recipient_balance_after={recipient_balance_after}")
    print(f"transaction={json.dumps(transaction, ensure_ascii=False, default=str, indent=2)}")

    _verify_success_transaction(
        case,
        sender_account=sender_account,
        recipient_account=recipient_account,
        transaction=transaction,
    )
