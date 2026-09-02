#!/usr/bin/env bash
# ==============================================================================
# SKY EXCHANGE - Ubuntu Server Automated Setup & Deployment Script
# Tested on: Ubuntu 20.04 LTS, 22.04 LTS, 24.04 LTS
# ==============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}====================================================${NC}"
echo -e "${GREEN}       SKY EXCHANGE Ubuntu Server Auto-Deploy       ${NC}"
echo -e "${GREEN}====================================================${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Error: Please run this script as root or with sudo.${NC}"
  exit 1
fi

# Prompt for Database Configuration
read -p "Enter Database User [default: sky_user]: " DB_USER
DB_USER=${DB_USER:-sky_user}

read -sp "Enter Database Password for ${DB_USER}: " DB_PASS
echo ""
if [ -z "$DB_PASS" ]; then
  echo -e "${RED}Error: Database password cannot be empty.${NC}"
  exit 1
fi

read -p "Enter Database Name [default: sky_exchange]: " DB_NAME
DB_NAME=${DB_NAME:-sky_exchange}

read -p "Enter Domain Name or Public IP (e.g. exchange.yourdomain.com): " DOMAIN_NAME
if [ -z "$DOMAIN_NAME" ]; then
  echo -e "${RED}Error: Domain name or Public IP is required.${NC}"
  exit 1
fi

PROJECT_DIR="/var/www/sky_exchange"
CURRENT_DIR=$(pwd)

echo -e "\n${YELLOW}[1/7] Updating system packages...${NC}"
apt-get update && apt-get upgrade -y
apt-get install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx certbot python3-certbot-nginx ufw git curl

echo -e "\n${YELLOW}[2/7] Setting up PostgreSQL Database...${NC}"
systemctl start postgresql
systemctl enable postgresql

# Create DB and User if they don't exist
sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';" 2>/dev/null || echo "User ${DB_USER} already exists."
sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};" 2>/dev/null || echo "Database ${DB_NAME} already exists."
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"

# Allow remote connections to PostgreSQL on port 5432 for Desktop app access
PG_VER=$(psql -V | awk '{print $3}' | cut -d. -f1)
PG_CONF=$(find /etc/postgresql/ -name "postgresql.conf" | head -n 1)
PG_HBA=$(find /etc/postgresql/ -name "pg_hba.conf" | head -n 1)

if [ -f "$PG_CONF" ]; then
  sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/g" "$PG_CONF"
  sed -i "s/listen_addresses = 'localhost'/listen_addresses = '*'/g" "$PG_CONF"
fi

if [ -f "$PG_HBA" ]; then
  if ! grep -q "0.0.0.0/0" "$PG_HBA"; then
    echo "host    all             all             0.0.0.0/0               scram-sha-256" >> "$PG_HBA"
  fi
fi

systemctl restart postgresql

echo -e "\n${YELLOW}[3/7] Setting up Application Directory...${NC}"
mkdir -p "$PROJECT_DIR"

if [ "$CURRENT_DIR" != "$PROJECT_DIR" ]; then
  echo "Copying application files to $PROJECT_DIR..."
  cp -r "$CURRENT_DIR"/* "$PROJECT_DIR"/ 2>/dev/null || true
fi

cd "$PROJECT_DIR"

# Ensure upload directory exists with proper permissions
mkdir -p collector_web/static/uploads
chown -r www-data:www-data "$PROJECT_DIR"
chmod -r 775 "$PROJECT_DIR"/collector_web/static/uploads

echo -e "\n${YELLOW}[4/7] Setting up Python Virtual Environment...${NC}"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install gunicorn

# Generate .env file
cat <<EOF > "$PROJECT_DIR/.env"
DATABASE_URL=postgresql://${DB_USER}:${DB_PASS}@127.0.0.1:5432/${DB_NAME}
COLLECTOR_WEB_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(24))")
EOF

cp "$PROJECT_DIR/.env" "$PROJECT_DIR/env"
chmod 600 "$PROJECT_DIR/.env" "$PROJECT_DIR/env"

echo -e "\n${YELLOW}[5/7] Configuring Systemd Service (skyexchange.service)...${NC}"
cat <<EOF > /etc/systemd/system/skyexchange.service
[Unit]
Description=SKY EXCHANGE Web Application (Gunicorn)
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=${PROJECT_DIR}
Environment="PATH=${PROJECT_DIR}/.venv/bin"
EnvironmentFile=${PROJECT_DIR}/.env
ExecStart=${PROJECT_DIR}/.venv/bin/gunicorn --workers 4 --bind 127.0.0.1:5001 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable skyexchange
systemctl restart skyexchange

echo -e "\n${YELLOW}[6/7] Configuring Nginx Reverse Proxy...${NC}"
cat <<EOF > /etc/nginx/sites-available/skyexchange
server {
    listen 80;
    server_name ${DOMAIN_NAME};

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static/ {
        alias ${PROJECT_DIR}/collector_web/static/;
        expires 30d;
    }
}
EOF

ln -sf /etc/nginx/sites-available/skyexchange /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default || true
nginx -t
systemctl restart nginx

echo -e "\n${YELLOW}[7/7] Firewall Configuration...${NC}"
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 5432/tcp
ufw --force enable || true

echo -e "\n${GREEN}====================================================${NC}"
echo -e "${GREEN}  SKY EXCHANGE Web & Database setup completed!       ${NC}"
echo -e "${GREEN}====================================================${NC}"
echo -e "Web App URL: http://${DOMAIN_NAME}"
echo -e "PostgreSQL Connection String for Desktop PCs:"
echo -e "  postgresql://${DB_USER}:${DB_PASS}@SERVER_PUBLIC_IP:5432/${DB_NAME}"
echo -e "\nTo setup SSL Certificate (HTTPS), run:"
echo -e "  sudo certbot --nginx -d ${DOMAIN_NAME}"
echo -e "${GREEN}====================================================${NC}"
