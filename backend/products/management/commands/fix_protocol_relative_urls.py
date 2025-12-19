#!/usr/bin/env python3
"""
Fix protocol-relative image URLs (starting with //) by adding https:// prefix
"""

from django.core.management.base import BaseCommand
from django.db.models import Q
from products.models import CoreProduct


class Command(BaseCommand):
    help = 'Fix protocol-relative image URLs by adding https:// prefix'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('FIX PROTOCOL-RELATIVE IMAGE URLS'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        # Find products with protocol-relative URLs
        products_to_fix = CoreProduct.objects.filter(
            is_active=True,
            main_image_url__startswith='//'
        )

        total_count = products_to_fix.count()

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('\n✅ No broken URLs found! All images are properly formatted.'))
            return

        self.stdout.write(f'\n📊 Found {total_count} products with protocol-relative URLs')

        # Group by platform
        from django.db.models import Count
        platforms = products_to_fix.values('seller__display_name').annotate(
            count=Count('id')
        ).order_by('-count')

        self.stdout.write('\n🏪 Breakdown by platform:')
        for plat in platforms:
            plat_name = plat['seller__display_name'] or 'Unknown'
            count = plat['count']
            self.stdout.write(f'  - {plat_name}: {count} products')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY RUN MODE - No changes will be made'))
            self.stdout.write('\nSample URLs that would be fixed:')
            for p in products_to_fix[:10]:
                old_url = p.main_image_url
                new_url = 'https:' + old_url if old_url.startswith('//') else old_url
                self.stdout.write(f'\nProduct: {p.name[:60]}')
                self.stdout.write(f'  OLD: {old_url[:100]}')
                self.stdout.write(f'  NEW: {new_url[:100]}')
        else:
            self.stdout.write(self.style.WARNING('\n🔧 Fixing URLs...'))
            
            fixed_count = 0
            for product in products_to_fix:
                old_url = product.main_image_url
                if old_url and old_url.startswith('//'):
                    # Add https: prefix
                    product.main_image_url = 'https:' + old_url
                    product.save(update_fields=['main_image_url'])
                    fixed_count += 1
                    
                    if fixed_count % 50 == 0:
                        self.stdout.write(f'  Fixed {fixed_count}/{total_count}...')

            self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully fixed {fixed_count} image URLs!'))

        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('COMPLETE'))
        self.stdout.write('=' * 80)

        if not dry_run and total_count > 0:
            self.stdout.write('\n💡 Tip: Verify the fix by running:')
            self.stdout.write('   python manage.py check_image_health')

