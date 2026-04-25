import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

import database


TABLES = [
    "currencies",
    "currency_rates",
    "banker_currencies",
    "banker_currency_rates",
    "customers",
    "collectors",
    "bankers",
    "transactions",
    "banker_payments",
]

APP_TABLES = TABLES + ["collector_users"]


def get_columns(cur, table_name):
    cur.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cur.fetchall()]


def table_exists(cur, table_name):
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cur.fetchone() is not None


def reset_postgres_sequence(cur, table_name):
    cur.execute(
        """
        SELECT setval(
            pg_get_serial_sequence(%s, 'id'),
            COALESCE((SELECT MAX(id) FROM """ + table_name + """), 1),
            (SELECT COUNT(*) > 0 FROM """ + table_name + """)
        )
        """,
        (table_name,),
    )


def fetch_remote_table_names(cur):
    cur.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema='public'
        ORDER BY table_name
        """
    )
    return [row[0] for row in cur.fetchall()]


def fetch_remote_row_counts(cur, table_names):
    counts = {}
    for table_name in table_names:
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        counts[table_name] = cur.fetchone()[0]
    return counts


def ensure_safe_target(cur, allow_nonempty):
    remote_tables = fetch_remote_table_names(cur)
    sky_tables_present = [name for name in APP_TABLES if name in remote_tables]
    non_sky_tables = [name for name in remote_tables if name not in APP_TABLES]

    if non_sky_tables and not allow_nonempty:
        sample = ", ".join(non_sky_tables[:8])
        raise SystemExit(
            "Target database is not empty and contains unrelated tables: "
            f"{sample}. Use a fresh database/project for SKY EXCHANGE."
        )

    if sky_tables_present and not allow_nonempty:
        counts = fetch_remote_row_counts(cur, sky_tables_present)
        nonempty = {name: count for name, count in counts.items() if count}
        if nonempty:
            details = ", ".join(f"{name}={count}" for name, count in nonempty.items())
            raise SystemExit(
                "Target database already has SKY EXCHANGE data: "
                f"{details}. Refusing to overwrite it."
            )


def backup_sqlite_file(sqlite_path):
    source = Path(sqlite_path)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = source.with_name(f"{source.stem}-backup-{timestamp}{source.suffix}")
    shutil.copy2(source, backup_path)
    return backup_path


def migrate_table(sqlite_cur, pg_cur, table_name):
    if not table_exists(sqlite_cur, table_name):
        print(f"Skipping missing table: {table_name}")
        return 0

    sqlite_columns = get_columns(sqlite_cur, table_name)
    pg_columns = get_columns(pg_cur, table_name)
    columns = [column for column in sqlite_columns if column in pg_columns]

    if not columns:
        print(f"Skipping table with no matching columns: {table_name}")
        return 0

    column_list = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)

    sqlite_cur.execute(f"SELECT {column_list} FROM {table_name}")
    rows = sqlite_cur.fetchall()

    pg_cur.execute(f"DELETE FROM {table_name}")
    if rows:
        insert_sql = f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})"
        for row in rows:
            pg_cur.execute(insert_sql, row)

    reset_postgres_sequence(pg_cur, table_name)
    print(f"Migrated {len(rows)} rows into {table_name}")
    return len(rows)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Safely migrate SKY EXCHANGE SQLite data into PostgreSQL."
    )
    parser.add_argument(
        "--source-db",
        default=database.DB_NAME,
        help="SQLite source file to migrate. Defaults to SQLITE_DB_PATH/exchange.db.",
    )
    parser.add_argument(
        "--allow-nonempty-target",
        action="store_true",
        help="Allow migration into a database that already has tables/data.",
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip the automatic local SQLite backup before migration.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not database.using_postgres():
        raise SystemExit("Set DATABASE_URL before running this migration.")

    sqlite_path = Path(args.source_db).resolve()
    if not sqlite_path.exists():
        raise SystemExit(f"SQLite source file not found: {sqlite_path}")

    if not args.skip_backup:
        backup_path = backup_sqlite_file(sqlite_path)
        print(f"Created SQLite backup: {backup_path}")

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_cur = sqlite_conn.cursor()

    pg_conn = database.connect_db(reuse_postgres=False)
    pg_cur = pg_conn.cursor()

    try:
        ensure_safe_target(pg_cur, allow_nonempty=args.allow_nonempty_target)
        database.create_tables()

        total_rows = 0
        for table_name in TABLES:
            total_rows += migrate_table(sqlite_cur, pg_cur, table_name)

        pg_conn.commit()
    except Exception:
        pg_conn.rollback()
        raise
    finally:
        pg_conn.close()
        sqlite_conn.close()

    print(f"Migration complete. Total migrated rows: {total_rows}")


if __name__ == "__main__":
    main()
