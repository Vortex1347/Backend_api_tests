from __future__ import annotations

import json
import re
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

from support.cases import validate_cases

SUITE_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = SUITE_ROOT / "data"
CATALOG_ROOT = DATA_ROOT / "catalog"

INTERNAL_DIR = DATA_ROOT / "bank_client_transfer"
OWN_DIR = DATA_ROOT / "own_accounts_transfer"
OTHER_BANK_DIR = DATA_ROOT / "other_bank_transfer"
QR_DIR = DATA_ROOT / "qr_payment"

DEFAULT_STATUS_INTERNAL = ["ACCEPTED_NOT_PROCESSED", "SUCCESS"]
DEFAULT_STATUS_EXTERNAL = ["IN_PROCESS", "SUCCESS"]

INTERNAL_VERIFICATION = {
    "sender_balance_observable": True,
    "recipient_balance_observable": True,
    "statement_fallback_allowed": True,
    "expected_status_internal": DEFAULT_STATUS_INTERNAL,
    "expected_status_external": DEFAULT_STATUS_EXTERNAL,
    "pass_on_timeout_if_last_status_matches": True,
    "skip_balance_check_for_processing_state": True,
}

OTHER_BANK_VERIFICATION = {
    "sender_balance_observable": True,
    "recipient_balance_observable": False,
    "statement_fallback_allowed": True,
    "expected_status_internal": DEFAULT_STATUS_INTERNAL,
    "expected_status_external": DEFAULT_STATUS_EXTERNAL,
    "pass_on_timeout_if_last_status_matches": True,
    "skip_balance_check_for_processing_state": True,
}

