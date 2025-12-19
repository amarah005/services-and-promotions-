#!/usr/bin/env python3
"""
Convert UTF-16 SQL file to UTF-8 and import using psql
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

# Output file (UTF-8 version)
output_file = backup_file.replace('.sql', '_utf8.sql')

print("=" * 60)
print("Converting SQL File to UTF-8 and Importing")
print("=" * 60)
print(f"Input File (UTF-16): {backup_file}")
print(f"Output File (UTF-8): {output_file}")
print(f"Database: {db_name}")
print("=" * 60)

# Step 1: Convert UTF-16 to UTF-8
print("\nStep 1: Converting UTF-16 to UTF-8...")
try:
    with open(backup_file, 'r', encoding='utf-16-le', errors='ignore') as f:
        content = f.read()
    
    with open(output_file, 'w', encoding='utf-8', errors='ignore') as f:
        f.write(content)
    
    print(f"[OK] Conversion complete!")
    print(f"     Original size: {os.path.getsize(backup_file) / (1024*1024):.2f} MB")
    print(f"     Converted size: {os.path.getsize(output_file) / (1024*1024):.2f} MB")
    
except Exception as e:
    print(f"[ERROR] Conversion failed: {e}")
    sys.exit(1)

# Step 2: Import using psql
print("\nStep 2: Importing to PostgreSQL using psql...")

# Find psql
psql_paths = [
    r"C:\Program Files\PostgreSQL\18\bin\psql.exe",
    r"C:\Program Files\PostgreSQL\17\bin\psql.exe",
    r"C:\Program Files\PostgreSQL\16\bin\psql.exe",
    r"C:\Program Files\PostgreSQL\15\bin\psql.exe",
]

psql_exe = None
for path in psql_paths:
    if os.path.exists(path):
        psql_exe = path
        break

if not psql_exe:
    print("[ERROR] psql.exe not found in common PostgreSQL installation paths")
    print("Please provide the path to psql.exe manually")
    sys.exit(1)

print(f"[OK] Found psql at: {psql_exe}")

# Set PGPASSWORD environment variable
env = os.environ.copy()
env['PGPASSWORD'] = db_password

# Build psql command
cmd = [
    psql_exe,
    '-h', db_host,
    '-p', str(db_port),
    '-U', db_user,
    '-d', db_name,
    '-f', output_file,
    '--echo-errors',
    '--set=ON_ERROR_STOP=0'  # Continue on errors
]

print(f"\nExecuting import (this may take several minutes for a {os.path.getsize(output_file) / (1024*1024):.1f} MB file)...\n")
print("Command: psql -h localhost -U postgres -d buyvaulthub_db -f <converted_file>\n")

try:
    # Run psql
    result = subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore'
    )
    
    # Filter output
    if result.stdout:
        lines = result.stdout.split('\n')
        # Show last 100 lines of output
        print("\n" + "=" * 60)
        print("Import Output (last 100 lines):")
        print("=" * 60)
        for line in lines[-100:]:
            if line.strip():
                print(line)
    
    if result.stderr:
        error_lines = result.stderr.split('\n')
        # Filter out non-critical errors
        critical_errors = [e for e in error_lines if 'ERROR' in e.upper() 
                          and 'already exists' not in e.lower()
                          and 'does not exist' not in e.lower()
                          and 'relation' not in e.lower()]
        
        if critical_errors:
            print("\n" + "=" * 60)
            print("Critical Errors:")
            print("=" * 60)
            for error in critical_errors[:20]:  # Show first 20
                print(error)
        elif error_lines:
            # Count errors
            error_count = len([e for e in error_lines if 'ERROR' in e.upper()])
            if error_count > 0:
                print(f"\n[INFO] Found {error_count} errors/warnings (mostly non-critical)")
    
    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("[OK] Import completed successfully!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("[WARNING] Import completed with some errors/warnings")
        print("(Some errors may be non-critical - check the output above)")
        print("=" * 60)
    
    # Cleanup: remove temporary UTF-8 file (optional)
    print(f"\nTemporary UTF-8 file saved at: {output_file}")
    print("(You can delete it after verifying the import was successful)")
    
except Exception as e:
    print(f"\n[ERROR] Failed to run psql: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nNext steps:")
print("1. Verify import: Check your database tables")
print("2. Run migrations if needed: python manage.py migrate")
print("3. Verify data: Use Django admin or database tools")

