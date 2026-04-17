# Collector Web Portal

This is a separate Flask web app for collectors. It uses the same `DATABASE_URL`
as the desktop admin app, so both apps read and write the same online database.

## Run Locally

From the project root:

```powershell
.venv\Scripts\python.exe collector_web\app.py
```

Open:

```text
http://127.0.0.1:5001
```

## Create Collector Logins

Collectors cannot sign up themselves. Office/admin creates their login from:

```text
http://127.0.0.1:5001/admin
```

Default local admin password:

```text
admin123
```

Set `COLLECTOR_ADMIN_PASSWORD` before deployment.

You can also create logins from the command line:

```powershell
.venv\Scripts\python.exe collector_web\manage_collectors.py create "Ali Raza" ali.raza "StrongPassword123"
```

List existing collector logins:

```powershell
.venv\Scripts\python.exe collector_web\manage_collectors.py list
```

## Current Collector Permissions

Collectors can:

- log in
- view their own pending transactions
- search by customer or currency
- record received EUR amounts
- view their recently received transactions

Collectors cannot:

- create accounts
- see other collectors' transactions
- delete transactions
- edit customers, bankers, currencies, or rates
- open admin reports
