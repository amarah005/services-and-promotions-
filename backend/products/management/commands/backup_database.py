#!/usr/bin/env python3
"""
Database Backup Command - Create comprehensive backup of all data
Creates a complete backup including products, categories, platforms, users, and relationships
"""

import os
import json
import datetime
from django.core.management.base import BaseCommand, CommandError
from django.core import serializers
from django.db import transaction
from django.conf import settings
from products.models import CoreProduct, ProductCategory, Platform, Brand, Seller
from django.contrib.auth.models import User
from recommendations.models import Recommendation


class Command(BaseCommand):
    help = 'Create a comprehensive backup of all database data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default='backups',
            help='Directory to save backup files (default: backups)'
        )
        parser.add_argument(
            '--include-media',
            action='store_true',
            help='Include media files in backup'
        )
        parser.add_argument(
            '--compress',
            action='store_true',
            help='Compress backup files'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔄 Starting comprehensive database backup...'))
        
        # Create backup directory
        backup_dir = options['output_dir']
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'database_backup_{timestamp}.json'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        try:
            with transaction.atomic():
                # Collect all data
                backup_data = self._collect_all_data()
                
                # Save to file
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)
                
                self.stdout.write(self.style.SUCCESS(f'✅ Backup created: {backup_path}'))
                
                # Create summary
                self._create_backup_summary(backup_data, backup_dir, timestamp)
                
                # Include media files if requested
                if options['include_media']:
                    self._backup_media_files(backup_dir, timestamp)
                
                # Compress if requested
                if options['compress']:
                    self._compress_backup(backup_path)
                
                self.stdout.write(self.style.SUCCESS('🎉 Database backup completed successfully!'))
                
        except Exception as e:
            raise CommandError(f'Backup failed: {str(e)}')

    def _collect_all_data(self):
        """Collect all database data"""
        self.stdout.write('📊 Collecting database data...')
        
        backup_data = {
            'metadata': {
                'created_at': datetime.datetime.now().isoformat(),
                'django_version': '5.2.6',
                'backup_version': '1.0',
                'description': 'Complete BuyVaultHub database backup'
            },
            'data': {}
        }
        
        # Core models
        models_to_backup = [
            ('users', User),
            ('platforms', Platform),
            ('brands', Brand),
            ('sellers', Seller),
            ('categories', ProductCategory),
            ('products', CoreProduct),
            ('recommendations', Recommendation),
        ]
        
        for model_name, model_class in models_to_backup:
            try:
                count = model_class.objects.count()
                self.stdout.write(f'  📦 {model_name}: {count} records')
                
                # Serialize all objects
                serialized_data = serializers.serialize('json', model_class.objects.all())
                backup_data['data'][model_name] = {
                    'count': count,
                    'serialized_data': serialized_data
                }
                
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠️ Failed to backup {model_name}: {str(e)}'))
                backup_data['data'][model_name] = {
                    'count': 0,
                    'error': str(e),
                    'serialized_data': '[]'
                }
        
        return backup_data

    def _create_backup_summary(self, backup_data, backup_dir, timestamp):
        """Create a summary of the backup"""
        summary_path = os.path.join(backup_dir, f'backup_summary_{timestamp}.txt')
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write('BUYVAULTHUB DATABASE BACKUP SUMMARY\n')
            f.write('=' * 50 + '\n\n')
            f.write(f'Backup Date: {backup_data["metadata"]["created_at"]}\n')
            f.write(f'Django Version: {backup_data["metadata"]["django_version"]}\n')
            f.write(f'Backup Version: {backup_data["metadata"]["backup_version"]}\n\n')
            
            f.write('DATA SUMMARY:\n')
            f.write('-' * 20 + '\n')
            for model_name, data in backup_data['data'].items():
                f.write(f'{model_name.upper()}: {data["count"]} records\n')
            
            f.write('\nRESTORATION INSTRUCTIONS:\n')
            f.write('-' * 30 + '\n')
            f.write('1. Run: python manage.py restore_database --backup-file <backup_file>\n')
            f.write('2. Run: python manage.py migrate\n')
            f.write('3. Run: python manage.py collectstatic\n')
            f.write('4. Restart your server\n')
        
        self.stdout.write(f'📋 Summary created: {summary_path}')

    def _backup_media_files(self, backup_dir, timestamp):
        """Backup media files"""
        media_dir = os.path.join(backup_dir, f'media_backup_{timestamp}')
        os.makedirs(media_dir, exist_ok=True)
        
        # Copy static images
        static_images_dir = os.path.join(settings.BASE_DIR, 'static', 'images')
        if os.path.exists(static_images_dir):
            import shutil
            shutil.copytree(static_images_dir, os.path.join(media_dir, 'static_images'))
            self.stdout.write(f'📁 Media files backed up to: {media_dir}')

    def _compress_backup(self, backup_path):
        """Compress backup file"""
        import gzip
        compressed_path = f'{backup_path}.gz'
        
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                f_out.writelines(f_in)
        
        # Remove original file
        os.remove(backup_path)
        self.stdout.write(f'🗜️ Compressed backup: {compressed_path}')
