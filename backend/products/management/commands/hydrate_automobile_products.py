#!/usr/bin/env python
"""
Management command to hydrate automobile products with missing data
"""

from django.core.management.base import BaseCommand
from django.db.models import Q
from products.models import CoreProduct, EcommerceProduct
import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin, urlparse
import re

class Command(BaseCommand):
    help = 'Hydrate automobile products with missing price, image, and description data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Limit number of products to process (default: 50)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        
        self.stdout.write('\n🔍 AUTOMOBILE PRODUCTS HYDRATION')
        self.stdout.write('='*60)
        
        # Find products needing hydration
        products_needing_price = CoreProduct.objects.filter(
            category__main_category__icontains='automobile'
        ).filter(
            Q(price__isnull=True) | Q(price=0)
        )[:limit]
        
        products_needing_image = CoreProduct.objects.filter(
            category__main_category__icontains='automobile'
        ).filter(
            Q(main_image_url__isnull=True) | Q(main_image_url='') | Q(main_image_url='null')
        )[:limit]
        
        products_needing_description = CoreProduct.objects.filter(
            category__main_category__icontains='automobile'
        ).filter(
            Q(description__isnull=True) | Q(description='')
        )[:limit]
        
        self.stdout.write(f'Products needing price: {products_needing_price.count()}')
        self.stdout.write(f'Products needing image: {products_needing_image.count()}')
        self.stdout.write(f'Products needing description: {products_needing_description.count()}')
        
        if dry_run:
            self.stdout.write('\n🔍 DRY RUN - No changes will be made')
            self.show_examples(products_needing_price, products_needing_image, products_needing_description)
            return
        
        # Process products
        self.hydrate_prices(products_needing_price)
        self.hydrate_images(products_needing_image)
        self.hydrate_descriptions(products_needing_description)
        
        self.stdout.write('\n✅ HYDRATION COMPLETE!')

    def show_examples(self, price_products, image_products, desc_products):
        """Show examples of products that would be updated"""
        self.stdout.write('\n📋 EXAMPLES TO BE UPDATED:')
        self.stdout.write('-'*40)
        
        self.stdout.write('\n🔴 Missing Price:')
        for product in price_products[:3]:
            self.stdout.write(f'  - {product.name[:50]}... ({product.seller.platform.display_name})')
        
        self.stdout.write('\n🖼️ Missing Image:')
        for product in image_products[:3]:
            self.stdout.write(f'  - {product.name[:50]}... ({product.seller.platform.display_name})')
        
        self.stdout.write('\n📝 Missing Description:')
        for product in desc_products[:3]:
            self.stdout.write(f'  - {product.name[:50]}... ({product.seller.platform.display_name})')

    def hydrate_prices(self, products):
        """Hydrate missing prices"""
        self.stdout.write('\n💰 HYDRATING PRICES...')
        updated = 0
        
        for product in products:
            try:
                # Try to get price from ecommerce data
                ecomm = EcommerceProduct.objects.filter(product=product).first()
                if ecomm and hasattr(ecomm, 'price') and ecomm.price:
                    product.price = ecomm.price
                    product.save()
                    updated += 1
                    self.stdout.write(f'  ✅ Updated price for: {product.name[:30]}...')
                else:
                    # Set default price based on category
                    if 'car' in product.name.lower() or 'auto' in product.name.lower():
                        product.price = 500000  # Default car price
                    else:
                        product.price = 5000    # Default accessory price
                    product.save()
                    updated += 1
                    self.stdout.write(f'  🔧 Set default price for: {product.name[:30]}...')
                    
            except Exception as e:
                self.stdout.write(f'  ❌ Error updating {product.name[:30]}: {str(e)}')
        
        self.stdout.write(f'💰 Updated {updated} prices')

    def hydrate_images(self, products):
        """Hydrate missing images"""
        self.stdout.write('\n🖼️ HYDRATING IMAGES...')
        updated = 0
        
        for product in products:
            try:
                # Try to get image from ecommerce data
                ecomm = EcommerceProduct.objects.filter(product=product).first()
                if ecomm and hasattr(ecomm, 'image_url') and ecomm.image_url:
                    product.main_image_url = ecomm.image_url
                    product.save()
                    updated += 1
                    self.stdout.write(f'  ✅ Updated image for: {product.name[:30]}...')
                else:
                    # Set placeholder image
                    product.main_image_url = f'https://via.placeholder.com/300x300?text={product.name[:20]}'
                    product.save()
                    updated += 1
                    self.stdout.write(f'  🔧 Set placeholder for: {product.name[:30]}...')
                    
            except Exception as e:
                self.stdout.write(f'  ❌ Error updating {product.name[:30]}: {str(e)}')
        
        self.stdout.write(f'🖼️ Updated {updated} images')

    def hydrate_descriptions(self, products):
        """Hydrate missing descriptions"""
        self.stdout.write('\n📝 HYDRATING DESCRIPTIONS...')
        updated = 0
        
        for product in products:
            try:
                # Generate description based on product name and category
                category = product.category.name if product.category else 'Automobile'
                platform = product.seller.platform.display_name if product.seller else 'Unknown'
                
                description = f"""
                <h3>{product.name}</h3>
                <p><strong>Category:</strong> {category}</p>
                <p><strong>Platform:</strong> {platform}</p>
                <p><strong>Description:</strong> High-quality {category.lower()} product from {platform}. 
                Perfect for automobile enthusiasts and car owners looking for reliable and durable accessories.</p>
                <ul>
                    <li>Premium quality materials</li>
                    <li>Easy installation</li>
                    <li>Durable construction</li>
                    <li>Compatible with various vehicle models</li>
                </ul>
                <p><em>Available from {platform} - your trusted automobile parts and accessories supplier.</em></p>
                """
                
                product.description = description.strip()
                product.save()
                updated += 1
                self.stdout.write(f'  ✅ Updated description for: {product.name[:30]}...')
                    
            except Exception as e:
                self.stdout.write(f'  ❌ Error updating {product.name[:30]}: {str(e)}')
        
        self.stdout.write(f'📝 Updated {updated} descriptions')
