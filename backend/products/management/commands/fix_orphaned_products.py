#!/usr/bin/env python
"""
Fix orphaned products by:
1. Deleting duplicates (products with same name+platform that have ecommerce data elsewhere)
2. Keeping unique products (may be manually added or have value)
"""
from django.core.management.base import BaseCommand
from products.models import CoreProduct
from django.db.models import Q
from django.db import transaction

class Command(BaseCommand):
    help = 'Fixes orphaned products (no ecommerce/Instagram data)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Do not delete products, just show what would be deleted.',
        )
        parser.add_argument(
            '--delete-duplicates',
            action='store_true',
            help='Delete duplicate orphaned products',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        delete_duplicates = options['delete_duplicates']
        
        self.stdout.write('\n🔍 ORPHANED PRODUCTS FIX')
        self.stdout.write('='*60)
        
        # Find orphaned products
        orphaned = CoreProduct.objects.filter(
            Q(ecommerce_data__isnull=True) & Q(instagram_data__isnull=True)
        ).select_related('seller__platform', 'category', 'brand')
        
        total_orphaned = orphaned.count()
        total_products = CoreProduct.objects.count()
        
        self.stdout.write(f'📊 Total Products: {total_products:,}')
        self.stdout.write(f'❌ Orphaned Products: {total_orphaned:,} ({total_orphaned/total_products*100:.1f}%)')
        
        if total_orphaned == 0:
            self.stdout.write('\n✅ No orphaned products!')
            return
        
        # Find duplicates
        duplicates_to_delete = []
        unique_orphans = []
        
        self.stdout.write('\n🔄 Analyzing orphaned products...')
        
        for orphan in orphaned:
            # Check if there's another product with same name and platform that has ecommerce data
            has_duplicate = CoreProduct.objects.filter(
                name=orphan.name,
                seller__platform=orphan.seller.platform,
                ecommerce_data__isnull=False
            ).exclude(id=orphan.id).exists()
            
            if has_duplicate:
                duplicates_to_delete.append(orphan)
            else:
                unique_orphans.append(orphan)
        
        self.stdout.write(f'\n📊 ANALYSIS RESULTS:')
        self.stdout.write(f'   Duplicates (can be deleted): {len(duplicates_to_delete):,}')
        self.stdout.write(f'   Unique orphans (keep): {len(unique_orphans):,}')
        
        if dry_run or not delete_duplicates:
            self.stdout.write('\n🔍 DRY RUN - Showing sample duplicates:')
            self.stdout.write('-'*60)
            
            for p in duplicates_to_delete[:10]:
                self.stdout.write(f'\n[{p.id}] {p.name[:60]}')
                self.stdout.write(f'  Platform: {p.seller.platform.display_name}')
                self.stdout.write(f'  Reason: Duplicate exists with ecommerce data')
            
            self.stdout.write('\n' + '='*60)
            self.stdout.write(f'\n💡 Run with --delete-duplicates to remove {len(duplicates_to_delete):,} duplicates')
            return
        
        # Delete duplicates
        if delete_duplicates:
            self.stdout.write(f'\n🗑️  Deleting {len(duplicates_to_delete):,} duplicate orphaned products...')
            
            with transaction.atomic():
                deleted_count = 0
                for orphan in duplicates_to_delete:
                    orphan.delete()
                    deleted_count += 1
                    
                    if deleted_count % 100 == 0:
                        self.stdout.write(f'   Deleted {deleted_count}/{len(duplicates_to_delete)}...')
            
            self.stdout.write(f'\n✅ Deleted {deleted_count:,} duplicate orphaned products!')
            self.stdout.write(f'✅ Kept {len(unique_orphans):,} unique orphaned products')
            
            # Final stats
            remaining_orphaned = CoreProduct.objects.filter(
                Q(ecommerce_data__isnull=True) & Q(instagram_data__isnull=True)
            ).count()
            
            remaining_total = CoreProduct.objects.count()
            
            self.stdout.write(f'\n📊 FINAL STATUS:')
            self.stdout.write(f'   Total Products: {remaining_total:,}')
            self.stdout.write(f'   Orphaned Products: {remaining_orphaned:,} ({remaining_orphaned/remaining_total*100:.1f}%)')
            self.stdout.write('='*60)

