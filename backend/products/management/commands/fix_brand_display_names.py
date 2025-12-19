#!/usr/bin/env python
"""
Fix empty display_name fields for brands
Sets display_name = name if empty
"""
from django.core.management.base import BaseCommand
from products.models import Brand

class Command(BaseCommand):
    help = 'Fixes empty display_name fields for brands'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Do not save changes to the database.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write('\n🏷️ FIXING BRAND DISPLAY NAMES')
        self.stdout.write('='*60)
        
        # Find brands with empty display_name
        brands_to_fix = Brand.objects.filter(display_name='')
        total = brands_to_fix.count()
        
        self.stdout.write(f'📊 Brands with empty display_name: {total:,}')
        
        if total == 0:
            self.stdout.write('✅ All brands have display names!')
            return
        
        if dry_run:
            self.stdout.write('\n🔍 DRY RUN - No changes will be made\n')
            self.stdout.write('Sample brands to fix:')
            for brand in brands_to_fix[:10]:
                self.stdout.write(f'  "{brand.name}" → "{brand.name}"')
            return
        
        # Fix all brands: set display_name = name
        self.stdout.write('\n🔧 Fixing display names...')
        
        for brand in brands_to_fix:
            brand.display_name = brand.name
            brand.save()
        
        self.stdout.write(f'\n✅ Fixed {total:,} brand display names!')
        self.stdout.write('='*60)

