#!/usr/bin/env python3
"""
Management command to check product availability on source platforms
Can be run manually or scheduled via cron
"""

from django.core.management.base import BaseCommand
from django.db.models import Q
from products.models import CoreProduct
from products.utils.availability_checker import check_product_availability
from datetime import timedelta
from django.utils import timezone
import time


class Command(BaseCommand):
    help = 'Check product availability on source platforms and mark unavailable ones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--platform',
            type=str,
            help='Only check products from specific platform (e.g., sehgalmotors.pk)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of products to check (default: 100)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force check even if recently checked'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be checked without making changes'
        )
        parser.add_argument(
            '--product-id',
            type=int,
            help='Check specific product by ID'
        )
        parser.add_argument(
            '--older-than-days',
            type=int,
            default=7,
            help='Only check products last checked more than X days ago (default: 7)'
        )

    def handle(self, *args, **options):
        platform = options['platform']
        limit = options['limit']
        force = options['force']
        dry_run = options['dry_run']
        product_id = options['product_id']
        older_than_days = options['older_than_days']

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('PRODUCT AVAILABILITY CHECKER'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        # Build query
        if product_id:
            # Check specific product
            products = CoreProduct.objects.filter(id=product_id, is_active=True)
            self.stdout.write(f"\n🎯 Checking specific product ID: {product_id}")
        else:
            # Check multiple products
            products = CoreProduct.objects.filter(is_active=True)
            
            # Filter by platform if specified
            if platform:
                products = products.filter(seller__display_name__icontains=platform)
                self.stdout.write(f"\n🔍 Platform filter: {platform}")
            
            # Filter by last check date (unless force)
            if not force:
                cutoff_date = timezone.now() - timedelta(days=older_than_days)
                products = products.filter(
                    Q(last_availability_check__isnull=True) |
                    Q(last_availability_check__lt=cutoff_date)
                )
                self.stdout.write(f"📅 Only checking products last checked > {older_than_days} days ago")
            
            # Limit results
            products = products[:limit]
            self.stdout.write(f"📊 Products to check: {products.count()}/{limit} (limit)")

        if not products.exists():
            self.stdout.write(self.style.WARNING("\n⚠️ No products found matching criteria"))
            return

        # Dry run info
        if dry_run:
            self.stdout.write(self.style.WARNING("\n🔸 DRY RUN MODE - No changes will be saved\n"))

        # Check each product
        self.stdout.write("\n" + "-" * 80)
        self.stdout.write("CHECKING PRODUCTS...")
        self.stdout.write("-" * 80 + "\n")

        results = {
            'active': 0,
            'unavailable': 0,
            'error': 0,
            'skipped': 0
        }

        for i, product in enumerate(products, 1):
            self.stdout.write(f"\n[{i}/{products.count()}] {product.name[:60]}...")
            self.stdout.write(f"           ID: {product.id} | Platform: {product.seller.display_name if product.seller else 'N/A'}")
            
            try:
                # Check availability
                result = check_product_availability(
                    product=product,
                    force=force,
                    update_db=not dry_run  # Only update if not dry run
                )
                
                status = result['status']
                results[status] = results.get(status, 0) + 1
                
                if status == 'active':
                    self.stdout.write(self.style.SUCCESS(f"           ✅ ACTIVE - {result['reason']}"))
                elif status == 'unavailable':
                    self.stdout.write(self.style.ERROR(f"           ❌ UNAVAILABLE - {result['reason']}"))
                    if not dry_run and product.consecutive_failures >= 3:
                        self.stdout.write(self.style.WARNING(f"              ⚠️ Marked as INACTIVE (3+ failures)"))
                elif status == 'error':
                    self.stdout.write(self.style.WARNING(f"           ⚠️ ERROR - {result['reason']}"))
                else:
                    self.stdout.write(f"           ⏭️ SKIPPED - {result['reason']}")
                
                # Be polite - small delay between checks
                if i < products.count():
                    time.sleep(0.5)
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"           ❌ EXCEPTION: {str(e)}"))
                results['error'] += 1

        # Summary
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write('=' * 80)
        self.stdout.write(f"\n✅ Active/Available: {results['active']}")
        self.stdout.write(f"❌ Unavailable: {results['unavailable']}")
        self.stdout.write(f"⚠️ Errors: {results['error']}")
        self.stdout.write(f"⏭️ Skipped: {results['skipped']}")
        self.stdout.write(f"\n📊 Total checked: {sum(results.values())}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n🔸 DRY RUN - No changes were saved to database"))
        
        self.stdout.write('\n' + '=' * 80)

        # Recommendations
        if results['unavailable'] > 0:
            self.stdout.write(self.style.WARNING('\n💡 RECOMMENDATIONS:'))
            self.stdout.write('   - Products marked unavailable will show warning message to users')
            self.stdout.write('   - After 3 consecutive failures, products are automatically marked inactive')
            self.stdout.write('   - Re-scrape these products to get updated data or remove them')
            self.stdout.write('=' * 80)

