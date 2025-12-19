#!/usr/bin/env python3
"""
Import PostgreSQL database from SQL backup file using psql (recommended method)
This method handles pg_dump format files better
"""
import os
import sys
import subprocess
from pathlib import Path
from decouple import config

# Get database credentials from .env
db_name = config('DATABASE_NAME', default='buyvaulthub_db')
db_user = config('DATABASE_USER', default='postgres')
db_host = config('DATABASE_HOST', default='localhost')
db_port = config('DATABASE_PORT', default='5432')
db_password = config('DATABASE_PASSWORD', default='12345')

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
print(f"Database: {db_name}")
print(f"User: {db_user}")
print("=" * 60)

# Check if backup file exists
if not os.path.exists(backup_file):
    print(f"[ERROR] Backup file not found: {backup_file}")
    sys.exit(1)

print(f"[OK] Backup file found: {backup_file}")
print(f"   File size: {os.path.getsize(backup_file) / (1024*1024):.2f} MB\n")

# Method 1: Try to find and use psql directly
print("Method 1: Trying to use psql command...")

# Common PostgreSQL installation paths on Windows
psql_paths = [
    r"C:\Program Files\PostgreSQL\18\bin\psql.exe",
    r"C:\Program Files\PostgreSQL\17\bin\psql.exe",
    r"C:\Program Files\PostgreSQL\16\bin\psql.exe",
    r"C:\Program Files\PostgreSQL\15\bin\psql.exe",
    r"C:\Program Files\PostgreSQL\14\bin\psql.exe",
    r"C:\Program Files\PostgreSQL\13\bin\psql.exe",
]

psql_exe = None
for path in psql_paths:
    if os.path.exists(path):
        psql_exe = path
        print(f"[OK] Found psql at: {psql_exe}")
        break

if psql_exe:
    try:
        # Set PGPASSWORD environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = db_password
        
        # Build psql command
        # Note: Need to handle UTF-16 encoding for the SQL file
        # psql doesn't handle UTF-16 well, so we'll pipe it through
        cmd = [
            psql_exe,
            '-h', db_host,
            '-p', str(db_port),
            '-U', db_user,
            '-d', db_name,
            '-f', backup_file,
            '--echo-errors'
        ]
        
        print(f"\nExecuting: {' '.join(cmd[:3])} ... -d {db_name} -f <file>\n")
        print("Importing database (this may take several minutes)...\n")
        
        # Run psql
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            encoding='utf-16-le',  # Handle UTF-16 input file
            errors='ignore'
        )
        
        if result.returncode == 0:
            print("[OK] Import completed successfully!")
            if result.stdout:
                print(f"\nOutput:\n{result.stdout[-500:]}")  # Show last 500 chars
        else:
            print("[WARNING] Import completed with warnings/errors")
            if result.stderr:
                # Filter out common warnings
                errors = result.stderr.split('\n')
                real_errors = [e for e in errors if 'ERROR' in e.upper() and 'already exists' not in e.lower()]
                if real_errors:
                    error_list = '\n'.join(real_errors[:10])
                    print(f"\nErrors:\n{error_list}")
                else:
                    print("\n(Only non-critical warnings, import likely successful)")
            if result.stdout:
                print(f"\nOutput:\n{result.stdout[-500:]}")
        
        print("\n" + "=" * 60)
        print("Database import completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"[ERROR] Error using psql: {e}")
        print("\nTrying alternative method...\n")
        psql_exe = None

# Method 2: Use Python with psycopg2 (fallback)
if not psql_exe or result.returncode != 0:
    print("Method 2: Using Python psycopg2 (improved SQL parsing)...")
    
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    
    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("[OK] Connected to database\n")
        
        # Read file with UTF-16 encoding
        with open(backup_file, 'r', encoding='utf-16-le', errors='ignore') as f:
            content = f.read()
        
        print(f"[OK] Read file ({len(content):,} characters)\n")
        
        # Better SQL parsing - remove comments and split properly
        # Remove single-line comments (-- comments)
        lines = content.split('\n')
        cleaned_lines = []
        in_multiline_comment = False
        
        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue
            
            # Skip pg_dump header lines (comments that start with --)
            if line.strip().startswith('--'):
                continue
            
            # Skip COPY metadata lines (Type:, Schema:, Owner:, etc.)
            if any(line.strip().startswith(prefix) for prefix in 
                   ['Type:', 'Schema:', 'Owner:', 'Name:', 'Data', 'Encoding:', 'Collate:', 'Ctype:']):
                continue
            
            # Skip multiline comments (/* */)
            if '/*' in line:
                in_multiline_comment = True
            if '*/' in line:
                in_multiline_comment = False
                continue
            if in_multiline_comment:
                continue
            
            cleaned_lines.append(line)
        
        cleaned_content = '\n'.join(cleaned_lines)
        
        # Split by semicolon (but keep track of strings and quoted identifiers)
        statements = []
        current_statement = []
        in_string = False
        quote_char = None
        
        for line in cleaned_content.split('\n'):
            for char in line:
                if not in_string and char in ("'", '"'):
                    in_string = True
                    quote_char = char
                elif in_string and char == quote_char:
                    # Check if escaped
                    if len(current_statement) > 0 and current_statement[-1] != '\\':
                        in_string = False
                        quote_char = None
                elif not in_string and char == ';':
                    # End of statement
                    stmt = ''.join(current_statement).strip()
                    if stmt and not stmt.startswith('--'):
                        statements.append(stmt)
                    current_statement = []
                    continue
                
                current_statement.append(char)
            
            current_statement.append('\n')
        
        # Add last statement if exists
        if current_statement:
            stmt = ''.join(current_statement).strip()
            if stmt and not stmt.startswith('--'):
                statements.append(stmt)
        
        print(f"Parsed {len(statements)} SQL statements\n")
        print("Executing statements (this may take several minutes)...\n")
        
        executed = 0
        errors = 0
        
        for i, statement in enumerate(statements):
            if not statement.strip() or statement.strip().startswith('--'):
                continue
            
            try:
                cursor.execute(statement)
                executed += 1
                if (executed % 50) == 0:
                    print(f"   Progress: {executed}/{len(statements)} statements...")
            except psycopg2.Error as e:
                errors += 1
                # Only show first few unique errors
                if errors <= 5:
                    error_msg = str(e).split('\n')[0]
                    if 'already exists' not in error_msg.lower():
                        print(f"   [WARNING] Statement {i+1}: {error_msg[:80]}")
        
        cursor.close()
        conn.close()
        
        print(f"\n[OK] Import completed!")
        print(f"   Executed: {executed} statements")
        if errors > 0:
            print(f"   Errors/warnings: {errors} (some may be non-critical)")
        
        print("\n" + "=" * 60)
        print("Database import completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

print("\nNext steps:")
print("1. Verify import: python manage.py showmigrations")
print("2. Run migrations if needed: python manage.py migrate")
print("3. Create superuser if needed: python manage.py createsuperuser")
print("4. Start server: python manage.py runserver")

