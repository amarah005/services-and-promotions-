#!/usr/bin/env python3
"""
Drop PostgreSQL database
"""
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from decouple import config

# Get database credentials from .env
db_params = {
    'host': config('DATABASE_HOST', default='localhost'),
    'port': config('DATABASE_PORT', default='5432'),
    'user': config('DATABASE_USER', default='postgres'),
    'password': config('DATABASE_PASSWORD', default='12345'),
    'database': 'postgres'  # Connect to default 'postgres' database to drop our database
}

db_name = config('DATABASE_NAME', default='buyvaulthub_db')

print("=" * 60)
print("Dropping PostgreSQL Database")
print("=" * 60)
print(f"Database Name: {db_name}")
print(f"User: {db_params['user']}")
print("=" * 60)

# Confirm before dropping
response = input(f"\n⚠️  WARNING: This will DELETE the database '{db_name}' and ALL its data!\nAre you sure? Type 'yes' to continue: ")

if response.lower() != 'yes':
    print("Operation cancelled.")
    sys.exit(0)

try:
    # Connect to PostgreSQL server (to default 'postgres' database)
    conn = psycopg2.connect(**db_params)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    print("\nConnecting to PostgreSQL server...")
    
    # Check if database exists
    cursor.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s",
        (db_name,)
    )
    exists = cursor.fetchone()
    
    if not exists:
        print(f"[INFO] Database '{db_name}' does not exist. Nothing to drop.")
        cursor.close()
        conn.close()
        sys.exit(0)
    
    # Terminate all connections to the database first
    print("Terminating active connections...")
    cursor.execute("""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = %s AND pid <> pg_backend_pid();
    """, (db_name,))
    
    # Drop the database
    print(f"Dropping database '{db_name}'...")
    cursor.execute(f'DROP DATABASE IF EXISTS "{db_name}";')
    
    print(f"[OK] Database '{db_name}' dropped successfully!")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("Database dropped successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Recreate database: python create_database.py")
    print("2. Import SQL backup: python convert_and_import.py ..\\backups\\backup_20251029_020655.sql")
    print("3. Or run migrations: python manage.py migrate")
    
except psycopg2.Error as e:
    print(f"\n[ERROR] Database Error: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure PostgreSQL service is running")
    print("2. Verify the password is correct")
    print("3. Check if you have DROP DATABASE privileges")
    sys.exit(1)
except Exception as e:
    print(f"\n[ERROR] Unexpected Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

