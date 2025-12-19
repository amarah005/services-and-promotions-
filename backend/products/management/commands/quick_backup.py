#!/usr/bin/env python3
"""
Quick Backup Command - Create a fast backup of essential data
Creates a lightweight backup with only the most important data for quick restoration
"""

import os
import json
import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import CoreProduct, ProductCategory, Platform, Brand, Seller
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Create a quick backup of essential data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default='backups',
            help='Directory to save backup files (default: backups)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('⚡ Creating quick backup...'))
        
        # Create backup directory
        backup_dir = options['output_dir']
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'quick_backup_{timestamp}.json'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        try:
            with transaction.atomic():
                # Collect essential data only
                backup_data = self._collect_essential_data()
                
                # Save to file
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, indent=2, ensure_ascii=False, default=str)
                
                self.stdout.write(self.style.SUCCESS(f'✅ Quick backup created: {backup_path}'))
                self.stdout.write(f'📊 Total products: {backup_data["summary"]["total_products"]}')
                self.stdout.write(f'📊 Total categories: {backup_data["summary"]["total_categories"]}')
                self.stdout.write(f'📊 Total platforms: {backup_data["summary"]["total_platforms"]}')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Quick backup failed: {str(e)}'))

    def _collect_essential_data(self):
        """Collect only essential data for quick restoration"""
        backup_data = {
            'metadata': {
                'created_at': datetime.datetime.now().isoformat(),
                'backup_type': 'quick',
                'description': 'Essential data backup for quick restoration'
            },
            'summary': {},
            'data': {}
        }
        
        # Essential models only
        essential_models = [
            ('platforms', Platform),
            ('brands', Brand),
            ('sellers', Seller),
            ('categories', ProductCategory),
            ('products', CoreProduct),
        ]
        
        for model_name, model_class in essential_models:
            try:
                count = model_class.objects.count()
                backup_data['summary'][f'total_{model_name}'] = count
                
                # Get essential fields only
                if model_name == 'products':
                    # For products, get only essential fields
                    products_data = []
                    for product in model_class.objects.all()[:1000]:  # Limit to 1000 products
                        products_data.append({
                            'id': product.id,
                            'name': product.name,
                            'price': str(product.price),
                            'main_image_url': product.main_image_url,
                            'is_active': product.is_active,
                            'category_id': product.category.id if product.category else None,
                            'seller_id': product.seller.id if product.seller else None,
                            'created_at': product.created_at.isoformat() if product.created_at else None,
                        })
                    backup_data['data'][model_name] = products_data
                else:
                    # For other models, get all fields
                    backup_data['data'][model_name] = list(model_class.objects.values())
                
                self.stdout.write(f'  📦 {model_name}: {count} records')
                
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ⚠️ Failed to backup {model_name}: {str(e)}'))
                backup_data['data'][model_name] = []
                backup_data['summary'][f'total_{model_name}'] = 0
        
        return backup_data
