import argparse
import os
import sys
from datetime import date

from werkzeug.security import generate_password_hash


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import database  # noqa: E402


def create_user(collector_name, username, password):
    database.create_tables()
    conn = database.connect_db(reuse_postgres=False)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO collector_users (collector_name, username, password_hash, status, created_at)
        VALUES (?, ?, ?, 1, ?)
        """,
        (
            collector_name,
            username,
            generate_password_hash(password),
            str(date.today()),
        ),
    )
    conn.commit()
    conn.close()
    print(f"Created collector login for {collector_name}: {username}")


def list_users():
    database.create_tables()
    conn = database.connect_db(reuse_postgres=False)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT collector_name, username, status, created_at
        FROM collector_users
        ORDER BY collector_name, username
        """
    )
    for collector_name, username, status, created_at in cur.fetchall():
        print(f"{username} | {collector_name} | status={status} | created={created_at}")
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Manage collector web logins.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("collector_name")
    create_parser.add_argument("username")
    create_parser.add_argument("password")

    subparsers.add_parser("list")

    args = parser.parse_args()
    if args.command == "create":
        create_user(args.collector_name, args.username, args.password)
    elif args.command == "list":
        list_users()


if __name__ == "__main__":
    main()
