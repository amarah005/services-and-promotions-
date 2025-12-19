#!/usr/bin/env python3
"""
SAFE deletion of products with non-standard image URLs (.heic, .avif, N/A)
Multiple safety checks and backups before any deletion
"""

import json
import re
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db.models import Q
from products.models import CoreProduct
import os


class Command(BaseCommand):
    help = 'SAFELY remove products with non-standard image formats (with dry-run and backup)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what WOULD be deleted without actually deleting (RECOMMENDED FIRST)'
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Actually delete products (requires explicit confirmation)'
        )
        parser.add_argument(
            '--backup-path',
            type=str,
            default='./backups',
            help='Path to save backup file'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        confirm = options['confirm']
        backup_path = options['backup_path']

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('SAFE PRODUCT DELETION - NON-STANDARD IMAGE FORMATS'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        # Get all products with URLs
        all_products = CoreProduct.objects.filter(
            is_active=True
        ).exclude(
            main_image_url__isnull=True
        ).exclude(
            main_image_url=''
        )

        non_standard_products = []

        for product in all_products:
            url = product.main_image_url
            if url and not self._is_standard_image_url(url):
                non_standard_products.append(product)

        total_count = len(non_standard_products)

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('\n✅ No products with non-standard images found!'))
            self.stdout.write(self.style.SUCCESS('Your database only has standard image formats! 🎉\n'))
            return

        # Display what will be deleted
        self.stdout.write(f'\n📊 Found {total_count} products with non-standard image formats\n')
        
        # Categorize by format
        format_breakdown = {}
        
        for product in non_standard_products:
            url = product.main_image_url or 'N/A'
            
            if url == 'N/A' or url.lower() == 'n/a':
                format_type = 'N/A (Broken)'
            elif '.heic' in url.lower():
                format_type = 'HEIC (Apple format)'
            elif '.avif' in url.lower():
                format_type = 'AVIF (Modern format)'
            else:
                format_type = 'Other non-standard'
            
            format_breakdown[format_type] = format_breakdown.get(format_type, 0) + 1

        # Display breakdown
        self.stdout.write(self.style.WARNING('📋 BREAKDOWN BY FORMAT TYPE:'))
        self.stdout.write('-' * 80)
        for format_type, count in sorted(format_breakdown.items(), key=lambda x: -x[1]):
            self.stdout.write(f'  {format_type:25} : {count:6} products')

        # Show all products
        self.stdout.write(f'\n🔍 ALL {total_count} PRODUCTS TO BE DELETED:')
        self.stdout.write('-' * 80)
        
        for i, product in enumerate(non_standard_products, 1):
            seller_name = product.seller.display_name if product.seller else 'Unknown'
            category_name = product.category.name if product.category else 'Uncategorized'
            url = product.main_image_url or 'N/A'
            
            # Determine format
            if url == 'N/A' or url.lower() == 'n/a':
                format_label = 'BROKEN'
            elif '.heic' in url.lower():
                format_label = 'HEIC'
            elif '.avif' in url.lower():
                format_label = 'AVIF'
            else:
                format_label = 'OTHER'
            
            self.stdout.write(
                f"{i:2}. ID: {product.id:6} | {format_label:6} | "
                f"{product.name[:40]:40} | {seller_name[:20]:20}"
            )

        # DRY RUN MODE
        if dry_run or not confirm:
            self.stdout.write('\n' + '=' * 80)
            self.stdout.write(self.style.WARNING('🔒 DRY-RUN MODE - NO CHANGES MADE'))
            self.stdout.write('=' * 80)
            self.stdout.write(f'\n⚠️  This would delete {total_count} products')
            self.stdout.write('\n💡 To actually delete these products, run:')
            self.stdout.write(self.style.SUCCESS(
                '   python manage.py safe_remove_nonstandard_images --confirm\n'
            ))
            return

        # CONFIRMATION MODE - Create backup first
        if confirm:
            self.stdout.write('\n' + '=' * 80)
            self.stdout.write(self.style.ERROR('⚠️  DELETION MODE ACTIVATED'))
            self.stdout.write('=' * 80)
            
            # Create backup
            self.stdout.write('\n📦 Creating backup before deletion...')
            backup_data = []
            
            for product in non_standard_products:
                backup_data.append({
                    'id': product.id,
                    'uuid': str(product.uuid),
                    'name': product.name,
                    'description': product.description,
                    'price': float(product.price) if product.price else None,
                    'original_price': float(product.original_price) if product.original_price else None,
                    'main_image_url': product.main_image_url,
                    'category_id': product.category_id,
                    'brand_id': product.brand_id,
                    'seller_id': product.seller_id,
                    'platform_type': product.platform_type,
                    'created_at': product.created_at.isoformat() if product.created_at else None,
                })
            
            # Save backup
            os.makedirs(backup_path, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(
                backup_path,
                f'deleted_nonstandard_images_{timestamp}.json'
            )
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': timestamp,
                    'total_deleted': total_count,
                    'products': backup_data
                }, f, indent=2, ensure_ascii=False)
            
            self.stdout.write(self.style.SUCCESS(f'✅ Backup saved to: {backup_file}'))

            # Final confirmation prompt
            self.stdout.write('\n' + '⚠️ ' * 20)
            self.stdout.write(self.style.ERROR(
                f'\n🚨 YOU ARE ABOUT TO DELETE {total_count} PRODUCTS! 🚨\n'
            ))
            self.stdout.write('⚠️ ' * 20 + '\n')
            
            # Ask for explicit confirmation
            response = input('\nType "DELETE" (in capitals) to confirm deletion: ')
            
            if response != 'DELETE':
                self.stdout.write(self.style.WARNING('\n❌ Deletion cancelled. No changes made.\n'))
                return

            # Perform deletion
            self.stdout.write('\n🗑️  Deleting products...')
            
            deleted_ids = [p.id for p in non_standard_products]
            deleted_count = 0
            
            for product in non_standard_products:
                product.delete()
                deleted_count += 1
            
            self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully deleted {deleted_count} products!'))
            
            # Save deletion log
            log_file = os.path.join(backup_path, f'deletion_log_nonstandard_{timestamp}.txt')
            with open(log_file, 'w') as f:
                f.write(f'Deletion performed at: {datetime.now().isoformat()}\n')
                f.write(f'Total products deleted: {deleted_count}\n')
                f.write(f'Deleted product IDs: {deleted_ids}\n')
                f.write(f'Backup file: {backup_file}\n')
            
            self.stdout.write(self.style.SUCCESS(f'✅ Deletion log saved to: {log_file}'))
            
            # Summary
            self.stdout.write('\n' + '=' * 80)
            self.stdout.write(self.style.SUCCESS('✅ DELETION COMPLETE'))
            self.stdout.write('=' * 80)
            self.stdout.write(f'\n📊 Statistics:')
            self.stdout.write(f'   • Products deleted: {deleted_count}')
            self.stdout.write(f'   • Backup location: {backup_file}')
            self.stdout.write(f'   • Log location: {log_file}')
            self.stdout.write('\n💡 To restore these products, you can use the backup file.')
            self.stdout.write('   Contact your developer for restoration instructions.\n')

    def _is_standard_image_url(self, url):
        """Check if URL uses standard image format"""
        if not url:
            return False
        
        # Check for standard image extensions
        if re.search(r'\.(jpg|jpeg|png|gif|webp|bmp|tiff)(\?|$)', url, re.IGNORECASE):
            return True
        
        # Known image CDNs that may not have extensions
        image_cdns = [
            'cdninstagram.com',
            'cdn.shopify.com',
            'cloudfront.net',
            'imgur.com',
            'i.imgur.com',
        ]
        
        url_lower = url.lower()
        if any(cdn in url_lower for cdn in image_cdns):
            return True
        
        return False

