#!/usr/bin/env python3
"""
Test PostgreSQL database connection
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'buyvaulthub.settings')
django.setup()

from django.db import connection
from django.conf import settings

print("=" * 60)
print("Testing PostgreSQL Connection")
print("=" * 60)
print(f"Database Name: {settings.DATABASES['default']['NAME']}")
print(f"Database User: {settings.DATABASES['default']['USER']}")
print(f"Database Host: {settings.DATABASES['default']['HOST']}")
print(f"Database Port: {settings.DATABASES['default']['PORT']}")
print(f"Password: {'*' * len(settings.DATABASES['default'].get('PASSWORD', ''))} (hidden)")
print("=" * 60)

try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print("✅ SUCCESS: Connected to PostgreSQL!")
        print(f"PostgreSQL Version: {version[0]}")
except Exception as e:
    print("❌ FAILED: Could not connect to PostgreSQL")
    print(f"Error: {str(e)}")
    print("\nTroubleshooting:")
    print("1. Make sure PostgreSQL service is running")
    print("2. Verify the password in backend/.env file")
    print("3. Try updating DATABASE_PASSWORD in backend/.env")
    print("4. Or reset PostgreSQL password using pgAdmin or command line")

