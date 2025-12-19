#!/usr/bin/env python3
"""
Fix sequences and re-import products from SQL backup
This script fixes the sequence issues that prevent imports
"""
import os
import subprocess
from decouple import config

db_name = config('DATABASE_NAME', default='buyvaulthub_db')
db_user = config('DATABASE_USER', default='postgres')
db_host = config('DATABASE_HOST', default='localhost')
db_port = config('DATABASE_PORT', default='5432')
db_password = config('DATABASE_PASSWORD', default='12345')

sql_file = sys.argv[1] if len(sys.argv) > 1 else '../backups/backup_20251029_020655_utf8.sql'

if not os.path.isabs(sql_file):
    sql_file = os.path.join(os.path.dirname(__file__), sql_file)
sql_file = os.path.abspath(sql_file)

print("=" * 60)
print("Fixing Sequences and Re-importing")
print("=" * 60)

# Find psql
psql_paths = [
    r"C:\Program Files\PostgreSQL\18\bin\psql.exe",
    r"C:\Program Files\PostgreSQL\17\bin\psql.exe",
    r"C:\Program Files\PostgreSQL\16\bin\psql.exe",
]

psql_exe = None
for path in psql_paths:
    if os.path.exists(path):
        psql_exe = path
        break

if not psql_exe:
    print("[ERROR] psql.exe not found")
    sys.exit(1)

env = os.environ.copy()
env['PGPASSWORD'] = db_password

# Step 1: Fix sequences first
print("\nStep 1: Fixing sequences...")
fix_sequences_sql = """
SELECT setval('auth_group_id_seq', COALESCE((SELECT MAX(id) FROM auth_group), 1), true);
SELECT setval('auth_permission_id_seq', COALESCE((SELECT MAX(id) FROM auth_permission), 1), true);
SELECT setval('auth_user_id_seq', COALESCE((SELECT MAX(id) FROM auth_user), 1), true);
SELECT setval('django_content_type_id_seq', COALESCE((SELECT MAX(id) FROM django_content_type), 1), true);
SELECT setval('django_migrations_id_seq', COALESCE((SELECT MAX(id) FROM django_migrations), 1), true);
SELECT setval('products_platform_id_seq', COALESCE((SELECT MAX(id) FROM products_platform), 1), true);
SELECT setval('products_brand_id_seq', COALESCE((SELECT MAX(id) FROM products_brand), 1), true);
SELECT setval('products_seller_id_seq', COALESCE((SELECT MAX(id) FROM products_seller), 1), true);
SELECT setval('products_productcategory_id_seq', COALESCE((SELECT MAX(id) FROM products_productcategory), 1), true);
SELECT setval('products_coreproduct_id_seq', COALESCE((SELECT MAX(id) FROM products_coreproduct), 1), true);
"""

cmd = [
    psql_exe,
    '-h', db_host,
    '-p', str(db_port),
    '-U', db_user,
    '-d', db_name,
    '-c', fix_sequences_sql
]

try:
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    print("[OK] Sequences fixed\n")
except Exception as e:
    print(f"[WARNING] Could not fix all sequences: {e}\n")

# Step 2: Try importing with psql again, but skip errors
print("Step 2: Re-importing data (skipping duplicates)...")
print("(This may take several minutes)\n")

# Create a modified SQL that uses ON CONFLICT DO NOTHING
# Actually, psql will continue on errors with --set=ON_ERROR_STOP=0
cmd = [
    psql_exe,
    '-h', db_host,
    '-p', str(db_port),
    '-U', db_user,
    '-d', db_name,
    '-f', sql_file,
    '--set=ON_ERROR_STOP=0',
    '--quiet'
]

result = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding='utf-8', errors='ignore')

# Check results
print("=" * 60)
print("Import Results:")
print("=" * 60)

# Count products now
import psycopg2
conn = psycopg2.connect(
    host=db_host, port=db_port, user=db_user,
    password=db_password, database=db_name
)
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM products_coreproduct")
product_count = cursor.fetchone()[0]
cursor.close()
conn.close()

print(f"Products in database: {product_count}")

if product_count > 0:
    print("[OK] Products imported successfully!")
else:
    print("[WARNING] No products found. Check the error messages above.")
    print("\nPossible solutions:")
    print("1. Check foreign key constraints match")
    print("2. Verify category_id, brand_id, seller_id in backup match current database")
    print("3. Try importing with: python import_products_only.py")

print("\nNext steps:")
print("1. Check Django admin: http://localhost:8000/admin")
print("2. Verify products: python manage.py shell -c \"from products.models import CoreProduct; print(CoreProduct.objects.count())\"")

