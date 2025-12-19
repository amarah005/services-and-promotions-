#!/bin/bash

# Database Setup Script for BuyVaultHub
# This script sets up the PostgreSQL database using the SQL backup file

set -e  # Exit on error

echo "========================================="
echo "BuyVaultHub Database Setup"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
DB_NAME="buyvaulthub_db"
DB_USER="postgres"
DB_HOST="localhost"
DB_PORT="5432"
SQL_FILE="backup_20251029_020655.sql"

# Check if SQL file exists
if [ ! -f "$SQL_FILE" ]; then
    echo -e "${RED}Error: SQL file '$SQL_FILE' not found!${NC}"
    echo "Please make sure the SQL backup file is in the project root directory."
    exit 1
fi

echo -e "${GREEN}✓${NC} Found SQL file: $SQL_FILE"
echo ""

# Prompt for database password
read -sp "Enter PostgreSQL password for user '$DB_USER': " DB_PASSWORD
echo ""
echo ""

# Check if PostgreSQL is running
echo "Checking PostgreSQL connection..."
if ! PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c '\q' 2>/dev/null; then
    echo -e "${RED}Error: Cannot connect to PostgreSQL!${NC}"
    echo "Please make sure:"
    echo "  1. PostgreSQL is installed and running"
    echo "  2. The password is correct"
    echo "  3. PostgreSQL is accessible on $DB_HOST:$DB_PORT"
    exit 1
fi

echo -e "${GREEN}✓${NC} PostgreSQL connection successful"
echo ""

# Check if database exists
echo "Checking if database '$DB_NAME' exists..."
if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
    echo -e "${YELLOW}⚠${NC} Database '$DB_NAME' already exists"
    read -p "Do you want to drop and recreate it? (y/N): " RECREATE
    if [[ $RECREATE =~ ^[Yy]$ ]]; then
        echo "Dropping existing database..."
        PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c "DROP DATABASE IF EXISTS $DB_NAME;"
        echo -e "${GREEN}✓${NC} Database dropped"
    else
        echo "Skipping database creation. Using existing database."
        SKIP_CREATE=true
    fi
fi

# Create database if it doesn't exist
if [ "$SKIP_CREATE" != "true" ]; then
    echo "Creating database '$DB_NAME'..."
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || {
        echo -e "${YELLOW}⚠${NC} Database might already exist, continuing..."
    }
    echo -e "${GREEN}✓${NC} Database created"
fi

echo ""

# Import SQL file
echo "Importing SQL backup file..."
echo "This may take a few minutes..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f $SQL_FILE

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} SQL file imported successfully"
else
    echo -e "${RED}✗${NC} Error importing SQL file"
    exit 1
fi

echo ""

# Verify import
echo "Verifying database import..."
TABLE_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')

if [ "$TABLE_COUNT" -gt "0" ]; then
    echo -e "${GREEN}✓${NC} Database verification successful"
    echo "   Found $TABLE_COUNT tables in the database"
else
    echo -e "${YELLOW}⚠${NC} No tables found. Database might be empty."
fi

echo ""
echo "========================================="
echo -e "${GREEN}Database setup completed!${NC}"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Update backend/.env with database credentials:"
echo "   DATABASE_NAME=$DB_NAME"
echo "   DATABASE_USER=$DB_USER"
echo "   DATABASE_PASSWORD=<your_password>"
echo "   DATABASE_HOST=$DB_HOST"
echo "   DATABASE_PORT=$DB_PORT"
echo ""
echo "2. Run backend migrations (if needed):"
echo "   cd backend"
echo "   python manage.py migrate"
echo ""
echo "3. Start the backend server:"
echo "   python manage.py runserver"
echo ""
