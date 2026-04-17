import os
import re
import sqlite3
import sys
import time


if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_NAME = os.path.join(BASE_DIR, "exchange.db")


def _load_env_file():
    for filename in (".env", "env"):
        path = os.path.join(BASE_DIR, filename)
        if not os.path.exists(path):
            continue

        with open(path, "r", encoding="utf-8") as file_obj:
            for line in file_obj:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)


_load_env_file()
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip().strip('"').strip("'")
_POSTGRES_CONNECTION = None


def using_postgres():
    return DATABASE_URL.startswith(("postgres://", "postgresql://"))


def _require_psycopg():
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(
            "DATABASE_URL is set for PostgreSQL, but the psycopg package is not "
            f"installed for this Python: {sys.executable}. "
            "Run: python -m pip install -r requirements.txt"
        ) from exc

    return psycopg


def _sqlite_connect():
    conn = sqlite3.connect(DB_NAME, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def connect_db(reuse_postgres=True):
    if using_postgres():
        psycopg = _require_psycopg()
        if reuse_postgres:
            global _POSTGRES_CONNECTION
            if _POSTGRES_CONNECTION is None or _POSTGRES_CONNECTION.closed:
                _POSTGRES_CONNECTION = psycopg.connect(
                    DATABASE_URL,
                    sslmode="require",
                    connect_timeout=10,
                )
                with _POSTGRES_CONNECTION.cursor() as cur:
                    cur.execute("SET statement_timeout = '15s'")
                _POSTGRES_CONNECTION.commit()

            conn = _POSTGRES_CONNECTION
            return PostgresConnection(conn, keep_open=True)

        conn = psycopg.connect(
                DATABASE_URL,
                sslmode="require",
                connect_timeout=10,
            )
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '15s'")
        conn.commit()
        return PostgresConnection(conn, keep_open=False)

    return _sqlite_connect()


class PostgresConnection:
    def __init__(self, conn, keep_open=True):
        self._conn = conn
        self._keep_open = keep_open

    def cursor(self):
        return PostgresCursor(self._conn, self._conn.cursor())

    def execute(self, query, params=None):
        cur = self.cursor()
        cur.execute(query, params)
        return cur

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        # Keep one online connection alive for the desktop app. Opening a fresh
        # SSL connection to Supabase for every dropdown/search is very slow.
        if self._keep_open:
            return None
        return self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)


