#!/usr/bin/env python
"""
Extract and assign brands to products
Uses intelligent brand detection from product names
"""
import re
from django.core.management.base import BaseCommand
from products.models import CoreProduct, Brand
from django.db import transaction

class Command(BaseCommand):
    help = 'Extracts and assigns brands to products using intelligent detection'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Do not save changes to the database.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Limit the number of products to process.',
        )

    # Common brand keywords and patterns
    KNOWN_BRANDS = [
        # Car brands
        'Toyota', 'Honda', 'Suzuki', 'Nissan', 'Mazda', 'Mitsubishi', 'Daihatsu',
        'Mercedes', 'BMW', 'Audi', 'Volkswagen', 'Hyundai', 'Kia', 'Ford',
        'Chevrolet', 'Lexus', 'Peugeot', 'Renault', 'Subaru', 'Isuzu',
        
        # Electronics brands
        'Samsung', 'LG', 'Sony', 'Panasonic', 'Haier', 'Dawlance', 'Orient',
        'Kenwood', 'Philips', 'TCL', 'Gree', 'Midea', 'Pel', 'Waves',
        
        # Fashion brands
        'Adidas', 'Nike', 'Puma', 'Reebok', 'Gucci', 'Zara', 'H&M',
        
        # Beauty brands
        'Loreal', "L'Oreal", 'Maybelline', 'MAC', 'Clinique', 'Estee Lauder',
        'Nivea', 'Garnier', 'Olay', 'Pond', 'Dove',
        
        # Toy brands
        'Lego', 'Barbie', 'Hot Wheels', 'Mattel', 'Hasbro', 'Fisher Price',
        'Bruder', 'Bburago', 'Intex',
        
        # Auto parts brands
        'Bosch', 'Denso', 'NGK', 'Mobil', 'Shell', 'Castrol', 'Michelin',
        'Bridgestone', 'Goodyear', 'Yokohama', 'Acebot', 'Flamingo',
        
        # Electronics accessories
        'Anker', 'Baseus', 'Ugreen', 'Belkin', 'Sandisk', 'Kingston',
        
        # Pakistani brands
        'Sana Safinaz', 'Khaadi', 'Gul Ahmed', 'Nishat', 'Alkaram',
        'Outfitters', 'Breakout', 'CrossRoads', 'Ethnic', 'Junaid Jamshed',
        
        # Generic auto brands
        'Maximus', 'JBL', 'Pioneer', 'Kenwood',
    ]

    def extract_brand_from_name(self, product_name, category_name='', platform_name=''):
        """Extract brand from product name using intelligent matching"""
        
        # Clean the name first
        name_clean = product_name.strip()
        name_lower = name_clean.lower()
        
        # Check for known brands (case insensitive, whole word match)
        for brand in self.KNOWN_BRANDS:
            # Use word boundary to avoid partial matches
            pattern = r'\b' + re.escape(brand.lower()) + r'\b'
            if re.search(pattern, name_lower):
                return brand
        
        # Extract from common patterns
        patterns = [
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+',  # Capital word(s) at start
            r'\b([A-Z]{2,})\b',  # All caps words (acronyms)
            r'([A-Z][a-zA-Z]+)(?:\s+[A-Z0-9])',  # Brand before model number
        ]
        
        for pattern in patterns:
            match = re.search(pattern, name_clean)
            if match:
                potential_brand = match.group(1).strip()
                
                # Filter out common words that aren't brands
                exclude_words = [
                    'The', 'New', 'For', 'With', 'And', 'Pack', 'Set', 'Sale',
                    'Deal', 'Best', 'Top', 'Premium', 'Luxury', 'Special',
                    'Limited', 'Edition', 'Collection', 'Series', 'Model',
                    'Used', 'Car', 'Bike', 'Product', 'Piece', 'Pcs'
                ]
                
                if potential_brand not in exclude_words and len(potential_brand) > 2:
                    return potential_brand
        
        # For cars/bikes, try to extract manufacturer at start
        if 'car' in category_name.lower() or 'bike' in category_name.lower() or 'automobile' in category_name.lower():
            # Look for car brands at the beginning
            match = re.search(r'^(Toyota|Honda|Suzuki|Nissan|Mazda|Mitsubishi|Daihatsu|Mercedes|BMW|Audi|Hyundai|Kia|Ford|Chevrolet|Lexus|Proton|Haval|MG|Changan|Isuzu|Volkswagen)', 
                            name_clean, re.IGNORECASE)
            if match:
                return match.group(1).title()
        
        # If no brand detected, use "Generic" or platform name
        return 'Generic'

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        
        self.stdout.write('\n🏷️ BRAND EXTRACTION AND ASSIGNMENT')
        self.stdout.write('='*60)
        
        # Get products without brands
        products_without_brand = CoreProduct.objects.filter(
            brand__isnull=True
        ).select_related('seller__platform', 'category')[:limit]
        
        total = products_without_brand.count()
        self.stdout.write(f'📊 Products to process: {total:,}')
        
        if total == 0:
            self.stdout.write('✅ All products already have brands!')
            return
        
        if dry_run:
            self.stdout.write('\n🔍 DRY RUN - No changes will be made\n')
        
        assigned = 0
        created_brands = 0
        skipped = 0
        
        for i, product in enumerate(products_without_brand, 1):
            brand_name = self.extract_brand_from_name(
                product.name, 
                product.category.name if product.category else ''
            )
            
            if brand_name:
                if dry_run:
                    self.stdout.write(
                        f'[{i}/{total}] {product.name[:50]}... → Brand: {brand_name}'
                    )
                else:
                    # Get or create brand (handle slug conflicts)
                    try:
                        brand, created = Brand.objects.get_or_create(
                            name__iexact=brand_name,
                            defaults={
                                'name': brand_name,
                                'slug': brand_name.lower().replace(' ', '-').replace("'", '')
                            }
                        )
                    except Brand.MultipleObjectsReturned:
                        # If multiple brands with same name (case insensitive), use first
                        brand = Brand.objects.filter(name__iexact=brand_name).first()
                        created = False
                    except Exception:
                        # If slug conflict, try to get existing brand by name
                        brand = Brand.objects.filter(name__iexact=brand_name).first()
                        if not brand:
                            # Create with unique slug
                            import time
                            clean_name = brand_name.lower().replace(' ', '-').replace("'", '')
                            slug = f"{clean_name}-{int(time.time())}"
                            brand = Brand.objects.create(name=brand_name, slug=slug)
                            created = True
                        else:
                            created = False
                    
                    if created:
                        created_brands += 1
                        self.stdout.write(f'  🆕 Created brand: {brand_name}')
                    
                    product.brand = brand
                    product.save()
                    
                    self.stdout.write(
                        f'[{i}/{total}] {product.name[:50]}... → ✅ {brand_name}'
                    )
                
                assigned += 1
            else:
                skipped += 1
                if dry_run and i <= 10:
                    self.stdout.write(
                        f'[{i}/{total}] {product.name[:50]}... → ⚠️ No brand detected'
                    )
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(f'📊 SUMMARY:')
        self.stdout.write(f'   Brands assigned: {assigned}')
        self.stdout.write(f'   New brands created: {created_brands}')
        self.stdout.write(f'   Skipped (no brand detected): {skipped}')
        
        if dry_run:
            self.stdout.write('\n💡 Run without --dry-run to apply changes')
        else:
            self.stdout.write('\n✅ BRAND ASSIGNMENT COMPLETE!')

