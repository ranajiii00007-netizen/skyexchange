import database


def main():
    conn = database.connect_db()
    cur = conn.cursor()
    cur.execute("SELECT 1")
    print("Database connection OK:", cur.fetchone()[0])
    print("Using PostgreSQL:", database.using_postgres())
    conn.close()


if __name__ == "__main__":
    main()
