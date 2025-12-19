#!/usr/bin/env python3
"""
Upgrade HTTP image URLs to HTTPS for security and browser compatibility
Modern browsers block HTTP resources on HTTPS pages (mixed content)
"""

from django.core.management.base import BaseCommand
from django.db.models import Q
from products.models import CoreProduct


class Command(BaseCommand):
    help = 'Upgrade HTTP image URLs to HTTPS to fix mixed content issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('UPGRADE HTTP URLS TO HTTPS'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        # Find products with HTTP URLs
        products_to_fix = CoreProduct.objects.filter(
            is_active=True,
            main_image_url__startswith='http://'
        )

        total_count = products_to_fix.count()

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('\n✅ No HTTP URLs found! All images use HTTPS.'))
            return

        self.stdout.write(f'\n📊 Found {total_count} products with HTTP URLs (insecure)')

        # Group by platform
        from django.db.models import Count
        platforms = products_to_fix.values('seller__display_name').annotate(
            count=Count('id')
        ).order_by('-count')

        self.stdout.write('\n🏪 Breakdown by platform:')
        for plat in platforms[:10]:
            plat_name = plat['seller__display_name'] or 'Unknown'
            count = plat['count']
            self.stdout.write(f'  - {plat_name}: {count} products')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY RUN MODE - No changes will be made'))
            self.stdout.write('\nSample URLs that would be upgraded:')
            for p in products_to_fix[:10]:
                old_url = p.main_image_url
                new_url = 'https://' + old_url[7:] if old_url.startswith('http://') else old_url
                self.stdout.write(f'\nProduct: {p.name[:60]}')
                self.stdout.write(f'  OLD: {old_url[:100]}')
                self.stdout.write(f'  NEW: {new_url[:100]}')
        else:
            self.stdout.write(self.style.WARNING('\n🔧 Upgrading URLs to HTTPS...'))
            
            fixed_count = 0
            for product in products_to_fix:
                old_url = product.main_image_url
                if old_url and old_url.startswith('http://'):
                    # Replace http:// with https://
                    product.main_image_url = 'https://' + old_url[7:]
                    product.save(update_fields=['main_image_url'])
                    fixed_count += 1
                    
                    if fixed_count % 50 == 0:
                        self.stdout.write(f'  Upgraded {fixed_count}/{total_count}...')

            self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully upgraded {fixed_count} URLs to HTTPS!'))

        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('COMPLETE'))
        self.stdout.write('=' * 80)

        if not dry_run and total_count > 0:
            self.stdout.write('\n💡 Why this matters:')
            self.stdout.write('   - Modern browsers block HTTP content on HTTPS pages (mixed content)')
            self.stdout.write('   - Images will now load properly in trending products and all views')
            self.stdout.write('   - Better security and SEO')
            self.stdout.write('\n💡 Verify the fix by running:')
            self.stdout.write('   python manage.py check_image_health')

