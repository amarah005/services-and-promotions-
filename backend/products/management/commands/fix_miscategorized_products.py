#!/usr/bin/env python3
"""
SAFE auto-fix for miscategorized products
Multiple safety checks, dry-run mode, and backups
Run: python manage.py fix_miscategorized_products --dry-run (SAFE)
"""

import json
import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from products.models import CoreProduct, ProductCategory
from django.db.models import Q
from collections import defaultdict
import os


class Command(BaseCommand):
    help = 'Safely fix miscategorized products (with dry-run and backup)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what WOULD be changed without actually changing (RECOMMENDED FIRST)'
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Actually fix products (requires explicit confirmation)'
        )
        parser.add_argument(
            '--category',
            type=str,
            default='Smartphones & Mobiles',
            help='Category to fix (default: Smartphones & Mobiles)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of products to fix (for testing)'
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
        category_name = options['category']
        limit = options['limit']
        backup_path = options['backup_path']

        self.stdout.write(self.style.SUCCESS('=' * 100))
        self.stdout.write(self.style.SUCCESS('🔧 SAFE PRODUCT RE-CATEGORIZATION'))
        self.stdout.write(self.style.SUCCESS('=' * 100))
        self.stdout.write('')

        if not dry_run and not confirm:
            self.stdout.write(self.style.ERROR('❌ ERROR: Must use either --dry-run or --confirm'))
            self.stdout.write(self.style.WARNING('   Recommended: Run with --dry-run first to preview changes'))
            self.stdout.write(self.style.WARNING('   Then use --confirm to actually apply changes'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
        else:
            self.stdout.write(self.style.ERROR('⚠️  LIVE MODE - Changes will be applied!'))
        self.stdout.write('')

        # Get category
        try:
            category_obj = ProductCategory.objects.get(name=category_name)
        except ProductCategory.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Category "{category_name}" not found'))
            return

        # Get all products in this category
        products = CoreProduct.objects.filter(
            category=category_obj,
            is_active=True
        ).select_related('brand', 'seller', 'category')

        if limit:
            products = products[:limit]

        total_products = products.count()
        self.stdout.write(f'📂 Category: {category_name}')
        self.stdout.write(f'📊 Products to check: {total_products}')
        self.stdout.write('')

        # Analyze and suggest fixes
        fixes = []
        no_change_needed = []

        self.stdout.write('🔍 Analyzing products...')
        self.stdout.write('')

        for product in products:
            name_lower = product.name.lower()
            suggested_category_name = self._suggest_category(product.name)

            # If suggested category is different from current, mark for fix
            if suggested_category_name and suggested_category_name != category_name:
                try:
                    suggested_category = ProductCategory.objects.get(name=suggested_category_name)
                    fixes.append({
                        'product': product,
                        'current_category': category_name,
                        'suggested_category': suggested_category_name,
                        'suggested_category_obj': suggested_category
                    })
                except ProductCategory.DoesNotExist:
                    # Suggested category doesn't exist - mark for "General" or keep as-is
                    pass
            elif not suggested_category_name:
                # Can't determine category - check if it matches current
                if not self._matches_category(product.name, category_name):
                    # Doesn't match, suggest General (use first one if multiple exist)
                    try:
                        general_category = ProductCategory.objects.filter(name='General').first()
                        if general_category:
                            fixes.append({
                                'product': product,
                                'current_category': category_name,
                                'suggested_category': 'General',
                                'suggested_category_obj': general_category
                            })
                    except Exception:
                        pass
            else:
                no_change_needed.append(product)

        fixes_count = len(fixes)
        no_change_count = len(no_change_needed)

        # Display results
        self.stdout.write(self.style.SUCCESS('=' * 100))
        self.stdout.write(self.style.SUCCESS('📊 ANALYSIS COMPLETE'))
        self.stdout.write(self.style.SUCCESS('=' * 100))
        self.stdout.write('')
        self.stdout.write(f'Total products checked:      {total_products}')
        self.stdout.write(f'Correctly categorized:       {no_change_count}')
        self.stdout.write(f'Need recategorization:       {fixes_count}')
        self.stdout.write('')

        if fixes_count == 0:
            self.stdout.write(self.style.SUCCESS('✅ No miscategorized products found!'))
            return

        # Show proposed changes
        self.stdout.write(self.style.WARNING('=' * 100))
        self.stdout.write(self.style.WARNING(f'📋 PROPOSED CHANGES (showing first 50):'))
        self.stdout.write(self.style.WARNING('=' * 100))
        self.stdout.write('')

        # Group by suggested category
        category_groups = defaultdict(list)
        for fix in fixes:
            category_groups[fix['suggested_category']].append(fix)

        for suggested_cat, items in sorted(category_groups.items()):
            self.stdout.write(self.style.SUCCESS(f'\n➡️  Move to "{suggested_cat}" ({len(items)} products):'))
            for i, fix in enumerate(items[:10], 1):  # Show first 10 per category
                product = fix['product']
                self.stdout.write(f"   {i}. {product.name[:70]}")
                self.stdout.write(f"      ID: {product.id} | Brand: {product.brand.display_name if product.brand else 'No Brand'}")
            
            if len(items) > 10:
                self.stdout.write(f"   ... and {len(items) - 10} more")

        self.stdout.write('')

        # Create backup if not dry-run
        if not dry_run and confirm:
            self.stdout.write(self.style.WARNING('💾 Creating backup...'))
            
            # Create backup
            os.makedirs(backup_path, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(backup_path, f'recategorize_backup_{timestamp}.json')

            backup_data = []
            for fix in fixes:
                product = fix['product']
                backup_data.append({
                    'id': product.id,
                    'name': product.name,
                    'old_category_id': product.category_id,
                    'old_category_name': fix['current_category'],
                    'new_category_name': fix['suggested_category'],
                    'brand': product.brand.display_name if product.brand else None,
                    'price': float(product.price) if product.price else None
                })

            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)

            self.stdout.write(self.style.SUCCESS(f'✅ Backup created: {backup_file}'))
            self.stdout.write('')

            # Apply fixes
            self.stdout.write(self.style.WARNING('🔄 Applying changes...'))
            self.stdout.write('')

            fixed_count = 0
            errors = []

            for fix in fixes:
                try:
                    product = fix['product']
                    old_category = product.category.name if product.category else 'None'
                    product.category = fix['suggested_category_obj']
                    product.save(update_fields=['category'])
                    fixed_count += 1
                    
                    if fixed_count % 50 == 0:
                        self.stdout.write(f'   Progress: {fixed_count}/{fixes_count} fixed...')
                        
                except Exception as e:
                    errors.append({
                        'product_id': fix['product'].id,
                        'error': str(e)
                    })

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 100))
            self.stdout.write(self.style.SUCCESS('✅ RECATEGORIZATION COMPLETE'))
            self.stdout.write(self.style.SUCCESS('=' * 100))
            self.stdout.write('')
            self.stdout.write(f'Successfully fixed:  {fixed_count} products')
            self.stdout.write(f'Errors:              {len(errors)} products')
            self.stdout.write(f'Backup saved to:     {backup_file}')
            self.stdout.write('')

            if errors:
                self.stdout.write(self.style.ERROR('❌ ERRORS:'))
                for error in errors[:10]:
                    self.stdout.write(f"   Product ID {error['product_id']}: {error['error']}")
                if len(errors) > 10:
                    self.stdout.write(f'   ... and {len(errors) - 10} more errors')
                self.stdout.write('')

        else:
            # Dry run summary
            self.stdout.write(self.style.SUCCESS('=' * 100))
            self.stdout.write(self.style.SUCCESS('📋 DRY RUN SUMMARY'))
            self.stdout.write(self.style.SUCCESS('=' * 100))
            self.stdout.write('')
            self.stdout.write(f'Would fix {fixes_count} products across {len(category_groups)} categories')
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('💡 TO APPLY THESE CHANGES:'))
            self.stdout.write(f'   python manage.py fix_miscategorized_products --category="{category_name}" --confirm')
            self.stdout.write('')
            self.stdout.write(self.style.ERROR('⚠️  WARNING: This will modify your database!'))
            self.stdout.write(self.style.SUCCESS('✅ A backup will be created automatically'))
            self.stdout.write('')

    def _suggest_category(self, product_name):
        """Suggest a better category based on product name"""
        name_lower = product_name.lower()

        # Category detection patterns (ordered by specificity)
        patterns = {
            # Specific first
            'Smartphones & Mobiles': [
                'galaxy', 'iphone', 'oppo', 'vivo', 'xiaomi', 'realme', 'infinix',
                'tecno', 'huawei', 'oneplus', 'nokia', 'motorola', 'redmi', 'poco',
                'honor', 'asus rog phone', 'asus zenfone', 'blackberry', 'pixel',
                'mi note', 'mi max', 'note 10', 'note 20', 'note 9', 
                's21', 's22', 's23', 's24', 'a53', 'a73', 'a13', 'a33',
                'pro max', 'pro+', 'lite 5g'
            ],
            'Laptops & Computers': [
                'laptop', 'macbook', 'notebook', 'chromebook', 'ultrabook',
                'thinkpad', 'pavilion', 'inspiron', 'vivobook', 'zenbook',
                'ideapad', 'core i3', 'core i5', 'core i7', 'ryzen 3', 'ryzen 5'
            ],
            'Clothing & Fashion': [
                'shirt', 'pant', 'dress', 'jeans', 'jacket', 'coat', 'sweater', 
                'hoodie', 't-shirt', 'kurta', 'shalwar', 'kameez', 'trouser',
                'suit', 'skirt', 'blouse', 'shawl', 'dupatta', 'lawn', 'cotton',
                'unstitched', 'stitched', 'embroidered', 'printed'
            ],
            'Toys & Games': [
                'toy ', 'doll', 'puzzle', 'board game', 'lego', 'action figure',
                'stuffed', 'plush', 'kids toy', 'baby toy', 'rc car', 'remote control',
                'blaster', 'nerf', 'fidget', 'slime', 'play set'
            ],
            'Books & Stationery': [
                'book', 'novel', 'diary', 'notebook', 'pen', 'pencil', 'marker',
                'stationery', 'paper', 'eraser', 'ruler', 'flash cards',
                'paint pen', 'acrylic paint'
            ],
            'Beauty & Personal Care': [
                'lipstick', 'makeup', 'foundation', 'mascara', 'perfume',
                'fragrance', 'cologne', 'cream', 'lotion', 'shampoo',
                'conditioner', 'soap', 'face wash', 'serum', 'nail polish'
            ],
            'Shoes & Accessories': [
                'shoes', 'sneakers', 'sandals', 'heels', 'boots', 'slippers',
                'adilette', 'slides', 'flip flop'
            ],
            'Home & Living': [
                'furniture', 'sofa', 'chair', 'table', 'bed', 'mattress', 'pillow',
                'curtain', 'carpet', 'rug', 'lamp', 'decoration', 'pill box',
                'night light', 'portable light'
            ],
            'Gardening & Outdoor': [
                'plant', 'seed', 'pot', 'planter', 'soil', 'fertilizer',
                'garden', 'lawn', 'outdoor', 'tree', 'flower', 'succulent',
                'aeonium', 'cactus', 'herb'
            ],
            'Home Appliances (Large)': [
                'fridge', 'refrigerator', 'washing machine', 'microwave',
                'dishwasher', 'dryer', 'freezer', 'deep freezer', 'washer',
                'dawlance', 'pel ', 'haier', 'orient fridge'
            ],
            'Kitchen Appliances (Small)': [
                'blender', 'juicer', 'toaster', 'kettle', 'mixer',
                'grinder', 'coffee maker', 'rice cooker', 'air fryer'
            ],
            'Audio & Accessories': [
                'earbuds', 'headphones', 'speaker', 'soundbar', 'airpods',
                'beats', 'bose', 'jbl', 'bluetooth speaker', 'wireless earbuds',
                'wired headphones'
            ],
            'Automobiles & Accessories': [
                'car ', 'vehicle', 'auto', 'headlamp', 'car seat', 'tire', 'wheel',
                'brake', 'engine', 'windshield', 'bumper', 'dashboard', 'steering',
                'rc tank', 'toy car', 'car rotate', 'future car'
            ],
            'Cooling & Heating': [
                'ac ', 'air conditioner', 'fan', 'cooler', 'heater', 'geyser',
                'split ac', 'window ac', 'portable ac', 'tower fan'
            ],
            'Entertainment': [
                'tv', 'television', 'smart tv', 'led tv', 'projector', 'screen',
                'home theater', 'soundbar', 'streaming device'
            ]
        }

        # Analyze each product
        fixes_to_apply = []

        for product in products:
            name_lower = product.name.lower()
            description_lower = (product.description or '').lower()
            combined_text = f"{name_lower} {description_lower[:200]}"

            # Check current category validity
            current_keywords = patterns.get(category_name, [])
            matches_current = any(keyword.lower() in combined_text for keyword in current_keywords)

            if not matches_current:
                # Doesn't match current category - find better one
                suggested = self._suggest_category(product.name)
                
                if suggested and suggested != category_name:
                    try:
                        suggested_cat_obj = ProductCategory.objects.get(name=suggested)
                        fixes_to_apply.append({
                            'product': product,
                            'old_category': category_name,
                            'new_category': suggested,
                            'new_category_obj': suggested_cat_obj,
                            'reason': f'Name contains {suggested.lower()} keywords'
                        })
                    except ProductCategory.DoesNotExist:
                        pass

        total_fixes = len(fixes_to_apply)

        # Display summary
        self.stdout.write(self.style.SUCCESS('=' * 100))
        self.stdout.write(self.style.SUCCESS('📊 ANALYSIS RESULTS'))
        self.stdout.write(self.style.SUCCESS('=' * 100))
        self.stdout.write('')
        self.stdout.write(f'Products to recategorize: {total_fixes}')
        self.stdout.write('')

        if total_fixes == 0:
            self.stdout.write(self.style.SUCCESS('✅ No miscategorizations detected!'))
            return

        # Group by new category
        category_groups = defaultdict(list)
        for fix in fixes_to_apply:
            category_groups[fix['new_category']].append(fix)

        self.stdout.write(self.style.WARNING('📋 CHANGES TO BE MADE:'))
        self.stdout.write('')
        for new_cat, items in sorted(category_groups.items()):
            self.stdout.write(f'➡️  Move to "{new_cat}": {len(items)} products')
            for i, fix in enumerate(items[:5], 1):
                self.stdout.write(f"   {i}. {fix['product'].name[:65]}")
            if len(items) > 5:
                self.stdout.write(f'   ... and {len(items) - 5} more')
            self.stdout.write('')

        # Apply changes if confirm mode
        if not dry_run and confirm:
            self.stdout.write(self.style.WARNING('💾 Creating backup...'))
            
            os.makedirs(backup_path, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(backup_path, f'recategorize_{category_name.replace(" ", "_")}_{timestamp}.json')

            backup_data = []
            for fix in fixes_to_apply:
                product = fix['product']
                backup_data.append({
                    'id': product.id,
                    'name': product.name,
                    'old_category_id': product.category_id,
                    'old_category_name': fix['old_category'],
                    'new_category_name': fix['new_category'],
                    'brand': product.brand.display_name if product.brand else None,
                    'seller': product.seller.display_name if product.seller else None
                })

            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)

            self.stdout.write(self.style.SUCCESS(f'✅ Backup created: {backup_file}'))
            self.stdout.write('')

            # Apply changes
            self.stdout.write(self.style.WARNING('🔄 Applying changes...'))
            fixed_count = 0

            for fix in fixes_to_apply:
                try:
                    product = fix['product']
                    product.category = fix['new_category_obj']
                    product.save(update_fields=['category'])
                    fixed_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   Error fixing product {product.id}: {e}"))

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 100))
            self.stdout.write(self.style.SUCCESS('✅ RECATEGORIZATION COMPLETE'))
            self.stdout.write(self.style.SUCCESS('=' * 100))
            self.stdout.write('')
            self.stdout.write(f'Successfully fixed:  {fixed_count} products')
            self.stdout.write(f'Backup saved to:     {backup_file}')
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('💡 RECOMMENDATION: Re-generate embeddings for better AI search'))
            self.stdout.write('   python manage.py generate_embeddings --force')
            self.stdout.write('')

        else:
            # Dry run instructions
            self.stdout.write(self.style.SUCCESS('=' * 100))
            self.stdout.write(self.style.SUCCESS('✅ DRY RUN COMPLETE - NO CHANGES MADE'))
            self.stdout.write(self.style.SUCCESS('=' * 100))
            self.stdout.write('')
            self.stdout.write(f'Would fix {total_fixes} products')
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('💡 TO APPLY THESE CHANGES:'))
            self.stdout.write(f'   python manage.py fix_miscategorized_products --category="{category_name}" --confirm')
            self.stdout.write('')
            self.stdout.write(self.style.ERROR('⚠️  This will modify your database (backup will be created)'))
            self.stdout.write('')

    def _suggest_category(self, product_name):
        """Suggest category based on product name keywords"""
        name_lower = product_name.lower()

        # Ordered by specificity (check specific patterns first)
        category_patterns = [
            ('Smartphones & Mobiles', ['galaxy', 'iphone', 'samsung a', 'oppo ', 'vivo ', 'xiaomi', 
                                      'realme', 'infinix', 'tecno', 'smartphone', 'mobile phone']),
            ('Laptops & Computers', ['laptop', 'macbook', 'notebook', 'chromebook', 'thinkpad',
                                    'pavilion', 'inspiron', 'vivobook', 'core i', 'ryzen']),
            ('Toys & Games', ['toy', 'doll', 'puzzle', 'lego', 'blaster', 'rc car', 'remote control toy',
                             'kids toy', 'baby toy', 'play set', 'action figure']),
            ('Clothing & Fashion', ['shirt', 'pant', 'dress', 'jeans', 'trouser', 'kurta', 'kameez',
                                   'lawn', 'unstitched', 'embroidered', 'printed dress', 'suit 3pc']),
            ('Books & Stationery', ['book', 'novel', 'diary', 'notebook', 'pen', 'pencil', 'marker',
                                   'paint pen', 'flash cards', 'stationery']),
            ('Shoes & Accessories', ['shoes', 'sneakers', 'sandals', 'heels', 'boots', 'adilette',
                                    'slides', 'slippers', 'flip flop']),
            ('Home & Living', ['furniture', 'sofa', 'chair', 'table', 'curtain', 'lamp',
                              'pill box', 'night light', 'portable light']),
            ('Gardening & Outdoor', ['plant', 'seed', 'pot', 'planter', 'aeonium', 'cactus',
                                    'succulent', 'flower', 'tree', 'herb']),
            ('Home Appliances (Large)', ['fridge', 'refrigerator', 'washing machine', 'dawlance',
                                        'pel ', 'haier', 'deep freezer']),
            ('Kitchen Appliances (Small)', ['blender', 'juicer', 'toaster', 'kettle', 'mixer']),
            ('Automobiles & Accessories', ['car ', 'vehicle', 'auto', 'headlamp', 'car seat',
                                          'dashboard', 'windshield', 'bumper']),
        ]

        for category, keywords in category_patterns:
            for keyword in keywords:
                if keyword in name_lower:
                    return category

        return None

    def _matches_category(self, product_name, category_name):
        """Check if product matches its current category"""
        suggested = self._suggest_category(product_name)
        return suggested == category_name if suggested else False

