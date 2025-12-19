#!/usr/bin/env python3
"""
Safely delete products with HTTP 404 errors (truly broken images)
"""

import csv
import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from products.models import CoreProduct


class Command(BaseCommand):
    help = 'Safely delete products with HTTP 404 errors from broken URLs CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            default='./backups/broken_urls_20251014_165215.csv',
            help='Path to broken URLs CSV file'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Actually delete products (requires explicit confirmation)'
        )

    def handle(self, *args, **options):
        csv_path = options['csv']
        dry_run = options['dry_run']
        confirm = options['confirm']

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('SAFE DELETION - HTTP 404 BROKEN IMAGES'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        # Read CSV and filter 404 errors
        self.stdout.write(f'\n📂 Reading CSV: {csv_path}')
        
        products_404 = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('Check_Result', '').strip() == 'ERROR_404':
                        products_404.append(row)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'\n❌ CSV file not found: {csv_path}\n'))
            return

        total_404 = len(products_404)

        if total_404 == 0:
            self.stdout.write(self.style.SUCCESS('\n✅ No products with HTTP 404 errors found!\n'))
            return

        self.stdout.write(f'✅ Found {total_404} products with HTTP 404 errors\n')

        # Display products to be deleted
        self.stdout.write('=' * 80)
        self.stdout.write(self.style.WARNING(f'📋 PRODUCTS WITH HTTP 404 ERRORS (Truly Broken Images):'))
        self.stdout.write('=' * 80)

        # Group by seller
        by_seller = {}
        for product in products_404:
            seller = product.get('Seller', 'Unknown')
            if seller not in by_seller:
                by_seller[seller] = []
            by_seller[seller].append(product)

        for seller, prods in sorted(by_seller.items(), key=lambda x: -len(x[1])):
            self.stdout.write(f'\n🏪 {seller}: {len(prods)} product(s)')
            for i, p in enumerate(prods[:5], 1):
                prod_id = p.get('ID', '')
                name = p.get('Name', '')[:60]
                self.stdout.write(f'   {i}. ID {prod_id}: {name}')
            if len(prods) > 5:
                self.stdout.write(f'   ... and {len(prods) - 5} more')

        # Get actual product IDs from database
        self.stdout.write('\n\n🔍 Verifying products in database...')
        
        product_ids = [int(p.get('ID')) for p in products_404 if p.get('ID', '').isdigit()]
        products_in_db = CoreProduct.objects.filter(id__in=product_ids, is_active=True)
        
        actual_count = products_in_db.count()
        
        self.stdout.write(f'✅ Found {actual_count} products in database (out of {total_404} in CSV)')

        if actual_count == 0:
            self.stdout.write(self.style.WARNING('\n⚠️  No matching products found in database.\n'))
            return

        # DRY RUN MODE
        if dry_run or not confirm:
            self.stdout.write('\n' + '=' * 80)
            self.stdout.write(self.style.WARNING('🔒 DRY-RUN MODE - NO CHANGES MADE'))
            self.stdout.write('=' * 80)
            
            self.stdout.write(f'\n⚠️  This would delete {actual_count} products with HTTP 404 errors')
            
            # Show sample products
            self.stdout.write('\n📋 Sample products to be deleted:')
            for i, product in enumerate(products_in_db[:10], 1):
                self.stdout.write(
                    f'   {i}. ID {product.id}: {product.name[:60]} | '
                    f'{product.seller.display_name if product.seller else "Unknown"}'
                )
            
            if actual_count > 10:
                self.stdout.write(f'   ... and {actual_count - 10} more')
            
            self.stdout.write('\n💡 To actually delete these products, run:')
            self.stdout.write(self.style.SUCCESS(
                '   python manage.py delete_404_products --confirm\n'
            ))
            return

        # CONFIRMATION MODE
        if confirm:
            self.stdout.write('\n' + '=' * 80)
            self.stdout.write(self.style.ERROR('⚠️  DELETION MODE ACTIVATED'))
            self.stdout.write('=' * 80)

            # Create backup
            self.stdout.write('\n📦 Creating backup before deletion...')
            
            backup_data = []
            for product in products_in_db:
                backup_data.append({
                    'id': product.id,
                    'uuid': str(product.uuid),
                    'name': product.name,
                    'description': product.description,
                    'price': float(product.price) if product.price else None,
                    'main_image_url': product.main_image_url,
                    'category_id': product.category_id,
                    'brand_id': product.brand_id,
                    'seller_id': product.seller_id,
                    'platform_type': product.platform_type,
                    'created_at': product.created_at.isoformat() if product.created_at else None,
                    'reason_deleted': 'HTTP 404 - Image not found',
                })

            # Save backup
            backup_dir = './backups'
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(backup_dir, f'deleted_404_products_{timestamp}.json')
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': timestamp,
                    'total_deleted': actual_count,
                    'reason': 'HTTP 404 - Broken image URLs',
                    'products': backup_data
                }, f, indent=2, ensure_ascii=False)
            
            self.stdout.write(self.style.SUCCESS(f'✅ Backup saved to: {backup_file}'))

            # Final confirmation
            self.stdout.write('\n' + '⚠️ ' * 20)
            self.stdout.write(self.style.ERROR(
                f'\n🚨 YOU ARE ABOUT TO DELETE {actual_count} PRODUCTS WITH BROKEN IMAGES! 🚨\n'
            ))
            self.stdout.write('⚠️ ' * 20 + '\n')

            response = input('\nType "DELETE" (in capitals) to confirm deletion: ')

            if response != 'DELETE':
                self.stdout.write(self.style.WARNING('\n❌ Deletion cancelled. No changes made.\n'))
                return

            # Perform deletion
            self.stdout.write('\n🗑️  Deleting products...')

            deleted_ids = list(products_in_db.values_list('id', flat=True))
            deletion_result = products_in_db.delete()

            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Successfully deleted {deletion_result[0]} products!\n'
            ))

            # Save deletion log
            log_file = os.path.join(backup_dir, f'deletion_log_404_{timestamp}.txt')
            with open(log_file, 'w') as f:
                f.write(f'Deletion performed at: {datetime.now().isoformat()}\n')
                f.write(f'Total products deleted: {deletion_result[0]}\n')
                f.write(f'Reason: HTTP 404 - Broken image URLs\n')
                f.write(f'Deleted product IDs: {deleted_ids}\n')
                f.write(f'Backup file: {backup_file}\n')

            self.stdout.write(self.style.SUCCESS(f'✅ Deletion log saved to: {log_file}'))

            # Summary
            self.stdout.write('\n' + '=' * 80)
            self.stdout.write(self.style.SUCCESS('✅ DELETION COMPLETE'))
            self.stdout.write('=' * 80)
            self.stdout.write(f'\n📊 Statistics:')
            self.stdout.write(f'   • Products deleted: {deletion_result[0]}')
            self.stdout.write(f'   • Backup location: {backup_file}')
            self.stdout.write(f'   • Log location: {log_file}')
            self.stdout.write('\n💡 To restore these products, you can use the backup file.')
            self.stdout.write('   Contact your developer for restoration instructions.\n')

