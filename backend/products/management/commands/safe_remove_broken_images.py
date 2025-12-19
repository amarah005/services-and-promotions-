#!/usr/bin/env python3
"""
SAFE deletion of products with broken/placeholder images
Multiple safety checks and backups before any deletion
"""

import json
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db.models import Q
from products.models import CoreProduct
import os


class Command(BaseCommand):
    help = 'SAFELY remove products with broken/placeholder images (with dry-run and backup)'

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
            '--backup',
            action='store_true',
            default=True,
            help='Create backup before deletion (default: True)'
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
        create_backup = options['backup']
        backup_path = options['backup_path']

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('SAFE PRODUCT DELETION - BROKEN/PLACEHOLDER IMAGES'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        # Identify problematic products
        placeholder_patterns = [
            'placeholder',
            'via.placeholder.com',
            'placehold',
            'default',
            'noimage',
            'no-image',
            'dummy',
            'sample',
        ]
        
        # Build query for products to delete
        placeholder_q = Q()
        for pattern in placeholder_patterns:
            placeholder_q |= Q(main_image_url__icontains=pattern)
        
        # Also include null/empty and invalid formats
        problematic_q = (
            Q(main_image_url__isnull=True) |
            Q(main_image_url='') |
            Q(main_image_url='null') |
            Q(main_image_url='undefined') |
            Q(main_image_url__startswith='https://:0') |
            Q(main_image_url__startswith='http://:0') |
            placeholder_q
        )

        # Get products to delete
        products_to_delete = CoreProduct.objects.filter(
            is_active=True
        ).filter(problematic_q)

        total_count = products_to_delete.count()

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('\n✅ No products with broken images found!'))
            self.stdout.write(self.style.SUCCESS('Your database is clean! 🎉\n'))
            return

        # Display what will be deleted
        self.stdout.write(f'\n📊 Found {total_count} products with broken/placeholder images\n')
        
        # Group by issue type
        issue_breakdown = {}
        sample_products = []
        
        for product in products_to_delete[:50]:  # Sample first 50
            url = product.main_image_url or 'NULL'
            
            # Categorize the issue
            if not product.main_image_url or product.main_image_url in ['', 'null', 'undefined']:
                issue_type = 'Null/Empty'
            elif 'placeholder' in url.lower():
                issue_type = 'Placeholder'
            elif url.startswith('https://:0') or url.startswith('http://:0'):
                issue_type = 'Invalid Format'
            else:
                issue_type = 'Other'
            
            issue_breakdown[issue_type] = issue_breakdown.get(issue_type, 0) + 1
            
            sample_products.append({
                'id': product.id,
                'name': product.name,
                'image_url': url,
                'issue_type': issue_type,
                'category': product.category.name if product.category else 'Uncategorized',
                'seller': product.seller.display_name if product.seller else 'Unknown'
            })

        # Display breakdown
        self.stdout.write(self.style.WARNING('📋 BREAKDOWN BY ISSUE TYPE:'))
        self.stdout.write('-' * 80)
        for issue_type, count in sorted(issue_breakdown.items(), key=lambda x: -x[1]):
            self.stdout.write(f'  {issue_type:20} : {count:6} products')

        # Show sample products
        self.stdout.write(f'\n🔍 SAMPLE PRODUCTS (showing first {min(len(sample_products), 20)}):')
        self.stdout.write('-' * 80)
        for i, p in enumerate(sample_products[:20], 1):
            self.stdout.write(
                f"{i:2}. ID: {p['id']:6} | {p['issue_type']:15} | "
                f"{p['name'][:40]:40} | {p['seller'][:20]:20}"
            )

        # DRY RUN MODE
        if dry_run or not confirm:
            self.stdout.write('\n' + '=' * 80)
            self.stdout.write(self.style.WARNING('🔒 DRY-RUN MODE - NO CHANGES MADE'))
            self.stdout.write('=' * 80)
            self.stdout.write(f'\n⚠️  This would delete {total_count} products')
            self.stdout.write('\n💡 To actually delete these products, run:')
            self.stdout.write(self.style.SUCCESS(
                '   python manage.py safe_remove_broken_images --confirm\n'
            ))
            return

        # CONFIRMATION MODE - Create backup first
        if confirm:
            self.stdout.write('\n' + '=' * 80)
            self.stdout.write(self.style.ERROR('⚠️  DELETION MODE ACTIVATED'))
            self.stdout.write('=' * 80)
            
            # Create backup if requested
            if create_backup:
                self.stdout.write('\n📦 Creating backup before deletion...')
                backup_data = []
                
                for product in products_to_delete:
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
                    f'deleted_broken_images_{timestamp}.json'
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
            
            deleted_ids = list(products_to_delete.values_list('id', flat=True))
            deletion_result = products_to_delete.delete()
            
            self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully deleted {deletion_result[0]} products!'))
            
            # Save deletion log
            log_file = os.path.join(backup_path, f'deletion_log_{timestamp}.txt')
            with open(log_file, 'w') as f:
                f.write(f'Deletion performed at: {datetime.now().isoformat()}\n')
                f.write(f'Total products deleted: {deletion_result[0]}\n')
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

