#!/usr/bin/env python3
"""
Import products from SQL backup, fixing foreign key references
"""
import os
import sys
import re
from decouple import config
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Database credentials
db_params = {
    'host': config('DATABASE_HOST', default='localhost'),
    'port': config('DATABASE_PORT', default='5432'),
    'user': config('DATABASE_USER', default='postgres'),
    'password': config('DATABASE_PASSWORD', default='12345'),
    'database': config('DATABASE_NAME', default='buyvaulthub_db')
}

# SQL file path
sql_file = sys.argv[1] if len(sys.argv) > 1 else '../backups/backup_20251029_020655_utf8.sql'

if not os.path.isabs(sql_file):
    sql_file = os.path.join(os.path.dirname(__file__), sql_file)
sql_file = os.path.abspath(sql_file)

print("=" * 60)
print("Importing Products from SQL Backup")
print("=" * 60)
print(f"SQL File: {sql_file}")
print(f"Database: {db_params['database']}")
print("=" * 60)

if not os.path.exists(sql_file):
    print(f"[ERROR] File not found: {sql_file}")
    sys.exit(1)

try:
    # Connect to database
    conn = psycopg2.connect(**db_params)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    print("[OK] Connected to database\n")
    
    # First, let's check what we have
    cursor.execute("SELECT COUNT(*) FROM products_coreproduct")
    current_count = cursor.fetchone()[0]
    print(f"Current products in database: {current_count}")
    
    if current_count > 0:
        response = input(f"\nThere are already {current_count} products. Import anyway? (y/N): ")
        if response.lower() != 'y':
            print("Import cancelled.")
            sys.exit(0)
    
    # Read the SQL file
    print("\nReading SQL file...")
    with open(sql_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    print(f"[OK] Read file ({len(content):,} characters)\n")
    
    # Find the COPY statement for products_coreproduct
    copy_pattern = r'COPY\s+public\.products_coreproduct\s+\([^)]+\)\s+FROM\s+stdin;'
    copy_match = re.search(copy_pattern, content, re.IGNORECASE)
    
    if not copy_match:
        print("[ERROR] Could not find COPY statement for products_coreproduct")
        sys.exit(1)
    
    copy_start = copy_match.start()
    # Find where the COPY data ends (look for \. or next COPY/statement)
    copy_data_section = content[copy_match.end():]
    
    # Find the end marker (\. on its own line)
    end_match = re.search(r'^\.\s*$', copy_data_section, re.MULTILINE)
    if not end_match:
        print("[ERROR] Could not find end of COPY data")
        sys.exit(1)
    
    copy_data = copy_data_section[:end_match.start()].strip()
    
    print(f"[OK] Found COPY data section ({len(copy_data):,} characters)\n")
    
    # Parse and insert data line by line
    # COPY format: tab-separated values, one line per record
    lines = [line for line in copy_data.split('\n') if line.strip()]
    
    print(f"Found {len(lines)} product records to import\n")
    print("Importing products (this may take several minutes)...\n")
    
    # Get column order from COPY statement
    columns_match = re.search(r'COPY\s+public\.products_coreproduct\s+\(([^)]+)\)', content, re.IGNORECASE)
    if not columns_match:
        print("[ERROR] Could not parse column names from COPY statement")
        sys.exit(1)
    
    columns = [col.strip() for col in columns_match.group(1).split(',')]
    print(f"Columns: {len(columns)} fields\n")
    
    # Insert products one by one (more reliable for foreign keys)
    inserted = 0
    errors = 0
    error_samples = []
    
    for i, line in enumerate(lines):
        if i % 100 == 0 and i > 0:
            print(f"   Progress: {i}/{len(lines)} processed, {inserted} inserted, {errors} errors...")
        
        # Split by tab (COPY format uses tabs)
        # But handle escaped tabs and special values like \N (NULL)
        values = []
        current_value = []
        in_escape = False
        in_quote = False
        
        for char in line:
            if in_escape:
                if char == 't':
                    current_value.append('\t')
                elif char == 'n':
                    current_value.append('\n')
                elif char == '\\':
                    current_value.append('\\')
                else:
                    current_value.append(char)
                in_escape = False
            elif char == '\\':
                in_escape = True
            elif char == '\t' and not in_quote:
                # End of field
                value_str = ''.join(current_value)
                if value_str == r'\N':
                    values.append(None)
                else:
                    values.append(value_str)
                current_value = []
            else:
                current_value.append(char)
        
        # Last field
        value_str = ''.join(current_value)
        if value_str == r'\N':
            values.append(None)
        else:
            values.append(value_str)
        
        # Map values to columns
        if len(values) != len(columns):
            errors += 1
            if len(error_samples) < 5:
                error_samples.append(f"Line {i+1}: Expected {len(columns)} columns, got {len(values)}")
            continue
        
        # Build INSERT statement
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join(columns)
        
        # Convert values - handle NULL, integers, decimals, etc.
        processed_values = []
        for val in values:
            if val is None or val == r'\N':
                processed_values.append(None)
            else:
                # Try to convert to appropriate type
                # For now, keep as string - PostgreSQL will handle conversion
                processed_values.append(val)
        
        try:
            # Use INSERT ... ON CONFLICT DO NOTHING to skip duplicates
            insert_sql = f"""
                INSERT INTO products_coreproduct ({column_names})
                VALUES ({placeholders})
                ON CONFLICT (id) DO NOTHING
            """
            cursor.execute(insert_sql, processed_values)
            if cursor.rowcount > 0:
                inserted += 1
        except psycopg2.Error as e:
            errors += 1
            if len(error_samples) < 10:
                error_msg = str(e).split('\n')[0]
                error_samples.append(f"Line {i+1}: {error_msg[:100]}")
    
    print(f"\n[OK] Import completed!")
    print(f"   Inserted: {inserted} products")
    print(f"   Errors: {errors}")
    
    if error_samples:
        print(f"\nFirst {len(error_samples)} errors:")
        for err in error_samples:
            print(f"   - {err}")
    
    # Reset sequences to match imported data
    print("\nResetting sequences...")
    cursor.execute("""
        SELECT setval('products_coreproduct_id_seq', 
            COALESCE((SELECT MAX(id) FROM products_coreproduct), 1), 
            false);
    """)
    
    cursor.execute("SELECT COUNT(*) FROM products_coreproduct")
    final_count = cursor.fetchone()[0]
    print(f"[OK] Final product count: {final_count}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("[OK] Product import completed!")
    print("=" * 60)
    
except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

