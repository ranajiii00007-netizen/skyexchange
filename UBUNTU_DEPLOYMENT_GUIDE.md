# SKY EXCHANGE - Complete Ubuntu Server Deployment & Data Migration Guide

This guide details step-by-step instructions to deploy all **SKY EXCHANGE Web Portals** and host your own **PostgreSQL Database** on a private **Ubuntu Server**, guaranteeing **Zero Data Loss**.

---

## 🏗 Architecture Overview

```
                      +------------------------------------------+
                      |             UBUNTU SERVER                |
                      |                                          |
   Web Users -------->| Nginx (Port 80/443 SSL)                  |
   (Admin, Banker,    |    └─> Gunicorn WSGI                      |
    Collector,        |          └─> Flask App (Web Portals)     |
    Customer)         |                 │                        |
                      |                 ▼                        |
                      |          PostgreSQL DB (sky_exchange)    |
                      +-----------------▲------------------------+
                                        │
   Desktop App PCs ---------------------+ (PostgreSQL TCP Port 5432)
   (main.exe / main.py)
```

---

## STEP 1: Server Preparation & Automated Setup

### 1. Upload Project Files to your Ubuntu Server
Transfer the project folder to your Ubuntu server (e.g. via SCP, Git, or SFTP):
```bash
# Example using SCP from your local machine:
scp -r "C:\Users\rehan\Downloads\bakar project" root@YOUR_SERVER_IP:/var/www/sky_exchange
```

### 2. Run the Automated Setup Script
Connect to your Ubuntu server via SSH and execute `deploy_ubuntu.sh`:
```bash
ssh root@YOUR_SERVER_IP
cd /var/www/sky_exchange
chmod +x deploy_ubuntu.sh migrate_from_supabase.sh backup_postgres.sh
sudo ./deploy_ubuntu.sh
```

**The script automatically:**
- Installs Python 3, PostgreSQL, Nginx, Gunicorn, Certbot, Firewall.
- Creates the local PostgreSQL database `sky_exchange` and user `sky_user`.
- Configures PostgreSQL remote access on port `5432` for Desktop PCs.
- Configures Systemd background service (`skyexchange.service`).
- Configures Nginx reverse proxy for Web Portals.

---

## STEP 2: Zero Data Loss Migration

Choose the scenario that applies to your current setup:

### Scenario A: Migrating from Supabase (Recommended if currently on Supabase)

Run the automated migration tool:
```bash
cd /var/www/sky_exchange
./migrate_from_supabase.sh
```
- Paste your Supabase `DATABASE_URL` string when prompted.
- The script exports all schema, tables, rows, indexes, and primary key sequences from Supabase and imports them directly into your local Ubuntu PostgreSQL database.
- It prints a row-by-row verification table after completion.

---

### Scenario B: Migrating from Local SQLite (`newdata.db` or `exchange.db`)

If your main data is currently in a local SQLite file:
1. Ensure `newdata.db` or `exchange.db` is present in `/var/www/sky_exchange`.
2. Run the Python migration tool:
```bash
cd /var/www/sky_exchange
.venv/bin/python migrate_sqlite_to_postgres.py --allow-nonempty
```
- This script creates a timestamped backup before migrating.
- It inserts all records and resets PostgreSQL sequences (`setval`) automatically.

---

## STEP 3: Setup HTTPS / SSL Certificate (Free with Certbot)

If you pointed a domain name (e.g., `exchange.yourdomain.com`) to your server IP:
```bash
sudo certbot --nginx -d exchange.yourdomain.com
```
Follow the prompts. Certbot will automatically issue and install an SSL certificate and set up automatic renewal.

---

## STEP 4: Update Desktop Application PCs

On every Windows PC running the desktop app (`main.exe` / `main.py`):

1. Open the `env` file inside the desktop app folder.
2. Update `DATABASE_URL` to point to your Ubuntu Server:
```text
DATABASE_URL=postgresql://sky_user:YOUR_PASSWORD@YOUR_SERVER_IP:5432/sky_exchange
```
3. Launch `main.exe`. The desktop app will instantly connect to your self-hosted database and sync live with all web portals!

---

## STEP 5: Automated Daily Backups

Set up automated daily database backups on the server:

```bash
sudo cp /var/www/sky_exchange/backup_postgres.sh /etc/cron.daily/sky_exchange_backup
sudo chmod +x /etc/cron.daily/sky_exchange_backup
```
Daily compressed backups will automatically be saved to `/var/backups/sky_exchange/` and kept for 30 days.

---

## 🔍 Service Management Commands

- **Check Web App Status**:
  ```bash
  sudo systemctl status skyexchange
  ```
- **Restart Web App**:
  ```bash
  sudo systemctl restart skyexchange
  ```
- **View Web App Logs**:
  ```bash
  sudo journalctl -u skyexchange -f
  ```
- **Check Nginx Logs**:
  ```bash
  sudo tail -f /var/log/nginx/error.log
  ```
- **Check PostgreSQL Status**:
  ```bash
  sudo systemctl status postgresql
  ```
