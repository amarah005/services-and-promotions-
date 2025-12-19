#!/usr/bin/env python3
"""
Convert SQL file from UTF-16 to UTF-8 and import into PostgreSQL
This script fixes the encoding issue with backup_20251029_020655.sql
"""

import os
import sys
import subprocess
import getpass

def convert_utf16_to_utf8(input_file, output_file):
    """Convert SQL file from UTF-16 to UTF-8"""
    print(f"Converting {input_file} from UTF-16 to UTF-8...")
    
    try:
        # Read as UTF-16
        with open(input_file, 'r', encoding='utf-16') as f:
            content = f.read()
        
        # Write as UTF-8
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ File converted successfully: {output_file}")
        return True
    except Exception as e:
        print(f"❌ Error converting file: {e}")
        return False

def import_sql_file(db_name, db_user, sql_file, password):
    """Import SQL file into PostgreSQL"""
    print(f"\nImporting {sql_file} into database {db_name}...")
    print("This will take 3-5 minutes. Please wait...")
    
    # Set password as environment variable
    env = os.environ.copy()
    env['PGPASSWORD'] = password
    
    try:
        # Run psql command
        result = subprocess.run(
            ['psql', '-U', db_user, '-d', db_name, '-f', sql_file],
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ SQL file imported successfully!")
            return True
        else:
            print(f"⚠️ Import completed with warnings/errors:")
            print(result.stderr)
            # Check if tables were created anyway
            return verify_import(db_name, db_user, password)
    except FileNotFoundError:
        print("❌ Error: psql command not found. Make sure PostgreSQL is installed and in PATH.")
        return False
    except Exception as e:
        print(f"❌ Error importing file: {e}")
        return False

def verify_import(db_name, db_user, password):
    """Verify that import was successful"""
    print("\nVerifying import...")
    
    env = os.environ.copy()
    env['PGPASSWORD'] = password
    
    try:
        # Check product count
        result = subprocess.run(
            ['psql', '-U', db_user, '-d', db_name, '-t', '-c', 
             'SELECT COUNT(*) FROM products_coreproduct;'],
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            count = result.stdout.strip()
            if count and count.isdigit() and int(count) > 0:
                print(f"✅ Import verified! Found {count} products in database.")
                return True
            else:
                print("⚠️ No products found. Import might have failed.")
                return False
        else:
            print("⚠️ Could not verify import. Check error messages above.")
            return False
    except Exception as e:
        print(f"⚠️ Error verifying import: {e}")
        return False

def main():
    print("=" * 60)
    print("SQL File Converter and Importer")
    print("=" * 60)
    print()
    
    # File paths
    input_file = "backup_20251029_020655.sql"
    output_file = "backup_20251029_020655_utf8.sql"
    
    # Database settings
    db_name = "buyvaulthub_db"
    db_user = "postgres"
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"❌ Error: {input_file} not found!")
        print(f"   Current directory: {os.getcwd()}")
        print(f"   Please make sure the SQL file is in the current directory.")
        return 1
    
    # Get PostgreSQL password
    password = getpass.getpass(f"Enter PostgreSQL password for user '{db_user}': ")
    print()
    
    # Step 1: Convert file
    if not convert_utf16_to_utf8(input_file, output_file):
        return 1
    
    # Step 2: Create database if not exists
    print(f"\nCreating database {db_name} (if not exists)...")
    env = os.environ.copy()
    env['PGPASSWORD'] = password
    
    try:
        subprocess.run(
            ['psql', '-U', db_user, '-c', f'CREATE DATABASE {db_name};'],
            env=env,
            capture_output=True,
            text=True
        )
        print(f"✅ Database {db_name} ready")
    except:
        print("⚠️ Database might already exist, continuing...")
    
    # Step 3: Import SQL file
    if not import_sql_file(db_name, db_user, output_file, password):
        print("\n❌ Import failed. Please check error messages above.")
        return 1
    
    print("\n" + "=" * 60)
    print("✅ Import Process Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Update backend/.env with database credentials")
    print("2. Test backend: python manage.py dbshell")
    print("3. Start backend: python manage.py runserver")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
