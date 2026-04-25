# SKY EXCHANGE Online Setup

This project can use one shared PostgreSQL database so multiple PCs work with the same data.

## 1. Create a new Supabase project

Create a brand new Supabase project for SKY EXCHANGE only.

Do not reuse the other project's database.

## 2. Copy the correct connection string

In Supabase, open your new project and click `Connect`.

For this desktop app, use the `Session pooler` connection string if your PCs are on normal IPv4 internet.

It looks like:

```text
postgresql://postgres.PROJECT_REF:[PASSWORD]@aws-REGION.pooler.supabase.com:5432/postgres
```

## 3. Create the local config file

Create a file named `env` in this project folder with:

```text
DATABASE_URL=postgresql://postgres.PROJECT_REF:[PASSWORD]@aws-REGION.pooler.supabase.com:5432/postgres
SQLITE_DB_PATH=newdata.db
ALLOW_SQLITE_FALLBACK=1
```

`SQLITE_DB_PATH=newdata.db` tells the migration which local file to upload.

## 4. Install requirements

```powershell
python -m pip install -r requirements.txt
```

## 5. Run the migration

```powershell
python migrate_sqlite_to_postgres.py
```

The migration script now:

- creates a timestamped backup of your SQLite file first
- refuses to run into a non-empty unrelated database
- refuses to overwrite existing SKY EXCHANGE data unless you explicitly allow it

## 6. Switch each PC to online mode

On every PC that should share the same data, use the same `DATABASE_URL` in its `env` file.

After that, the app will use PostgreSQL automatically.

## 7. Optional local fallback

If you want to force online-only mode later, remove this line:

```text
ALLOW_SQLITE_FALLBACK=1
```
