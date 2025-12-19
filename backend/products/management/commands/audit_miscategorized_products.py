#!/usr/bin/env python3
"""
SAFE audit of miscategorized products
Detects products in wrong categories without making any changes
Run: python manage.py audit_miscategorized_products
"""

from django.core.management.base import BaseCommand
from products.models import CoreProduct, ProductCategory
from django.db.models import Count, Q
import re
from collections import defaultdict


class Command(BaseCommand):
    help = 'Safely audit miscategorized products (no changes made)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--category',
            type=str,
            default='Smartphones & Mobiles',
            help='Category to audit (default: Smartphones & Mobiles)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Number of suspicious products to show (default: 50)'
        )
        parser.add_argument(
            '--export',
            type=str,
            help='Export results to CSV file'
        )

    def handle(self, *args, **options):
        category_name = options['category']
        limit = options['limit']
        export_file = options.get('export')

        self.stdout.write(self.style.SUCCESS('=' * 100))
        self.stdout.write(self.style.SUCCESS('🔍 MISCATEGORIZED PRODUCTS AUDIT'))
        self.stdout.write(self.style.SUCCESS('=' * 100))
        self.stdout.write('')

        # Define category-specific keywords
        category_keywords = {
            'Smartphones & Mobiles': {
                'required': ['galaxy', 'iphone', 'oppo', 'vivo', 'xiaomi', 'realme', 'infinix',
                           'tecno', 'huawei', 'oneplus', 'nokia', 'motorola', 'redmi', 'poco',
                           'honor', 'asus rog phone', 'asus zenfone', 'blackberry', 'pixel',
                           'mi note', 'mi max', 'note ', 'pro ', 'plus ', 'ultra', 'lite',
                           'a0', 'a1', 'a2', 'a3', 'a5', 'a7', 'f1', 's2', 'm3', 'y1'],
                'broad': ['phone', 'mobile', 'smartphone', 'dual sim', 'android', 'ios',
                         '4g', '5g', 'lte', 'gsm', 'cdma', 'sim card', 'imei']
            },
            'Laptops & Computers': {
                'required': ['laptop', 'macbook', 'notebook', 'chromebook', 'ultrabook',
                           'dell', 'hp ', 'lenovo', 'asus', 'acer', 'msi', 'razer',
                           'thinkpad', 'pavilion', 'inspiron', 'vivobook', 'zenbook',
                           'ideapad', 'core i', 'ryzen ', 'celeron', 'pentium'],
                'broad': ['laptop', 'computer', 'pc', 'desktop', 'workstation', 'gaming pc']
            },
            'Home Appliances (Large)': {
                'required': ['fridge', 'refrigerator', 'washing machine', 'microwave',
                           'dishwasher', 'dryer', 'freezer', 'deep freezer', 'washer'],
                'broad': ['appliance', 'kitchen', 'home']
            },
            'Audio & Accessories': {
                'required': ['earbuds', 'headphones', 'speaker', 'soundbar', 'airpods',
                           'beats', 'bose', 'jbl', 'sony headphones', 'bluetooth speaker'],
                'broad': ['audio', 'sound', 'music', 'bluetooth', 'wireless']
            }
        }

        # Get keywords for this category
        keywords = category_keywords.get(category_name, {})
        required_keywords = keywords.get('required', [])
        broad_keywords = keywords.get('broad', [])

        self.stdout.write(f'📂 Auditing category: {category_name}')
        self.stdout.write('')

        # Get all products in this category
        try:
            category_obj = ProductCategory.objects.get(name=category_name)
        except ProductCategory.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Category "{category_name}" not found'))
            return

        products = CoreProduct.objects.filter(
            category=category_obj,
            is_active=True
        ).select_related('brand', 'seller')

        total_products = products.count()
        self.stdout.write(f'📊 Total products in category: {total_products}')
        self.stdout.write('')

        # Analyze each product
        miscategorized = []
        correctly_categorized = []

        for product in products:
            name_lower = product.name.lower()
            description_lower = (product.description or '').lower()
            combined_text = f"{name_lower} {description_lower}"

            # Check if product name contains any required keywords
            has_required = any(keyword.lower() in combined_text for keyword in required_keywords)
            has_broad = any(keyword.lower() in combined_text for keyword in broad_keywords)

            if not has_required and not has_broad:
                # Likely miscategorized
                miscategorized.append({
                    'id': product.id,
                    'name': product.name,
                    'brand': product.brand.display_name if product.brand else 'No Brand',
                    'seller': product.seller.display_name if product.seller else 'Unknown',
                    'price': product.price,
                    'category': product.category.name if product.category else 'No Category'
                })
            else:
                correctly_categorized.append(product)

        # Statistics
        miscategorized_count = len(miscategorized)
        correct_count = len(correctly_categorized)
        miscategorized_percentage = (miscategorized_count / total_products * 100) if total_products > 0 else 0

        self.stdout.write(self.style.SUCCESS('=' * 100))
        self.stdout.write(self.style.SUCCESS('📊 AUDIT RESULTS'))
        self.stdout.write(self.style.SUCCESS('=' * 100))
        self.stdout.write('')
        self.stdout.write(f'Total products:              {total_products}')
        self.stdout.write(f'Correctly categorized:       {correct_count} ({100-miscategorized_percentage:.1f}%)')
        self.stdout.write(f'Likely miscategorized:       {miscategorized_count} ({miscategorized_percentage:.1f}%)')
        self.stdout.write('')

        if miscategorized_count > 0:
            self.stdout.write(self.style.WARNING('=' * 100))
            self.stdout.write(self.style.WARNING(f'⚠️  SUSPICIOUS PRODUCTS (showing first {min(limit, miscategorized_count)}):'))
            self.stdout.write(self.style.WARNING('=' * 100))
            self.stdout.write('')

            for i, product in enumerate(miscategorized[:limit], 1):
                self.stdout.write(f"{i}. {product['name'][:80]}")
                self.stdout.write(f"   ID: {product['id']} | Brand: {product['brand']} | Seller: {product['seller']}")
                self.stdout.write(f"   Price: ₨{product['price']:,.0f}" if product['price'] else "   Price: N/A")
                self.stdout.write(f"   Current Category: {product['category']}")
                
                # Suggest better category
                suggested = self._suggest_category(product['name'])
                if suggested:
                    self.stdout.write(f"   💡 Suggested: {suggested}")
                self.stdout.write('')

        # Category breakdown of miscategorized products
        if miscategorized_count > 0:
            self.stdout.write(self.style.WARNING('=' * 100))
            self.stdout.write(self.style.WARNING('📊 PATTERN ANALYSIS'))
            self.stdout.write(self.style.WARNING('=' * 100))
            self.stdout.write('')

            # Analyze brands
            brand_counter = defaultdict(int)
            for p in miscategorized:
                brand_counter[p['brand']] += 1

            top_brands = sorted(brand_counter.items(), key=lambda x: x[1], reverse=True)[:10]
            self.stdout.write('Top brands with miscategorized products:')
            for brand, count in top_brands:
                self.stdout.write(f'  • {brand}: {count} products')
            self.stdout.write('')

            # Analyze sellers
            seller_counter = defaultdict(int)
            for p in miscategorized:
                seller_counter[p['seller']] += 1

            top_sellers = sorted(seller_counter.items(), key=lambda x: x[1], reverse=True)[:10]
            self.stdout.write('Top sellers with miscategorized products:')
            for seller, count in top_sellers:
                self.stdout.write(f'  • {seller}: {count} products')
            self.stdout.write('')

        # Export option
        if export_file and miscategorized:
            import csv
            import os
            os.makedirs('backend/backups', exist_ok=True)
            filepath = f'backend/backups/{export_file}'
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['id', 'name', 'brand', 'seller', 'price', 'category', 'suggested_category'])
                writer.writeheader()
                for p in miscategorized:
                    p['suggested_category'] = self._suggest_category(p['name']) or 'Unknown'
                    writer.writerow(p)
            
            self.stdout.write(self.style.SUCCESS(f'✅ Exported to: {filepath}'))
            self.stdout.write('')

        # Summary
        self.stdout.write(self.style.SUCCESS('=' * 100))
        self.stdout.write(self.style.SUCCESS('✅ AUDIT COMPLETE - NO CHANGES MADE'))
        self.stdout.write(self.style.SUCCESS('=' * 100))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('💡 NEXT STEPS:'))
        self.stdout.write('')
        if miscategorized_count > 0:
            self.stdout.write(f'1. Review the {miscategorized_count} suspicious products above')
            self.stdout.write('2. Export to CSV for detailed review:')
            self.stdout.write(f'   python manage.py audit_miscategorized_products --category="{category_name}" --export=miscategorized.csv')
            self.stdout.write('3. Create a fix command to recategorize these products')
        else:
            self.stdout.write(f'✅ Category "{category_name}" looks clean!')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('🧪 TRY OTHER CATEGORIES:'))
        self.stdout.write('   python manage.py audit_miscategorized_products --category="Laptops & Computers"')
        self.stdout.write('   python manage.py audit_miscategorized_products --category="Audio & Accessories"')
        self.stdout.write('   python manage.py audit_miscategorized_products --category="Home Appliances (Large)"')
        self.stdout.write('')

    def _suggest_category(self, product_name):
        """Suggest a better category based on product name"""
        name_lower = product_name.lower()

        # Category detection patterns
        patterns = {
            'Clothing & Fashion': ['shirt', 'pant', 'dress', 'jeans', 'jacket', 'coat', 'sweater', 
                                  'hoodie', 'tshirt', 't-shirt', 'kurta', 'shalwar', 'kameez',
                                  'suit', 'trouser', 'skirt', 'blouse', 'shawl', 'dupatta'],
            'Shoes & Accessories': ['shoes', 'sneakers', 'sandals', 'heels', 'boots', 'slippers',
                                   'belt', 'wallet', 'bag', 'purse', 'backpack', 'watch',
                                   'sunglasses', 'jewelry', 'necklace', 'bracelet', 'ring'],
            'Beauty & Personal Care': ['lipstick', 'makeup', 'foundation', 'mascara', 'perfume',
                                      'fragrance', 'cologne', 'cream', 'lotion', 'shampoo',
                                      'conditioner', 'soap', 'face wash', 'serum'],
            'Sports & Fitness': ['dumbbell', 'barbell', 'treadmill', 'bike', 'bicycle', 'cycle',
                                'yoga mat', 'exercise', 'fitness', 'gym', 'sports'],
            'Home & Living': ['furniture', 'sofa', 'chair', 'table', 'bed', 'mattress', 'pillow',
                            'curtain', 'carpet', 'rug', 'lamp', 'decoration', 'plant'],
            'Toys & Games': ['toy', 'doll', 'puzzle', 'board game', 'lego', 'action figure',
                           'stuffed', 'plush', 'kids toy', 'baby toy'],
            'Kitchen Appliances (Small)': ['blender', 'juicer', 'toaster', 'kettle', 'mixer',
                                          'grinder', 'coffee maker', 'rice cooker'],
            'Automobiles & Accessories': ['car', 'vehicle', 'auto', 'headlamp', 'car seat',
                                         'tire', 'wheel', 'brake', 'engine', 'windshield',
                                         'bumper', 'dashboard', 'steering'],
            'Books & Stationery': ['book', 'novel', 'diary', 'notebook', 'pen', 'pencil',
                                  'stationery', 'paper', 'eraser', 'ruler'],
            'Gardening & Outdoor': ['plant', 'seed', 'pot', 'planter', 'soil', 'fertilizer',
                                   'garden', 'lawn', 'outdoor', 'tree'],
        }

        for category, keywords in patterns.items():
            for keyword in keywords:
                if keyword in name_lower:
                    return category

        return None

