#!/usr/bin/env python3
"""
Database Restore Command - Restore database from backup
Restores all data including products, categories, platforms, users, and relationships
"""

import os
import json
from django.core.management.base import BaseCommand, CommandError
from django.core import serializers
from django.db import transaction
from django.conf import settings
from products.models import CoreProduct, ProductCategory, Platform, Brand, Seller
from django.contrib.auth.models import User
from recommendations.models import Recommendation


class Command(BaseCommand):
    help = 'Restore database from backup file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--backup-file',
            type=str,
            required=True,
            help='Path to backup file to restore from'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing data before restore (DANGEROUS)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be restored without actually restoring'
        )

    def handle(self, *args, **options):
        backup_file = options['backup_file']
        dry_run = options['dry_run']
        clear_existing = options['clear_existing']
        
        if not os.path.exists(backup_file):
            raise CommandError(f'Backup file not found: {backup_file}')
        
        self.stdout.write(self.style.SUCCESS('🔄 Starting database restoration...'))
        
        try:
            # Load backup data
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Show backup info
            self._show_backup_info(backup_data)
            
            if dry_run:
                self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No data will be restored'))
                self._show_restore_plan(backup_data)
                return
            
            # Confirm restoration
            if not self._confirm_restore(clear_existing):
                self.stdout.write(self.style.WARNING('❌ Restoration cancelled'))
                return
            
            # Clear existing data if requested
            if clear_existing:
                self._clear_existing_data()
            
            # Restore data
            self._restore_data(backup_data)
            
            self.stdout.write(self.style.SUCCESS('🎉 Database restoration completed successfully!'))
            
        except Exception as e:
            raise CommandError(f'Restoration failed: {str(e)}')

    def _show_backup_info(self, backup_data):
        """Show information about the backup"""
        metadata = backup_data.get('metadata', {})
        self.stdout.write(f'📅 Backup Date: {metadata.get("created_at", "Unknown")}')
        self.stdout.write(f'🐍 Django Version: {metadata.get("django_version", "Unknown")}')
        self.stdout.write(f'📦 Backup Version: {metadata.get("backup_version", "Unknown")}')
        
        self.stdout.write('\n📊 Backup Contents:')
        for model_name, data in backup_data.get('data', {}).items():
            count = data.get('count', 0)
            self.stdout.write(f'  {model_name.upper()}: {count} records')

    def _show_restore_plan(self, backup_data):
        """Show what would be restored"""
        self.stdout.write('\n🔍 Restore Plan:')
        for model_name, data in backup_data.get('data', {}).items():
            count = data.get('count', 0)
            if count > 0:
                self.stdout.write(f'  ✅ {model_name.upper()}: {count} records')
            else:
                self.stdout.write(f'  ⚠️ {model_name.upper()}: {count} records (empty or error)')

    def _confirm_restore(self, clear_existing):
        """Confirm restoration with user"""
        if clear_existing:
            self.stdout.write(self.style.WARNING('⚠️ WARNING: This will DELETE all existing data!'))
        
        response = input('\n🤔 Do you want to proceed with restoration? (yes/no): ')
        return response.lower() in ['yes', 'y']

    def _clear_existing_data(self):
        """Clear existing data"""
        self.stdout.write('🗑️ Clearing existing data...')
        
        # Delete in reverse order to avoid foreign key constraints
        models_to_clear = [
            Recommendation,
            CoreProduct,
            ProductCategory,
            Seller,
            Brand,
            Platform,
        ]
        
        for model in models_to_clear:
            count = model.objects.count()
            if count > 0:
                model.objects.all().delete()
                self.stdout.write(f'  🗑️ Cleared {count} {model.__name__} records')

    def _restore_data(self, backup_data):
        """Restore data from backup"""
        self.stdout.write('📥 Restoring data...')
        
        # Restore in order to maintain foreign key relationships
        restore_order = [
            ('users', User),
            ('platforms', Platform),
            ('brands', Brand),
            ('sellers', Seller),
            ('categories', ProductCategory),
            ('products', CoreProduct),
            ('recommendations', Recommendation),
        ]
        
        for model_name, model_class in restore_order:
            data = backup_data.get('data', {}).get(model_name, {})
            serialized_data = data.get('serialized_data', '[]')
            
            if serialized_data and serialized_data != '[]':
                try:
                    # Deserialize and save objects
                    objects = serializers.deserialize('json', serialized_data)
                    saved_count = 0
                    
                    for obj in objects:
                        obj.save()
                        saved_count += 1
                    
                    self.stdout.write(f'  ✅ {model_name.upper()}: {saved_count} records restored')
                    
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  ⚠️ Failed to restore {model_name}: {str(e)}'))
            else:
                self.stdout.write(f'  ⚠️ {model_name.upper()}: No data to restore')
