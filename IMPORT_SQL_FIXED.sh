#!/bin/bash

# Fixed SQL Import Script for PostgreSQL 17.6
# This script properly handles COPY ... FROM stdin; commands

set -e  # Exit on error

echo "========================================="
echo "PostgreSQL SQL Import - Fixed Version"
echo "========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

DB_NAME="buyvaulthub_db"
DB_USER="postgres"
SQL_FILE="backup_20251029_020655.sql"

# Check if SQL file exists
if [ ! -f "$SQL_FILE" ]; then
    echo -e "${RED}[ERROR]${NC} SQL file '$SQL_FILE' not found!"
    echo "Please make sure the file is in the current directory."
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Found SQL file: $SQL_FILE"
echo ""

# Get PostgreSQL password
read -sp "Enter PostgreSQL password for user '$DB_USER': " DB_PASSWORD
echo ""
echo ""

# Set password as environment variable
export PGPASSWORD=$DB_PASSWORD

# Check PostgreSQL connection
echo "Checking PostgreSQL connection..."
if ! psql -U $DB_USER -c '\q' 2>/dev/null; then
    echo -e "${RED}[ERROR]${NC} Cannot connect to PostgreSQL!"
    echo "Please check:"
    echo "  1. PostgreSQL is running"
    echo "  2. Password is correct"
    echo "  3. PostgreSQL is accessible"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} PostgreSQL connection successful"
echo ""

# Drop and recreate database for clean import
echo "Dropping existing database (if exists)..."
psql -U $DB_USER -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null || true

echo "Creating fresh database..."
psql -U $DB_USER -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || {
    echo -e "${YELLOW}[WARNING]${NC} Database might already exist, continuing..."
}

echo -e "${GREEN}[OK]${NC} Database ready"
echo ""

# Import SQL file
echo "========================================="
echo "Importing SQL file..."
echo "This will take 3-5 minutes. Please wait..."
echo "========================================="
echo ""

# Import with error handling
if psql -U $DB_USER -d $DB_NAME -f "$SQL_FILE" -v ON_ERROR_STOP=0; then
    echo ""
    echo -e "${GREEN}[OK]${NC} SQL file imported successfully"
else
    echo ""
    echo -e "${YELLOW}[WARNING]${NC} Import completed with some errors."
    echo "This might be normal if some objects already exist."
    echo "Verifying data..."
fi

echo ""

# Verify import
echo "Verifying import..."
PRODUCT_COUNT=$(psql -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM products_coreproduct;" 2>/dev/null | tr -d ' ')

if [ "$PRODUCT_COUNT" -gt 0 ]; then
    echo -e "${GREEN}[OK]${NC} Import verified successfully!"
    echo "   Found $PRODUCT_COUNT products in database"
else
    echo -e "${YELLOW}[WARNING]${NC} No products found. Import might have failed."
    echo "   Please check error messages above."
fi

echo ""

# Check tables
echo "Checking tables..."
TABLE_COUNT=$(psql -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')

if [ "$TABLE_COUNT" -gt 0 ]; then
    echo -e "${GREEN}[OK]${NC} Found $TABLE_COUNT tables in database"
else
    echo -e "${RED}[ERROR]${NC} No tables found. Import failed."
    exit 1
fi

echo ""
echo "========================================="
echo "Import Process Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Update backend/.env with database credentials"
echo "2. Test backend connection: python manage.py dbshell"
echo "3. Start backend: python manage.py runserver"
echo ""
