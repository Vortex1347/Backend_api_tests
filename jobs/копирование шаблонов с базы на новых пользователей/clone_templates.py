#!/usr/bin/env python3
"""
CLI-скрипт для копирования актуальных шаблонов на новых пользователей.

Логика:
1. Берем все текущие template_type из ibank.templates.
2. Для каждого типа выбираем до 4 самых актуальных шаблонов по id DESC.
3. Клонируем шаблоны на целевого клиента, меняя только customer_no.
4. Повторные запуски идемпотентны: совпадения по
   (customer_no, template_type, txn_code, template_name) пропускаются.

По умолчанию скрипт работает в dry-run режиме и не пишет в БД.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from database_collector import DatabaseConfig

try:
    import psycopg2
    from psycopg2.extras import Json, RealDictCursor
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Не найден модуль psycopg2. Запусти скрипт через Python-интерпретатор, "
        "в котором установлен psycopg2."
    ) from exc


JOB_DIR = Path(__file__).resolve().parent
TARGET_CUSTOMERS_PATH = JOB_DIR / "target_customers.json"
REPORTS_DIR = JOB_DIR / "reports"
TABLE_NAME = "ibank.templates"
SOURCE_LIMIT_PER_TYPE = 4
DEFAULT_PILOT_CUSTOMER = "00909465"

TEMPLATE_COLUMNS = [
    "template_name",
    "template_type",
    "txn_id",
    "txn_code",
    "total_charges",
    "amount_debit_total",
    "customer_no",
    "account_credit_id",
    "account_debit_id",
    "amount_debit",
    "payment_purpose",
    "prop_value",
    "recipient_bank_bic",
    "value_date",
    "knp",
    "amount_credit",
    "recipient_name",
    "service_provider_id",
    "account_credit_no",
    "account_credit_prop_value",
    "account_credit_prop_type",
    "account_credit_ccy",
    "tax_code",
    "region_code",
    "district_code",
    "okmot_code",
    "vehicle_number",
    "pay_ref_1",
    "pay_ref_2",
    "ipk",
    "iph",
    "transfer_clearing_gross",
    "swift_transfer_ccy",
    "recipient_address",
    "recipient_bank_swift",
    "swift_recipient_bank_branch",
    "intermediary_bank_swift",
    "swift_commission_type",
    "charges_acc_id",
    "swift_correspondent_acc_no",
    "swift_vo_code",
    "swift_inn",
    "swift_kpp",
    "swift_bin",
    "swift_kbe",
    "swift_knp",
    "customer_no_credit",
    "account_credit_card_pan",
    "c_p_h",
    "money_transfer_type",
    "additional_data",
    "their_ref_no",
]

DUPLICATE_KEY_COLUMNS = ("template_type", "txn_code", "template_name")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


@dataclass
class CustomerRunResult:
    customer_no: str
    planned_inserts: int
    existing_duplicates: int
    inserted: int
    source_row_count: int
    source_template_ids: list[int]
    skipped_duplicate_source_ids: list[int]
    status: str
    error: str | None = None


class TemplateCloneJob:
    def __init__(self, config: DatabaseConfig):
        self.config = config

    def connect(self) -> psycopg2.extensions.connection:
        return psycopg2.connect(
            user=self.config.user,
            password=self.config.password,
            host=self.config.host,
            port=self.config.port,
            database=self.config.database,
        )

    def fetch_source_templates(
        self,
        conn: psycopg2.extensions.connection,
        excluded_customer_nos: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        excluded_customer_nos = excluded_customer_nos or []
        source_filter = ""
        params: list[Any] = []
        if excluded_customer_nos:
            source_filter = "WHERE customer_no <> ALL(%s)"
            params.append(excluded_customer_nos)
        params.append(SOURCE_LIMIT_PER_TYPE)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                WITH ranked_templates AS (
                    SELECT
                        id,
                        {", ".join(TEMPLATE_COLUMNS)},
                        ROW_NUMBER() OVER (
                            PARTITION BY template_type
                            ORDER BY id DESC
                        ) AS rn
                    FROM {TABLE_NAME}
                    {source_filter}
                )
                SELECT
                    id,
                    {", ".join(TEMPLATE_COLUMNS)},
                    rn
                FROM ranked_templates
                WHERE rn <= %s
                ORDER BY template_type, rn
                """,
                params,
            )
            return [dict(row) for row in cur.fetchall()]

    def fetch_existing_duplicate_keys(
        self,
        conn: psycopg2.extensions.connection,
        customer_no: str,
    ) -> set[tuple[Any, Any, Any]]:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT {", ".join(DUPLICATE_KEY_COLUMNS)}
                FROM {TABLE_NAME}
                WHERE customer_no = %s
                """,
                (customer_no,),
            )
            return {
                self.build_duplicate_key(dict(row))
                for row in cur.fetchall()
            }

    @staticmethod
    def build_duplicate_key(row: dict[str, Any]) -> tuple[Any, Any, Any]:
        return tuple(row[column] for column in DUPLICATE_KEY_COLUMNS)

    def insert_templates_for_customer(
        self,
        conn: psycopg2.extensions.connection,
        customer_no: str,
        source_rows: list[dict[str, Any]],
        execute: bool,
    ) -> CustomerRunResult:
        existing_keys = self.fetch_existing_duplicate_keys(conn, customer_no)
        rows_to_insert: list[dict[str, Any]] = []
        skipped_duplicate_source_ids: list[int] = []

        for row in source_rows:
            duplicate_key = self.build_duplicate_key(row)
            if duplicate_key in existing_keys:
                skipped_duplicate_source_ids.append(int(row["id"]))
                continue
            rows_to_insert.append(row)

        inserted = 0
        try:
            with conn.cursor() as cur:
                for row in rows_to_insert:
                    if not execute:
                        continue

                    values = []
                    for column in TEMPLATE_COLUMNS:
                        value = customer_no if column == "customer_no" else row[column]
                        if column == "additional_data" and value is not None:
                            value = Json(value, dumps=lambda payload: json.dumps(payload, ensure_ascii=False))
                        values.append(value)

                    cur.execute(
                        f"""
                        INSERT INTO {TABLE_NAME} ({", ".join(TEMPLATE_COLUMNS)})
                        VALUES ({", ".join(["%s"] * len(TEMPLATE_COLUMNS))})
                        """,
                        values,
                    )
                    inserted += 1

            if execute:
                conn.commit()
            else:
                conn.rollback()

            return CustomerRunResult(
                customer_no=customer_no,
                planned_inserts=len(rows_to_insert),
                existing_duplicates=len(skipped_duplicate_source_ids),
                inserted=inserted,
                source_row_count=len(source_rows),
                source_template_ids=[int(row["id"]) for row in source_rows],
                skipped_duplicate_source_ids=skipped_duplicate_source_ids,
                status="success",
            )
        except Exception as exc:
            conn.rollback()
            return CustomerRunResult(
                customer_no=customer_no,
                planned_inserts=len(rows_to_insert),
                existing_duplicates=len(skipped_duplicate_source_ids),
                inserted=inserted,
                source_row_count=len(source_rows),
                source_template_ids=[int(row["id"]) for row in source_rows],
                skipped_duplicate_source_ids=skipped_duplicate_source_ids,
                status="error",
                error=str(exc),
            )


def load_target_customers(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Не найден файл с клиентами: {path}")

    with path.open("r", encoding="utf-8") as file:
        raw_data = json.load(file)

    if not isinstance(raw_data, list):
        raise ValueError("Файл target_customers.json должен содержать JSON-массив строк")

    customers = [str(item).strip() for item in raw_data if str(item).strip()]
    if not customers:
        raise ValueError("В файле target_customers.json нет customer_no")

    return customers


def select_customers(args: argparse.Namespace, all_customers: list[str]) -> list[str]:
    if args.all_customers:
        return all_customers

    if args.customer_no:
        return [args.customer_no]

    if DEFAULT_PILOT_CUSTOMER in all_customers:
        return [DEFAULT_PILOT_CUSTOMER]

    return [all_customers[0]]


def build_source_summary(
    source_rows: list[dict[str, Any]],
    excluded_customer_nos: list[str],
) -> dict[str, Any]:
    by_type: dict[str, dict[str, Any]] = {}

    for row in source_rows:
        template_type = row["template_type"]
        entry = by_type.setdefault(
            template_type,
            {
                "count": 0,
                "source_ids": [],
            },
        )
        entry["count"] += 1
        entry["source_ids"].append(int(row["id"]))

    return {
        "template_types_count": len(by_type),
        "source_rows_count": len(source_rows),
        "limit_per_type": SOURCE_LIMIT_PER_TYPE,
        "excluded_source_customers": excluded_customer_nos,
        "source_ids": [int(row["id"]) for row in source_rows],
        "by_type": by_type,
    }


def json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def save_report(report_payload: dict[str, Any]) -> tuple[Path, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_report_path = REPORTS_DIR / f"template_clone_report_{timestamp}.json"
    last_report_path = REPORTS_DIR / "last_run_report.json"

    report_json = json.dumps(
        report_payload,
        indent=2,
        ensure_ascii=False,
        default=json_default,
    )

    timestamped_report_path.write_text(report_json, encoding="utf-8")
    last_report_path.write_text(report_json, encoding="utf-8")
    return timestamped_report_path, last_report_path


def print_run_summary(
    *,
    execute: bool,
    selected_customers: list[str],
    source_summary: dict[str, Any],
    results: list[CustomerRunResult],
    report_paths: tuple[Path, Path],
) -> None:
    mode = "EXECUTE" if execute else "DRY-RUN"
    print(f"=== TEMPLATE CLONE JOB [{mode}] ===")
    print(f"Целевые клиенты: {', '.join(selected_customers)}")
    print(f"Типов шаблонов: {source_summary['template_types_count']}")
    print(f"Выбрано source-шаблонов: {source_summary['source_rows_count']}")
    print(
        "Source IDs: "
        + ", ".join(str(source_id) for source_id in source_summary["source_ids"])
    )

    print("\nРазбивка по template_type:")
    for template_type, payload in source_summary["by_type"].items():
        source_ids = ", ".join(str(source_id) for source_id in payload["source_ids"])
        print(f"- {template_type}: {payload['count']} шт. (IDs: {source_ids})")

    print("\nРезультаты по клиентам:")
    for result in results:
        line = (
            f"- {result.customer_no}: planned={result.planned_inserts}, "
            f"existing={result.existing_duplicates}, inserted={result.inserted}, "
            f"status={result.status}"
        )
        print(line)
        if result.error:
            print(f"  error: {result.error}")

    print("\nОтчеты сохранены:")
    print(f"- {report_paths[0]}")
    print(f"- {report_paths[1]}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Копирование актуальных шаблонов из ibank.templates на новых клиентов."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Выполнить реальные INSERT в БД. Без флага работает dry-run.",
    )
    parser.add_argument(
        "--customer-no",
        help="Запустить копирование только для одного customer_no.",
    )
    parser.add_argument(
        "--all-customers",
        action="store_true",
        help="Запустить копирование для всех customer_no из target_customers.json.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    all_customers = load_target_customers(TARGET_CUSTOMERS_PATH)
    selected_customers = select_customers(args, all_customers)

    job = TemplateCloneJob(DatabaseConfig())
    conn = job.connect()

    try:
        source_rows = job.fetch_source_templates(
            conn,
            excluded_customer_nos=all_customers,
        )
        source_summary = build_source_summary(source_rows, all_customers)
        results = [
            job.insert_templates_for_customer(
                conn=conn,
                customer_no=customer_no,
                source_rows=source_rows,
                execute=args.execute,
            )
            for customer_no in selected_customers
        ]
    finally:
        conn.close()

    report_payload = {
        "generated_at": datetime.now().isoformat(),
        "mode": "execute" if args.execute else "dry-run",
        "selected_customers": selected_customers,
        "source_summary": source_summary,
        "results": [result.__dict__ for result in results],
        "totals": {
            "customers": len(results),
            "source_rows_count": source_summary["source_rows_count"],
            "planned_inserts": sum(result.planned_inserts for result in results),
            "existing_duplicates": sum(result.existing_duplicates for result in results),
            "inserted": sum(result.inserted for result in results),
            "errors": sum(1 for result in results if result.status == "error"),
        },
    }
    report_paths = save_report(report_payload)
    print_run_summary(
        execute=args.execute,
        selected_customers=selected_customers,
        source_summary=source_summary,
        results=results,
        report_paths=report_paths,
    )

    return 1 if any(result.status == "error" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
