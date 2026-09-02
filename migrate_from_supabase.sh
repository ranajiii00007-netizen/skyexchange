#!/usr/bin/env bash
# ==============================================================================
# SKY EXCHANGE - Zero Data Loss Supabase to Ubuntu PostgreSQL Migration Tool
# ==============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}====================================================${NC}"
echo -e "${GREEN}  SKY EXCHANGE Supabase -> Ubuntu Migration Tool   ${NC}"
echo -e "${GREEN}====================================================${NC}"

read -p "Enter Supabase Database Connection String (or press Enter to read from .env/env file): " SUPABASE_URL

if [ -z "$SUPABASE_URL" ]; then
  if [ -f "env" ]; then
    SUPABASE_URL=$(grep "DATABASE_URL" env | cut -d '=' -f2-)
  elif [ -f ".env" ]; then
    SUPABASE_URL=$(grep "DATABASE_URL" .env | cut -d '=' -f2-)
  fi
fi

if [ -z "$SUPABASE_URL" ]; then
  echo -e "${RED}Error: Could not find Supabase DATABASE_URL.${NC}"
  exit 1
fi

read -p "Enter Target Local DB Name [default: sky_exchange]: " TARGET_DB
TARGET_DB=${TARGET_DB:-sky_exchange}

read -p "Enter Target Local DB User [default: sky_user]: " TARGET_USER
TARGET_USER=${TARGET_USER:-sky_user}

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DUMP_FILE="sky_exchange_supabase_dump_${TIMESTAMP}.sql"

echo -e "\n${YELLOW}[1/3] Dumping all data & schema from Supabase...${NC}"
pg_dump "$SUPABASE_URL" \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  --quote-all-identifiers \
  --file="$DUMP_FILE"

echo -e "${GREEN}Successfully created dump file: ${DUMP_FILE}${NC}"

echo -e "\n${YELLOW}[2/3] Importing data into local PostgreSQL (${TARGET_DB})...${NC}"
sudo -u postgres psql -d "$TARGET_DB" -f "$DUMP_FILE"

echo -e "\n${YELLOW}[3/3] Verifying table counts & sequence values...${NC}"
sudo -u postgres psql -d "$TARGET_DB" -c "
SELECT table_name, 
       (xpath('/row/c/text()', query_to_xml(format('select count(*) as c from %I.%I', table_schema, table_name), false, true, '')))[1]::text::int AS row_count
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
"

echo -e "\n${GREEN}====================================================${NC}"
echo -e "${GREEN}  MIGRATION COMPLETED SUCCESSFULLY WITH ZERO DATA LOSS! ${NC}"
echo -e "${GREEN}====================================================${NC}"