QR_VERIFICATION = {
    "sender_balance_observable": True,
    "recipient_balance_observable": False,
    "statement_fallback_allowed": True,
    "expected_status_internal": DEFAULT_STATUS_INTERNAL,
    "expected_status_external": DEFAULT_STATUS_EXTERNAL,
    "pass_on_timeout_if_last_status_matches": True,
    "skip_balance_check_for_processing_state": True,
}


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_json(path: Path, payload: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if current != serialized:
        path.write_text(serialized, encoding="utf-8")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _entity_sort_key(entity: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        entity["customer_no"],
        entity["currency"],
        entity["account_kind"],
        entity["processor"],
        entity["account_no"],
    )


def _entity_kind_slug(entity: dict[str, Any]) -> str:
    return "card" if entity["account_kind"] == "CARD" else "account"


def _entity_ref(entity: dict[str, Any]) -> str:
    return f"c{entity['customer_no']}_a{entity['account_no'][-4:]}"


def _entity_expected(entity: dict[str, Any]) -> dict[str, str]:
    expected = {
        "currency": entity["currency"],
        "account_kind": entity["account_kind"],
        "processor": entity["processor"],
    }
    if entity.get("card_system"):
        expected["card_system"] = entity["card_system"]
    return expected


def _entity_party(entity: dict[str, Any]) -> dict[str, Any]:
    party = {
        "customer_no": entity["customer_no"],
        "account_no": entity["account_no"],
        "expected": _entity_expected(entity),
    }
    if entity.get("card_no"):
        party["card_no"] = entity["card_no"]
    if entity.get("card_mask"):
        party["card_mask"] = entity["card_mask"]
    return party


def _build_case(
    *,
    name: str,
    route_key: str,
    operation_code: str,
    sender: dict[str, Any],
    request: dict[str, Any],
    verification: dict[str, Any],
    recipient: dict[str, Any] | None = None,
) -> dict[str, Any]:
    case = {
        "name": name,
        "route_key": route_key,
        "operation": {"code": operation_code},
        "sender": sender,
        "request": request,
        "verification": verification,
    }
    if recipient is not None:
        case["recipient"] = recipient
    return case


def _bank_client_case(
    sender: dict[str, Any],
    recipient: dict[str, Any],
    *,
    prop_type: str,
) -> dict[str, Any]:
    sender_kind = _entity_kind_slug(sender)
    recipient_kind = "card" if prop_type == "CARD_NO" else "account"
    name = (
        f"bank_client_{sender_kind}_to_{recipient_kind}_"
        f"{_slug(sender['currency'])}_{_slug(sender['processor'])}_{_entity_ref(sender)}_"
        f"to_{_slug(recipient['processor'])}_{_entity_ref(recipient)}"
    )
    route_key = (
        f"MAKE_BANK_CLIENT_TRANSFER:{prop_type}:"
        f"{sender['account_kind']}:{sender['processor']}:{sender['currency']}"
        f"->{recipient['account_kind']}:{recipient['processor']}:{recipient['currency']}"
    )
    request = {
        "accountCreditPropType": prop_type,
        "amountDebit": "1.00",
        "paymentPurpose": f"Matrix {sender_kind} to {recipient_kind}",
    }
    return _build_case(
        name=name,
        route_key=route_key,
        operation_code="MAKE_BANK_CLIENT_TRANSFER",
        sender=_entity_party(sender),
        recipient=_entity_party(recipient),
        request=request,
        verification=deepcopy(INTERNAL_VERIFICATION),
    )


def _own_accounts_case(sender: dict[str, Any], recipient: dict[str, Any]) -> dict[str, Any]:
    same_currency = sender["currency"] == recipient["currency"]
    transfer_type = "SAME_CURRENCY" if same_currency else "FX"
    name = (
        f"own_accounts_{transfer_type.lower()}_{_entity_kind_slug(sender)}_to_{_entity_kind_slug(recipient)}_"
        f"{_slug(sender['currency'])}_{_entity_ref(sender)}_to_{_slug(recipient['currency'])}_{_entity_ref(recipient)}"
    )
    route_key = (
        f"MAKE_OWN_ACCOUNTS_TRANSFER:{transfer_type}:"
        f"{sender['account_kind']}:{sender['processor']}:{sender['currency']}"
        f"->{recipient['account_kind']}:{recipient['processor']}:{recipient['currency']}"
    )
    request = {
        "amountDebit": "1.00",
        "paymentPurpose": f"Own transfer {sender['currency']} to {recipient['currency']}",
    }
    return _build_case(
        name=name,
        route_key=route_key,
        operation_code="MAKE_OWN_ACCOUNTS_TRANSFER",
        sender=_entity_party(sender),
        recipient=_entity_party(recipient),
        request=request,
        verification=deepcopy(INTERNAL_VERIFICATION),
    )


def _other_bank_case(
    sender: dict[str, Any],
    target: dict[str, Any],
    *,
    transfer_mode: str,
) -> dict[str, Any]:
    mode_label = "CLEARING" if transfer_mode == "C" else "GROSS"
    name = (
        f"other_bank_{mode_label.lower()}_{_slug(target['target_id'])}_"
        f"{_entity_kind_slug(sender)}_{_slug(sender['processor'])}_{_entity_ref(sender)}"
    )
    route_key = (
        f"MAKE_OTHER_BANK_TRANSFER:{mode_label}:"
        f"{sender['account_kind']}:{sender['processor']}:{sender['currency']}"
        f"->EXTERNAL:{target['currency']}"
    )
    request = {
        "transferClearingGross": transfer_mode,
        "valueDate": target["value_date"],
        "recipientName": target["recipient_name"],
        "recipientBankBic": target["recipient_bank_bic"],
        "accountCreditNumber": target["account_credit_number"],
        "transferPurposeText": target["transfer_purpose_text"],
        "knp": target["knp"],
        "amountCredit": target["amount_credit"],
    }
    return _build_case(
        name=name,
        route_key=route_key,
        operation_code="MAKE_OTHER_BANK_TRANSFER",
        sender=_entity_party(sender),
        request=request,
        verification=deepcopy(OTHER_BANK_VERIFICATION),
    )


def _qr_payment_case(sender: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    name = f"qr_payment_{_slug(target['target_id'])}_{_entity_kind_slug(sender)}_{_slug(sender['processor'])}_{_entity_ref(sender)}"
    route_key = (
        f"MAKE_QR_PAYMENT:{target['target_id'].upper()}:"
        f"{sender['account_kind']}:{sender['processor']}:{sender['currency']}"
        f"->QR:{target['currency']}"
    )
    request = {
        "clientType": target["client_type"],
        "qrVersion": target["qr_version"],
        "qrType": target["qr_type"],
        "qrMerchantProviderId": target["qr_merchant_provider_id"],
        "amount": target["amount"],
        "qrAccountChangeable": target.get("qr_account_changeable", False),
    }
    optional_fields = {
        "qrMerchantId": target.get("qr_merchant_id"),
        "qrServiceId": target.get("qr_service_id"),
        "qrAccount": target.get("qr_account"),
        "qrMcc": target.get("qr_mcc"),
        "qrCcy": target.get("qr_ccy"),
        "qrTransactionId": target.get("qr_transaction_id"),
        "qrServiceName": target.get("qr_service_name"),
        "qrComment": target.get("qr_comment"),
        "qrControlSum": target.get("qr_control_sum"),
    }
    request.update({key: value for key, value in optional_fields.items() if value not in {None, ""}})
    return _build_case(
        name=name,
        route_key=route_key,
        operation_code="MAKE_QR_PAYMENT",
        sender=_entity_party(sender),
        request=request,
        verification=deepcopy(QR_VERIFICATION),
    )


def build_case_matrices() -> dict[Path, list[dict[str, Any]]]:
    entities = sorted(_load_json(CATALOG_ROOT / "entities.json"), key=_entity_sort_key)
    other_bank_targets = sorted(_load_json(CATALOG_ROOT / "other_bank_targets.json"), key=lambda item: item["target_id"])
    qr_targets = sorted(_load_json(CATALOG_ROOT / "qr_payment_targets.json"), key=lambda item: item["target_id"])

    outputs: dict[Path, list[dict[str, Any]]] = {
        INTERNAL_DIR / "card_to_card.json": [],
        INTERNAL_DIR / "account_to_card.json": [],
        INTERNAL_DIR / "card_to_account.json": [],
        INTERNAL_DIR / "account_to_account.json": [],
        OWN_DIR / "same_currency.json": [],
        OWN_DIR / "fx.json": [],
        OTHER_BANK_DIR / "clearing.json": [],
        OTHER_BANK_DIR / "gross.json": [],
        QR_DIR / "static_qr.json": [],
    }

    for sender in entities:
        if not sender.get("account_no"):
            continue
        sender_kind = _entity_kind_slug(sender)
        for recipient in entities:
            if sender["customer_no"] == recipient["customer_no"]:
                continue
            if sender["currency"] != recipient["currency"]:
                continue
            if sender["customer_no"] == recipient["customer_no"] and sender["account_no"] == recipient["account_no"]:
                continue

            if recipient.get("card_no"):
                outputs[INTERNAL_DIR / f"{sender_kind}_to_card.json"].append(
                    _bank_client_case(sender, recipient, prop_type="CARD_NO")
                )

            outputs[INTERNAL_DIR / f"{sender_kind}_to_account.json"].append(
                _bank_client_case(sender, recipient, prop_type="ACCOUNT_NO")
            )

    entities_by_customer: dict[str, list[dict[str, Any]]] = {}
    for entity in entities:
        entities_by_customer.setdefault(entity["customer_no"], []).append(entity)

    for customer_entities in entities_by_customer.values():
        ordered = sorted(customer_entities, key=_entity_sort_key)
        for sender in ordered:
            for recipient in ordered:
                if sender["account_no"] == recipient["account_no"]:
                    continue
                case = _own_accounts_case(sender, recipient)
                output_file = OWN_DIR / ("same_currency.json" if sender["currency"] == recipient["currency"] else "fx.json")
                outputs[output_file].append(case)

    for target in other_bank_targets:
        for sender in entities:
            if sender["currency"] != target["currency"]:
                continue
            outputs[OTHER_BANK_DIR / "clearing.json"].append(
                _other_bank_case(sender, target, transfer_mode="C")
            )
            outputs[OTHER_BANK_DIR / "gross.json"].append(
                _other_bank_case(sender, target, transfer_mode="G")
            )

    for target in qr_targets:
        for sender in entities:
            if sender["currency"] != target["currency"]:
                continue
            outputs[QR_DIR / "static_qr.json"].append(_qr_payment_case(sender, target))

    normalized_outputs: dict[Path, list[dict[str, Any]]] = {}
    seen_names: set[str] = set()
    for path, cases in outputs.items():
        ordered_cases = sorted(cases, key=lambda item: item["name"])
        validate_cases(ordered_cases, source=path)
        for case in ordered_cases:
            if case["name"] in seen_names:
                raise ValueError(f"Duplicate generated case name detected across files: {case['name']}")
            seen_names.add(case["name"])
        normalized_outputs[path] = ordered_cases

    return normalized_outputs


def _delete_stale_generated_files(expected_paths: set[Path]) -> None:
    generated_dirs = [INTERNAL_DIR, OWN_DIR, OTHER_BANK_DIR, QR_DIR]
    for directory in generated_dirs:
        if not directory.exists():
            continue
        for candidate in directory.glob("*.json"):
            if candidate not in expected_paths:
                candidate.unlink()


@lru_cache(maxsize=1)
def ensure_generated_matrices() -> tuple[str, ...]:
    outputs = build_case_matrices()
    expected_paths = set(outputs)
    _delete_stale_generated_files(expected_paths)
    for path, cases in outputs.items():
        _write_json(path, cases)
    return tuple(sorted(str(path) for path in outputs))


if __name__ == "__main__":
    built_paths = ensure_generated_matrices()
    for built_path in built_paths:
        path = Path(built_path)
        cases = _load_json(path)
        print(f"{path.relative_to(SUITE_ROOT)} -> {len(cases)} cases")