class PostgresCursor:
    def __init__(self, conn, cursor):
        self._conn = conn
        self._cursor = cursor
        self._manual_rows = None

    def execute(self, query, params=None):
        self._manual_rows = None
        pragma_match = re.match(r"\s*PRAGMA\s+table_info\((\w+)\)\s*$", query, re.I)

        if pragma_match:
            table_name = pragma_match.group(1)
            try:
                self._cursor.execute(
                    """
                    SELECT ordinal_position - 1, column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    (table_name,),
                )
            except Exception:
                self._conn.rollback()
                raise
            self._manual_rows = [
                (position, column_name, None, None, None, None)
                for position, column_name in self._cursor.fetchall()
            ]
            return self

        query = _translate_sqlite_query(query)
        start_time = time.perf_counter()
        try:
            self._cursor.execute(query, params)
        except Exception:
            self._conn.rollback()
            raise
        elapsed = time.perf_counter() - start_time
        if elapsed > 2:
            preview = " ".join(query.split())[:180]
            print(f"Slow database query ({elapsed:.1f}s): {preview}")
        return self

    def fetchone(self):
        if self._manual_rows is not None:
            return self._manual_rows.pop(0) if self._manual_rows else None
        return self._cursor.fetchone()

    def fetchall(self):
        if self._manual_rows is not None:
            rows = self._manual_rows
            self._manual_rows = []
            return rows
        return self._cursor.fetchall()

    def __iter__(self):
        return iter(self.fetchall())

    def __getattr__(self, name):
        return getattr(self._cursor, name)


def _translate_sqlite_query(query):
    query = _translate_insert_or_replace(query)
    query = query.replace("?", "%s")
    return query


def _translate_insert_or_replace(query):
    normalized = " ".join(query.split())

    if normalized.lower().startswith("insert or replace into currency_rates"):
        return """
        INSERT INTO currency_rates (currency_code, base_currency, rate, rate_date)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (currency_code, rate_date)
        DO UPDATE SET
            base_currency = EXCLUDED.base_currency,
            rate = EXCLUDED.rate
        """

    if normalized.lower().startswith("insert or replace into banker_currency_rates"):
        return """
        INSERT INTO banker_currency_rates (banker_name, currency_code, rate, rate_date)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (banker_name, currency_code, rate_date)
        DO UPDATE SET rate = EXCLUDED.rate
        """

    return query


def _id_column_type():
    return "SERIAL PRIMARY KEY" if using_postgres() else "INTEGER PRIMARY KEY AUTOINCREMENT"


def _column_exists(cur, table_name, column_name):
    cur.execute(f"PRAGMA table_info({table_name})")
    return column_name in {row[1] for row in cur.fetchall()}


def create_tables():
    conn = connect_db()
    cur = conn.cursor()
    id_type = _id_column_type()

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS banker_payments (
        id {id_type},
        banker_name TEXT,
        paid_usd REAL,
        payment_date TEXT
    )
    """)

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS currencies (
        id {id_type},
        name TEXT NOT NULL,
        code TEXT NOT NULL UNIQUE,
        status INTEGER DEFAULT 1
    )
    """)

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS currency_rates (
        id {id_type},
        currency_code TEXT NOT NULL,
        base_currency TEXT NOT NULL,
        rate REAL NOT NULL,
        rate_date TEXT NOT NULL,
        UNIQUE(currency_code, rate_date)
    )
    """)

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS banker_currencies (
        id {id_type},
        banker_name TEXT NOT NULL,
        currency_code TEXT NOT NULL,
        UNIQUE(banker_name, currency_code)
    )
    """)

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS banker_currency_rates (
        id {id_type},
        banker_name TEXT NOT NULL,
        currency_code TEXT NOT NULL,
        rate REAL NOT NULL,
        rate_date TEXT NOT NULL,
        UNIQUE(banker_name, currency_code, rate_date)
    )
    """)

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS customers (
        id {id_type},
        name TEXT NOT NULL,
        phone TEXT,
        phone2 TEXT,
        phone3 TEXT,
        address TEXT,
        reference TEXT,
        country TEXT,
        status INTEGER DEFAULT 1,
        created_at TEXT
    )
    """)

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS collectors (
        id {id_type},
        name TEXT NOT NULL,
        phone TEXT,
        area TEXT,
        status INTEGER DEFAULT 1,
        created_at TEXT
    )
    """)

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS bankers (
        id {id_type},
        name TEXT NOT NULL,
        phone TEXT,
        bank_name TEXT,
        city TEXT,
        status INTEGER DEFAULT 1,
        created_at TEXT
    )
    """)

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS collector_users (
        id {id_type},
        collector_name TEXT NOT NULL,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        status INTEGER DEFAULT 1,
        created_at TEXT
    )
    """)

    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS transactions (
        id {id_type},
        customer_name TEXT NOT NULL,
        collector_name TEXT,
        banker_name TEXT,
        target_currency TEXT NOT NULL,
        exchange_rate REAL NOT NULL,
        eur_expected REAL NOT NULL,
        eur_received REAL NOT NULL,
        pending_eur REAL NOT NULL,
        foreign_amount REAL NOT NULL,
        status TEXT NOT NULL,
        deal_date TEXT NOT NULL,
        notes TEXT,
        transaction_type TEXT NOT NULL DEFAULT 'REGULAR'
    )
    """)

    if not _column_exists(cur, "transactions", "received_date"):
        cur.execute("ALTER TABLE transactions ADD COLUMN received_date TEXT")

    if not _column_exists(cur, "transactions", "transaction_type"):
        cur.execute(
            """
            ALTER TABLE transactions
            ADD COLUMN transaction_type TEXT NOT NULL DEFAULT 'REGULAR'
            """
        )

    if not _column_exists(cur, "banker_payments", "total_usd_snapshot"):
        cur.execute("ALTER TABLE banker_payments ADD COLUMN total_usd_snapshot REAL DEFAULT 0")

    if not _column_exists(cur, "banker_payments", "remaining_usd_snapshot"):
        cur.execute("ALTER TABLE banker_payments ADD COLUMN remaining_usd_snapshot REAL DEFAULT 0")

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_currency_rates
    ON currency_rates(currency_code, rate_date)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_banker_currency
    ON banker_currency_rates(banker_name, currency_code)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_transactions_date
    ON transactions(deal_date)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_transactions_customer
    ON transactions(customer_name)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_transactions_collector
    ON transactions(collector_name)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_transactions_date_type
    ON transactions(deal_date, transaction_type)
    """)

    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_collector_users_collector
    ON collector_users(collector_name)
    """)

    conn.commit()
    conn.close()
