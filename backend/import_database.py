#!/usr/bin/env python3
"""
Import PostgreSQL database from SQL backup file
"""
import os
import sys
from pathlib import Path
from decouple import config
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Get database credentials from .env
db_params = {
    'host': config('DATABASE_HOST', default='localhost'),
    'port': config('DATABASE_PORT', default='5432'),
    'user': config('DATABASE_USER', default='postgres'),
    'password': config('DATABASE_PASSWORD', default='12345'),
    'database': config('DATABASE_NAME', default='buyvaulthub_db')
}

# Get backup file path
backup_file = sys.argv[1] if len(sys.argv) > 1 else '../backups/backup_20251029_020655.sql'

# Convert to absolute path
if not os.path.isabs(backup_file):
    backup_file = os.path.join(os.path.dirname(__file__), backup_file)

backup_file = os.path.abspath(backup_file)

print("=" * 60)
print("Importing PostgreSQL Database from SQL Backup")
print("=" * 60)
print(f"Backup File: {backup_file}")
print(f"Database: {db_params['database']}")
print(f"User: {db_params['user']}")
print("=" * 60)

# Check if backup file exists
if not os.path.exists(backup_file):
    print(f"❌ ERROR: Backup file not found: {backup_file}")
    print("\nPlease provide the correct path to your backup file.")
    print("Usage: python import_database.py [path/to/backup.sql]")
    sys.exit(1)

print(f"✅ Backup file found: {backup_file}")
print(f"   File size: {os.path.getsize(backup_file) / (1024*1024):.2f} MB\n")

try:
    # Connect to database
    print("Connecting to database...")
    conn = psycopg2.connect(**db_params)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    print("✅ Connected successfully!\n")
    
    # Read SQL file - try different encodings (including UTF-16)
    print("Reading SQL backup file...")
    # Check file header to detect encoding
    with open(backup_file, 'rb') as f:
        header = f.read(4)
    
    encodings = []
    if header.startswith(b'\xff\xfe'):
        # UTF-16 LE (Windows Unicode)
        encodings = ['utf-16-le', 'utf-16']
    elif header.startswith(b'\xfe\xff'):
        # UTF-16 BE
        encodings = ['utf-16-be', 'utf-16']
    else:
        # Try common text encodings
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'utf-16-le', 'utf-16']
    
    sql_content = None
    
    for encoding in encodings:
        try:
            with open(backup_file, 'r', encoding=encoding, errors='ignore') as f:
                sql_content = f.read()
            print(f"✅ Read file using {encoding} encoding ({len(sql_content):,} characters)")
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    if sql_content is None:
        print("❌ ERROR: Could not read SQL file with any encoding")
        print("The file might be in a binary format (pg_dump custom format)")
        print("For binary dumps, use pg_restore instead:")
        print(f"   pg_restore -h localhost -U postgres -d buyvaulthub_db {backup_file}")
        sys.exit(1)
    
    print()
    
    # Split SQL content by semicolons (basic approach)
    # PostgreSQL dump files may have multi-line statements
    print("Importing SQL commands...")
    print("(This may take a few minutes for large backups)\n")
    
    # Execute SQL - for PostgreSQL dumps, we can use psycopg2's cursor
    # For large files, we might need to execute statement by statement
    # But for simplicity, let's try executing the whole thing
    
    # Note: Some SQL dumps may have specific formatting that requires
    # splitting by semicolon or using COPY commands
    
    try:
        # Method 1: Execute all at once (works for simple dumps)
        cursor.execute(sql_content)
        print("✅ Import completed successfully!")
    except psycopg2.ProgrammingError as e:
        # If that fails, try splitting by semicolon
        print("⚠️  Trying alternative import method...")
        
        # Split by semicolons and execute each statement
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        print(f"   Found {len(statements)} SQL statements to execute...")
        
        executed = 0
        errors = 0
        
        for i, statement in enumerate(statements):
            # Skip comments and empty statements
            if statement.startswith('--') or not statement:
                continue
            
            try:
                cursor.execute(statement)
                executed += 1
                if (executed % 100) == 0:
                    print(f"   Progress: {executed}/{len(statements)} statements executed...")
            except psycopg2.Error as e:
                errors += 1
                if errors < 10:  # Only show first 10 errors
                    print(f"   ⚠️  Warning on statement {i+1}: {str(e)[:100]}")
        
        print(f"\n✅ Import completed!")
        print(f"   Executed: {executed} statements")
        if errors > 0:
            print(f"   Errors: {errors} (some statements may have been skipped)")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("Database import completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run migrations to ensure schema is up to date:")
    print("   python manage.py migrate")
    print("2. Create a superuser if needed:")
    print("   python manage.py createsuperuser")
    print("3. Start the Django server:")
    print("   python manage.py runserver")
    
except psycopg2.Error as e:
    print(f"\n❌ Database Error: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure PostgreSQL service is running")
    print("2. Verify database credentials in .env file")
    print("3. Check if database exists: python create_database.py")
    sys.exit(1)
except FileNotFoundError:
    print(f"\n❌ ERROR: Backup file not found: {backup_file}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Unexpected Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

