import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    user: str = "postgres"
    password: str = "postgres"
    host: str = "localhost"
    port: str = "5434"
    database: str = "ibank"
    schema: str = "ibank"


CARD_SYSTEM_KEYWORDS = (
    ("ELCARD_UPI", ("elcard/upi", "elcard/ upi")),
    ("MASTERCARD", ("mastercard",)),
    ("VISA", ("visa",)),
    ("ELCARD", ("elcard",)),
    ("UPI", ("upi",)),
)


def derive_processor(destination: str | None) -> str:
    normalized = (destination or "").strip().lower()
    if normalized == "ipc":
        return "IPC"
    if normalized == "compass":
        return "COMPASS"
    return "NONE"


def derive_account_kind(account: Dict[str, Any]) -> str:
    description = (account.get("account_class_description") or "").lower()
    if "current account" in description:
        return "CURRENT"
    if "card account" in description:
        return "CARD"
    if account.get("ipc_card_pan") or account.get("destination"):
        return "CARD"
    return "UNKNOWN"


def derive_card_system(account: Dict[str, Any]) -> str:
    description = (account.get("account_class_description") or "").lower()
    for system_name, keywords in CARD_SYSTEM_KEYWORDS:
        if any(keyword in description for keyword in keywords):
            return system_name
    return "UNKNOWN"


