#!/usr/bin/env python3
"""
Create PostgreSQL database if it doesn't exist
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from decouple import config

# Database connection parameters (connect to default 'postgres' database first)
db_params = {
    'host': config('DATABASE_HOST', default='localhost'),
    'port': config('DATABASE_PORT', default='5432'),
    'user': config('DATABASE_USER', default='postgres'),
    'password': config('DATABASE_PASSWORD', default='12345'),
    'database': 'postgres'  # Connect to default database first
}

db_name = config('DATABASE_NAME', default='buyvaulthub_db')

print("=" * 60)
print("Creating PostgreSQL Database")
print("=" * 60)
print(f"Database Name: {db_name}")
print(f"User: {db_params['user']}")
print("=" * 60)

try:
    # Connect to PostgreSQL server (to default 'postgres' database)
    conn = psycopg2.connect(**db_params)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    # Check if database exists
    cursor.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s",
        (db_name,)
    )
    exists = cursor.fetchone()
    
    if exists:
        print(f"✅ Database '{db_name}' already exists!")
    else:
        # Create database
        cursor.execute(f'CREATE DATABASE "{db_name}"')
        print(f"✅ Database '{db_name}' created successfully!")
    
    cursor.close()
    conn.close()
    
    # Test connection to the new database
    print("\nTesting connection to new database...")
    db_params['database'] = db_name
    test_conn = psycopg2.connect(**db_params)
    test_cursor = test_conn.cursor()
    test_cursor.execute("SELECT version();")
    version = test_cursor.fetchone()
    print(f"✅ Successfully connected to '{db_name}'!")
    print(f"PostgreSQL Version: {version[0][:50]}...")
    test_cursor.close()
    test_conn.close()
    
except psycopg2.Error as e:
    print(f"❌ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure PostgreSQL service is running")
    print("2. Verify the password is correct")
    print("3. Check if user 'postgres' has CREATE DATABASE privileges")
except Exception as e:
    print(f"❌ Unexpected error: {e}")

