import sqlite3

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


def main():
    if not database.using_postgres():
        raise SystemExit("Set DATABASE_URL before running this migration.")

    database.create_tables()

    sqlite_conn = sqlite3.connect(database.DB_NAME)
    sqlite_cur = sqlite_conn.cursor()

    pg_conn = database.connect_db()
    pg_cur = pg_conn.cursor()

    for table_name in TABLES:
        if not table_exists(sqlite_cur, table_name):
            print(f"Skipping missing table: {table_name}")
            continue

        sqlite_columns = get_columns(sqlite_cur, table_name)
        pg_columns = get_columns(pg_cur, table_name)
        columns = [column for column in sqlite_columns if column in pg_columns]

        if not columns:
            print(f"Skipping table with no matching columns: {table_name}")
            continue

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

    pg_conn.commit()
    pg_conn.close()
    sqlite_conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    main()
