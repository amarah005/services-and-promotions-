#!/usr/bin/env python
"""
Django management command to import Toys & Games products from CSV
"""

import os
import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import Platform, Brand, Seller, ProductCategory, CoreProduct, EcommerceProduct
from urllib.parse import urlparse
import re

class Command(BaseCommand):
    help = 'Import Toys & Games products from CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')
        parser.add_argument('--preview', action='store_true', help='Preview mode - only show first 10 products')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        preview_mode = options['preview']
        
        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f'CSV file not found: {csv_file}'))
            return

        self.stdout.write(f'Importing Toys & Games products from {csv_file}')
        
        # Create or get main category
        main_category, created = ProductCategory.objects.get_or_create(
            name="Toys & Games",
            defaults={
                'slug': 'toys-games',
                'description': 'Toys, games, and educational products for children',
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(f'Created main category: {main_category.name}')
        else:
            self.stdout.write(f'Using existing category: {main_category.name}')

        # Create subcategories
        subcategories = {
            'Educational Toys': {
                'slug': 'educational-toys',
                'description': 'Learning toys, puzzles, building sets, and educational games'
            },
            'Dolls & Action Figures': {
                'slug': 'dolls-action-figures', 
                'description': 'Dolls, action figures, stuffed toys, and collectibles'
            },
            'Board & Indoor Games': {
                'slug': 'board-indoor-games',
                'description': 'Board games, card games, puzzles, and indoor activities'
            },
            'Outdoor Toys': {
                'slug': 'outdoor-toys',
                'description': 'Outdoor play equipment, sports toys, and active games'
            }
        }

        category_objects = {}
        for subcat_name, subcat_data in subcategories.items():
            subcategory, created = ProductCategory.objects.get_or_create(
                name=subcat_name,
                parent=main_category,
                defaults={
                    'slug': subcat_data['slug'],
                    'description': subcat_data['description'],
                    'is_active': True
                }
            )
            category_objects[subcat_name] = subcategory
            if created:
                self.stdout.write(f'Created subcategory: {subcategory.name}')

        # Import products
        imported_count = 0
        skipped_count = 0
        
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for i, row in enumerate(reader):
                if preview_mode and i >= 10:
                    break
                    
                try:
                    with transaction.atomic():
                        # Get or create platform
                        platform_name = self.clean_platform_name(row['platform'])
                        platform, created = Platform.objects.get_or_create(
                            name=platform_name.lower().replace('.', ''),
                            defaults={
                                'display_name': platform_name,
                                'base_url': f"https://{row['platform']}",
                                'platform_type': 'ecommerce',
                                'is_active': True
                            }
                        )
                        
                        # Get or create brand (use platform as default brand)
                        brand, created = Brand.objects.get_or_create(
                            name=platform.display_name,
                            defaults={
                                'display_name': platform.display_name,
                                'slug': platform.display_name.lower().replace(' ', '-')
                            }
                        )
                        
                        # Get or create seller (use platform as default seller)
                        seller, created = Seller.objects.get_or_create(
                            platform=platform,
                            username=platform.display_name.lower().replace(' ', '_'),
                            defaults={
                                'display_name': platform.display_name
                            }
                        )
                        
                        # Get category
                        subcategory_name = row.get('subcategory', row.get('category', 'Educational Toys'))
                        category = category_objects.get(subcategory_name, category_objects['Educational Toys'])
                        
                        # Generate unique slug
                        from django.utils.text import slugify
                        base_slug = slugify(row['title'][:50])
                        slug = base_slug
                        counter = 1
                        while CoreProduct.objects.filter(slug=slug).exists():
                            slug = f"{base_slug}-{counter}"
                            counter += 1
                        
                        # Create CoreProduct
                        core_product = CoreProduct.objects.create(
                            name=row['title'][:200],  # Limit to 200 chars
                            slug=slug,
                            description=f"Toys & Games product from {platform.display_name}",
                            category=category,
                            brand=brand,
                            seller=seller,
                            price=self.parse_price(row.get('price')),
                            is_active=True
                        )
                        
                        # Create EcommerceProduct
                        ecommerce_product = EcommerceProduct.objects.create(
                            product=core_product,
                            platform=platform,
                            platform_url=row.get('product_url', ''),
                            in_stock=True
                        )
                        
                        imported_count += 1
                        
                        if preview_mode:
                            self.stdout.write(f'{i+1}. {row["title"][:50]}... - Rs. {row.get("price", "N/A")}')
                        
                except Exception as e:
                    skipped_count += 1
                    self.stdout.write(self.style.WARNING(f'Error importing product {i+1}: {str(e)}'))
                    continue

        self.stdout.write(
            self.style.SUCCESS(
                f'Import complete! Imported: {imported_count}, Skipped: {skipped_count}'
            )
        )

    def clean_platform_name(self, platform_url):
        """Extract clean platform name from URL"""
        if not platform_url:
            return "Unknown Platform"
        
        # Parse URL to get domain
        parsed = urlparse(platform_url if platform_url.startswith('http') else f'https://{platform_url}')
        domain = parsed.netloc or parsed.path
        
        # Remove www. and common suffixes
        domain = re.sub(r'^www\.', '', domain)
        domain = domain.split('.')[0]
        
        # Capitalize first letter
        return domain.capitalize()

    def parse_price(self, price_str):
        """Parse price string to float"""
        if not price_str or price_str == 'N/A':
            return None
        
        try:
            # Remove currency symbols and commas
            price_clean = re.sub(r'[^\d.]', '', str(price_str))
            return float(price_clean) if price_clean else None
        except:
            return None
