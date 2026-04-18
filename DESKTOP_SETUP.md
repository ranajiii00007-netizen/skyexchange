# Desktop App Setup

Use this when sending the desktop app to another PC.

## Required Files

Put these files in the same folder:

```text
main.exe
env
```

The `env` file must contain:

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
```

Use the same `DATABASE_URL` on every PC. That is what makes all users share the
same online database.

## Do Not Send

Do not send these files as the shared database:

```text
exchange.db
exchange.db-shm
exchange.db-wal
```

Those are local SQLite files. The shared database is PostgreSQL online.

## Internet

The app needs internet access. If internet is unavailable, it cannot connect to
the online database.

## Local Developer Mode

Only for testing without the online database:

```text
ALLOW_SQLITE_FALLBACK=1
```

Do not enable this for normal office users, or they may create a private local
database by mistake.
