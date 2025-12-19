#!/usr/bin/env python3
"""
Import products using COPY FROM STDIN (most reliable method)
"""
import os
import sys
import re
import io
import psycopg2
from decouple import config

db_params = {
    'host': config('DATABASE_HOST', default='localhost'),
    'port': config('DATABASE_PORT', default='5432'),
    'user': config('DATABASE_USER', default='postgres'),
    'password': config('DATABASE_PASSWORD', default='12345'),
    'database': config('DATABASE_NAME', default='buyvaulthub_db')
}

sql_file = sys.argv[1] if len(sys.argv) > 1 else '../backups/backup_20251029_020655_utf8.sql'
if not os.path.isabs(sql_file):
    sql_file = os.path.join(os.path.dirname(__file__), sql_file)
sql_file = os.path.abspath(sql_file)

print("=" * 60)
print("Importing Products using COPY FROM STDIN")
print("=" * 60)
print(f"SQL File: {sql_file}")
print("=" * 60)

try:
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    
    print("[OK] Connected to database\n")
    
    # Read SQL file
    print("Reading SQL file...")
    with open(sql_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    print(f"[OK] Read file ({len(content):,} characters)\n")
    
    # Find COPY statement and extract data
    copy_pattern = r'COPY\s+public\.products_coreproduct\s+\([^)]+\)\s+FROM\s+stdin;'
    copy_match = re.search(copy_pattern, content, re.IGNORECASE)
    
    if not copy_match:
        print("[ERROR] Could not find COPY statement for products_coreproduct")
        sys.exit(1)
    
    # Extract data section
    data_start = copy_match.end()
    data_section = content[data_start:]
    end_match = re.search(r'^\.\s*$', data_section, re.MULTILINE)
    
    if not end_match:
        print("[ERROR] Could not find end marker (\\.)")
        sys.exit(1)
    
    copy_data = data_section[:end_match.start()].strip()
    
    # Remove any trailing backslashes on empty lines
    lines = copy_data.split('\n')
    clean_lines = []
    for line in lines:
        line = line.rstrip()
        if line and line != '\\':
            clean_lines.append(line)
    
    copy_data_clean = '\n'.join(clean_lines) + '\n'
    
    print(f"[OK] Extracted COPY data ({len(copy_data_clean):,} characters)")
    print(f"     Lines: {len(clean_lines)}\n")
    
    # Get column names from COPY statement
    columns_match = re.search(r'COPY\s+public\.products_coreproduct\s+\(([^)]+)\)', copy_match.group(0), re.IGNORECASE)
    if not columns_match:
        print("[ERROR] Could not parse column names")
        sys.exit(1)
    
    columns = [col.strip() for col in columns_match.group(1).split(',')]
    print(f"[OK] Found {len(columns)} columns\n")
    
    # Use COPY FROM STDIN
    print("Importing using COPY FROM STDIN...")
    print("(This may take several minutes for large files)\n")
    
    # Create a file-like object from the data
    data_stream = io.StringIO(copy_data_clean)
    
    # Use COPY FROM
    copy_sql = f"COPY products_coreproduct ({', '.join(columns)}) FROM STDIN WITH (FORMAT csv, DELIMITER E'\\t', NULL '\\N')"
    
    try:
        cursor.copy_expert(copy_sql, data_stream)
        conn.commit()
        
        print("[OK] COPY completed successfully!")
        
        # Verify
        cursor.execute("SELECT COUNT(*) FROM products_coreproduct")
        count = cursor.fetchone()[0]
        print(f"\n[OK] Products imported: {count}")
        
    except psycopg2.Error as e:
        conn.rollback()
        print(f"[ERROR] COPY failed: {e}")
        print("\nThis might be due to:")
        print("1. Foreign key constraint violations")
        print("2. Invalid data format")
        print("3. Sequence issues")
        
        # Try alternative: insert row by row with error handling
        print("\nTrying alternative import method (row by row)...")
        conn.commit()  # Clear any transaction
        
        # Parse and insert manually
        inserted = 0
        errors = 0
        
        for i, line in enumerate(clean_lines[:1000]):  # Try first 1000
            if (i + 1) % 100 == 0:
                print(f"   Progress: {i+1} processed, {inserted} inserted...")
            
            # Simple tab split (won't handle all edge cases but might work)
            values = line.split('\t')
            
            if len(values) != len(columns):
                errors += 1
                continue
            
            # Convert \N to None
            processed = [None if v == r'\N' else v for v in values]
            
            try:
                placeholders = ', '.join(['%s'] * len(columns))
                insert_sql = f"""
                    INSERT INTO products_coreproduct ({', '.join(columns)})
                    VALUES ({placeholders})
                    ON CONFLICT (id) DO NOTHING
                """
                cursor.execute(insert_sql, processed)
                if cursor.rowcount > 0:
                    inserted += 1
            except:
                errors += 1
        
        conn.commit()
        print(f"\n[OK] Inserted {inserted} products (errors: {errors})")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("[OK] Import process completed!")
    print("=" * 60)
    print("\nCheck Django admin to see imported products")
    
except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