def enrich_account_runtime(account: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(account)
    enriched["processor"] = derive_processor(enriched.get("destination"))
    enriched["account_kind"] = derive_account_kind(enriched)
    enriched["card_system"] = derive_card_system(enriched)
    return enriched


class DataCollector:
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

    @property
    def schema(self) -> str:
        return self.config.schema

    def execute_query(
        self,
        query: str,
        params: tuple[Any, ...] | list[Any] | None = None,
        *,
        fetchone: bool = False,
    ):
        with self.connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, tuple(params or ()))
                return cur.fetchone() if fetchone else cur.fetchall()

    def fetch_sessions_to_json(
        self,
        user_id: int,
        json_file_path: str = "C:/project_kicb/Backend_grpc_requests/web_transfer_transactions/data/session_data.json",
    ) -> str:
        """Получает первую активную сессию пользователя и сохраняет результат в JSON файл."""
        result = self.get_session_record(user_id=user_id, offset=0)
        json_data = json.dumps(result, ensure_ascii=False, indent=4)

        with open(json_file_path, "w", encoding="utf-8") as file:
            file.write(json_data)

        return json_data

    def get_session_record(self, user_id: int, offset: int = 0) -> Dict[str, Any] | None:
        with self.connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT session_key, session_id, created_at
                    FROM {self.schema}.sessions
                    WHERE user_id = %s AND is_valid = true
                    ORDER BY created_at DESC
                    LIMIT 1 OFFSET %s
                    """,
                    (user_id, offset),
                )
                return cur.fetchone()

    def get_valid_session_key(self, user_id: int = 134, offset: int = 0) -> str:
        """Получает валидный сессионный ключ по user_id."""
        try:
            result = self.get_session_record(user_id=user_id, offset=offset)
            return result["session_key"] if result else None
        except Exception as e:
            print(f"Ошибка при получении сессионного ключа: {str(e)}")
            return None

    def get_user_id_by_customer_no(self, customer_no: str) -> int | None:
        with self.connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT id
                    FROM {self.schema}.users
                    WHERE customer_no = %s
                    ORDER BY updated_at DESC NULLS LAST, id DESC
                    LIMIT 1
                    """,
                    (customer_no,),
                )
                result = cur.fetchone()
                return result["id"] if result else None

    def get_valid_session_key_by_customer_no(self, customer_no: str, offset: int = 0) -> str | None:
        user_id = self.get_user_id_by_customer_no(customer_no)
        if user_id is None:
            return None
        return self.get_valid_session_key(user_id=user_id, offset=offset)

    def get_accounts_by_customer_and_account_no(self, customer_no: str, account_no: str) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT
                        a.id,
                        a.customer_no,
                        a.account_no,
                        a.ccy,
                        a.destination,
                        a.is_default,
                        a.account_class,
                        a.ipc_card_base_supp,
                        a.ac_stat_dormant,
                        a.ac_stat_no_dr,
                        a.ac_stat_no_cr,
                        a.ac_stat_block,
                        a.ac_stat_frozen,
                        a.record_stat,
                        a.acy_withdrawable_bal,
                        a.ipc_card_pan,
                        ac.description AS account_class_description,
                        ac.account_class_group,
                        ac.customer_type
                    FROM {self.schema}.accounts a
                    LEFT JOIN {self.schema}.account_classes ac ON ac.account_class_id = a.account_class
                    WHERE a.customer_no = %s AND a.account_no = %s
                    ORDER BY a.is_default DESC NULLS LAST, a.id
                    """,
                    (customer_no, account_no),
                )
                return [enrich_account_runtime(row) for row in cur.fetchall()]

    def get_accounts_by_customer_no(self, customer_no: str) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT
                        a.id,
                        a.customer_no,
                        a.account_no,
                        a.ccy,
                        a.destination,
                        a.is_default,
                        a.account_class,
                        a.ipc_card_base_supp,
                        a.ac_stat_dormant,
                        a.record_stat,
                        a.acy_withdrawable_bal,
                        a.ipc_card_pan,
                        ac.description AS account_class_description,
                        ac.account_class_group,
                        ac.customer_type
                    FROM {self.schema}.accounts a
                    LEFT JOIN {self.schema}.account_classes ac ON ac.account_class_id = a.account_class
                    WHERE a.customer_no = %s
                    ORDER BY a.is_default DESC NULLS LAST, a.account_no, a.id
                    """,
                    (customer_no,),
                )
                return [enrich_account_runtime(row) for row in cur.fetchall()]

    def get_account_balance(
        self,
        *,
        account_id: int | None = None,
        account_no: str | None = None,
        customer_no: str | None = None,
    ):
        filters = []
        params: list[Any] = []

        if account_id is not None:
            filters.append("id = %s")
            params.append(account_id)
        if account_no is not None:
            filters.append("account_no = %s")
            params.append(account_no)
        if customer_no is not None:
            filters.append("customer_no = %s")
            params.append(customer_no)

        if not filters:
            raise ValueError("Нужно передать account_id или account_no для поиска баланса")

        where_clause = " AND ".join(filters)
        with self.connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT acy_withdrawable_bal
                    FROM {self.schema}.accounts
                    WHERE {where_clause}
                    ORDER BY is_default DESC NULLS LAST, id
                    LIMIT 1
                    """,
                    tuple(params),
                )
                result = cur.fetchone()
                return result["acy_withdrawable_bal"] if result else None

    def get_transaction_by_operation_id(self, operation_id: str) -> Dict[str, Any] | None:
        with self.connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT
                        id,
                        operation_id,
                        txn_code,
                        txn_type,
                        txn_status_internal,
                        txn_status_external,
                        cbs_reference,
                        error_code,
                        err_desc,
                        backend_err_code,
                        add_text,
                        confirmed_at,
                        end_at,
                        account_debit_id,
                        account_debit_no,
                        account_debit_ccy,
                        account_credit_id,
                        account_credit_no,
                        account_credit_ccy,
                        account_credit_prop_value,
                        account_credit_prop_type,
                        amount_debit,
                        amount_debit_total,
                        amount_credit,
                        customer_no_debit,
                        customer_no_credit,
                        payment_purpose,
                        exchange_rate,
                        value_date,
                        service_provider_id,
                        prop_value,
                        recipient_bank_bic,
                        recipient_name,
                        clearing_recipient_acc_no,
                        recipient_bank_swift,
                        swift_recipient_acc_no,
                        swift_transfer_ccy,
                        swift_commission_type,
                        payment_code,
                        created_at,
                        updated_at
                    FROM {self.schema}.transactions
                    WHERE operation_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (operation_id,),
                )
                return cur.fetchone()

    def get_transaction_statement_by_reference(self, reference_no: str) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT
                        trn_ref_no,
                        account_no,
                        customer_no,
                        dr,
                        cr,
                        contra_ac,
                        details,
                        trn_code,
                        created_at
                    FROM {self.schema}.transaction_statement
                    WHERE trn_ref_no = %s
                    ORDER BY created_at DESC, id DESC
                    """,
                    (reference_no,),
                )
                return cur.fetchall()

# Пример использования:
if __name__ == "__main__":
    config = DatabaseConfig()
    collector = DataCollector(config)
    json_data = collector.fetch_sessions_to_json(user_id=1)
    print(json_data)
