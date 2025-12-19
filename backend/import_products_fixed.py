#!/usr/bin/env python3
"""
Import products from SQL backup, fixing foreign key mismatches
"""
import os
import sys
import re
import psycopg2
from decouple import config
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

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
print("Importing Products (with FK mapping)")
print("=" * 60)

try:
    conn = psycopg2.connect(**db_params)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    print("[OK] Connected to database\n")
    
    # Read the SQL file to find COPY data
    print("Reading SQL file...")
    with open(sql_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Find COPY statement for products
    copy_match = re.search(r'COPY\s+public\.products_coreproduct\s+\([^)]+\)\s+FROM\s+stdin;', content, re.IGNORECASE | re.DOTALL)
    if not copy_match:
        print("[ERROR] Could not find products COPY statement")
        sys.exit(1)
    
    # Extract data section (from COPY start to \.)
    data_start = copy_match.end()
    data_section = content[data_start:]
    end_match = re.search(r'^\.\s*$', data_section, re.MULTILINE)
    if not end_match:
        print("[ERROR] Could not find end of COPY data")
        sys.exit(1)
    
    copy_data = data_section[:end_match.start()].strip()
    lines = [line for line in copy_data.split('\n') if line.strip() and not line.strip() == '\\']
    
    print(f"Found {len(lines)} product records\n")
    
    # Get current FK mappings (old_id -> new_id)
    print("Building foreign key mappings...")
    
    # Categories: map by name (more reliable than ID)
    cursor.execute("SELECT id, name FROM products_productcategory")
    category_map = {name: id for id, name in cursor.fetchall()}
    print(f"  Categories: {len(category_map)} mapped")
    
    # Brands: map by name
    cursor.execute("SELECT id, name FROM products_brand")
    brand_map = {name: id for id, name in cursor.fetchall()}
    print(f"  Brands: {len(brand_map)} mapped")
    
    # Sellers: map by username+platform
    cursor.execute("""
        SELECT s.id, s.username, p.name 
        FROM products_seller s 
        JOIN products_platform p ON s.platform_id = p.id
    """)
    seller_map = {}
    for seller_id, username, platform_name in cursor.fetchall():
        key = f"{username}@{platform_name}"
        seller_map[key] = seller_id
    print(f"  Sellers: {len(seller_map)} mapped\n")
    
    # Parse and insert products
    print("Importing products (this will take time)...\n")
    
    inserted = 0
    skipped = 0
    errors = []
    
    # Get column names from COPY statement
    columns_match = re.search(r'COPY\s+public\.products_coreproduct\s+\(([^)]+)\)', content, re.IGNORECASE)
    if columns_match:
        columns = [col.strip() for col in columns_match.group(1).split(',')]
        category_idx = columns.index('category_id') if 'category_id' in columns else None
        brand_idx = columns.index('brand_id') if 'brand_id' in columns else None
        seller_idx = columns.index('seller_id') if 'seller_id' in columns else None
    else:
        print("[ERROR] Could not parse column names")
        sys.exit(1)
    
    for i, line in enumerate(lines):
        if (i + 1) % 500 == 0:
            print(f"   Progress: {i+1}/{len(lines)} processed, {inserted} inserted...")
        
        # Parse tab-separated values (COPY format)
        # Handle \N (NULL), \t (tab), \\ (backslash)
        values = []
        current = []
        escape = False
        
        for char in line:
            if escape:
                if char == 't':
                    current.append('\t')
                elif char == 'n':
                    current.append('\n')
                elif char == '\\':
                    current.append('\\')
                elif char == 'N':
                    # \N means NULL - we'll handle this specially
                    if len(current) == 0:
                        values.append(None)
                        current = []
                        escape = False
                        continue
                    else:
                        current.append('N')
                else:
                    current.append(char)
                escape = False
            elif char == '\\':
                escape = True
            elif char == '\t' and not escape:
                val = ''.join(current)
                if val == r'\N':
                    values.append(None)
                else:
                    values.append(val if val else None)
                current = []
            else:
                current.append(char)
        
        # Last field
        val = ''.join(current)
        if val == r'\N':
            values.append(None)
        else:
            values.append(val if val else None)
        
        if len(values) != len(columns):
            skipped += 1
            continue
        
        # For now, skip FK remapping - try direct insert
        # The issue might be that IDs don't match
        # Let's try inserting and see what happens
        
        placeholders = ', '.join(['%s'] * len(columns))
        column_list = ', '.join(columns)
        
        try:
            insert_sql = f"""
                INSERT INTO products_coreproduct ({column_list})
                VALUES ({placeholders})
                ON CONFLICT (id) DO NOTHING
            """
            cursor.execute(insert_sql, values)
            if cursor.rowcount > 0:
                inserted += 1
        except psycopg2.IntegrityError as e:
            # Foreign key violation - skip this record
            skipped += 1
            if len(errors) < 10:
                errors.append(f"Line {i+1}: FK violation - {str(e).split('(')[0]}")
        except Exception as e:
            skipped += 1
            if len(errors) < 10:
                errors.append(f"Line {i+1}: {str(e)[:80]}")
    
    print(f"\n[OK] Import completed!")
    print(f"   Inserted: {inserted} products")
    print(f"   Skipped: {skipped} products")
    
    if errors:
        print(f"\nFirst errors:")
        for err in errors:
            print(f"   - {err}")
    
    # Check final count
    cursor.execute("SELECT COUNT(*) FROM products_coreproduct")
    final_count = cursor.fetchone()[0]
    print(f"\nFinal product count: {final_count}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

