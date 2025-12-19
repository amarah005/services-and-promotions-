#!/usr/bin/env python
"""
Generate descriptions for products missing them
Uses product name, category, brand, and platform to create informative descriptions
"""
from django.core.management.base import BaseCommand
from products.models import CoreProduct
from django.db.models import Q

class Command(BaseCommand):
    help = 'Generates descriptions for products that are missing them'

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

    def generate_description(self, product):
        """Generate a description based on product details"""
        
        # Get product details
        name = product.name
        category = product.category.name if product.category else 'product'
        brand = product.brand.display_name if product.brand else ''
        platform = product.seller.platform.display_name if product.seller and product.seller.platform else ''
        price = f"Rs. {product.price:,.0f}" if product.price else ''
        
        # Create templates based on category
        templates = []
        
        # Template 1: Full detailed description
        if brand and price:
            templates.append(
                f"Discover the {name} from {brand}, available on {platform}. "
                f"This premium {category.lower()} is priced at {price}, offering "
                f"exceptional quality and value. Perfect for those seeking reliable "
                f"and authentic {category.lower()} from trusted brands. "
                f"Browse more {category.lower()} options on our platform."
            )
        
        # Template 2: Brand-focused
        elif brand:
            templates.append(
                f"Explore the {name} by {brand}, featured on {platform}. "
                f"This {category.lower()} combines quality craftsmanship with "
                f"innovative design. {brand} is known for delivering exceptional "
                f"products that meet customer expectations. Find more {category.lower()} "
                f"from {brand} and other leading brands on our platform."
            )
        
        # Template 3: Platform-focused
        elif platform:
            templates.append(
                f"The {name} is available on {platform}. "
                f"This {category.lower()} offers great features and functionality "
                f"perfect for your needs. Explore our extensive collection of "
                f"{category.lower()} from {platform} and other trusted platforms. "
                f"Compare prices and find the best deals on quality products."
            )
        
        # Template 4: Category-focused
        else:
            templates.append(
                f"Introducing the {name}, a quality {category.lower()} designed "
                f"to meet your requirements. This product combines functionality "
                f"with reliability, making it an excellent choice for customers "
                f"looking for dependable {category.lower()}. Browse our extensive "
                f"catalog to find more similar products and compare options."
            )
        
        # Add category-specific details
        category_lower = category.lower()
        
        if 'car' in category_lower or 'bike' in category_lower or 'automobile' in category_lower:
            templates[0] += f" Enhance your vehicle with this genuine {category.lower()}."
        elif 'beauty' in category_lower or 'skincare' in category_lower or 'makeup' in category_lower:
            templates[0] += f" Enhance your beauty routine with this premium product."
        elif 'electronics' in category_lower or 'mobile' in category_lower:
            templates[0] += f" Experience cutting-edge technology and reliability."
        elif 'fashion' in category_lower or 'clothing' in category_lower:
            templates[0] += f" Elevate your style with this fashionable piece."
        elif 'home' in category_lower or 'furniture' in category_lower:
            templates[0] += f" Transform your living space with this quality item."
        elif 'gym' in category_lower or 'fitness' in category_lower:
            templates[0] += f" Achieve your fitness goals with this equipment."
        elif 'toy' in category_lower or 'kids' in category_lower:
            templates[0] += f" Bring joy and entertainment to children."
        elif 'book' in category_lower or 'stationery' in category_lower:
            templates[0] += f" Enhance learning and creativity."
        
        return templates[0]

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        
        self.stdout.write('\n📝 GENERATING PRODUCT DESCRIPTIONS')
        self.stdout.write('='*60)
        
        # Find products without descriptions
        products_without_description = CoreProduct.objects.filter(
            Q(description__isnull=True) | Q(description='')
        ).select_related('category', 'brand', 'seller__platform')[:limit]
        
        total = products_without_description.count()
        
        self.stdout.write(f'📊 Products without descriptions: {total:,}')
        
        if total == 0:
            self.stdout.write('✅ All products have descriptions!')
            return
        
        if dry_run:
            self.stdout.write('\n🔍 DRY RUN - Sample descriptions:\n')
            
            for i, product in enumerate(products_without_description[:5], 1):
                description = self.generate_description(product)
                self.stdout.write(f'\n{i}. [{product.id}] {product.name[:60]}')
                self.stdout.write(f'   Category: {product.category.name if product.category else "N/A"}')
                self.stdout.write(f'   Brand: {product.brand.display_name if product.brand else "N/A"}')
                self.stdout.write(f'   Generated Description:')
                self.stdout.write(f'   "{description[:200]}..."')
            
            self.stdout.write('\n' + '='*60)
            self.stdout.write(f'\n💡 Run without --dry-run to apply to all {total:,} products')
            return
        
        # Generate and save descriptions
        self.stdout.write('\n🔧 Generating descriptions...\n')
        
        generated = 0
        
        for i, product in enumerate(products_without_description, 1):
            description = self.generate_description(product)
            product.description = description
            product.save()
            
            generated += 1
            
            if generated % 100 == 0:
                self.stdout.write(f'   Generated {generated}/{total}...')
        
        self.stdout.write(f'\n✅ Generated descriptions for {generated:,} products!')
        self.stdout.write('='*60)

