#!/usr/bin/env python3
"""
Check specific product by name and verify image status
"""

from django.core.management.base import BaseCommand
from products.models import CoreProduct
import re


class Command(BaseCommand):
    help = 'Search for a specific product and check its image status'

    def add_arguments(self, parser):
        parser.add_argument('product_name', type=str, help='Product name to search for')

    def handle(self, *args, **options):
        search_term = options['product_name']
        
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS(f'SEARCHING FOR: "{search_term}"'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        # Search for products matching the name
        products = CoreProduct.objects.filter(
            name__icontains=search_term,
            is_active=True
        )

        count = products.count()

        if count == 0:
            self.stdout.write(self.style.WARNING(f'\n❌ No products found matching: "{search_term}"\n'))
            return

        self.stdout.write(f'\n✅ Found {count} product(s) matching your search:\n')

        for i, product in enumerate(products, 1):
            self.stdout.write('=' * 80)
            self.stdout.write(f'\n📦 PRODUCT #{i}')
            self.stdout.write(f'   ID: {product.id}')
            self.stdout.write(f'   Name: {product.name}')
            self.stdout.write(f'   Category: {product.category.name if product.category else "Uncategorized"}')
            self.stdout.write(f'   Seller: {product.seller.display_name if product.seller else "Unknown"}')
            self.stdout.write(f'   Platform: {product.platform_type}')
            
            if product.price:
                self.stdout.write(f'   Price: PKR {product.price:,.2f}')
            
            # Check image URL
            image_url = product.main_image_url
            self.stdout.write(f'\n🖼️  IMAGE STATUS:')
            self.stdout.write(f'   URL: {image_url or "NULL"}')
            
            # Validate image
            if not image_url:
                self.stdout.write(self.style.ERROR('   ❌ STATUS: NO IMAGE (NULL)'))
            elif image_url in ['', 'null', 'undefined', 'N/A']:
                self.stdout.write(self.style.ERROR('   ❌ STATUS: NO IMAGE (EMPTY)'))
            elif 'placeholder' in image_url.lower():
                self.stdout.write(self.style.ERROR('   ❌ STATUS: PLACEHOLDER IMAGE'))
            elif image_url.startswith('https://:0') or image_url.startswith('http://:0'):
                self.stdout.write(self.style.ERROR('   ❌ STATUS: INVALID URL FORMAT'))
            elif self._is_valid_image_url(image_url):
                self.stdout.write(self.style.SUCCESS('   ✅ STATUS: VALID IMAGE URL'))
                
                # Check format
                if re.search(r'\.(jpg|jpeg|png|gif|webp)(\?|$)', image_url, re.IGNORECASE):
                    format_match = re.search(r'\.(jpg|jpeg|png|gif|webp)', image_url, re.IGNORECASE)
                    format_type = format_match.group(1).upper() if format_match else 'Unknown'
                    self.stdout.write(f'   📸 FORMAT: {format_type}')
                elif '.heic' in image_url.lower():
                    self.stdout.write(f'   📸 FORMAT: HEIC (Apple format)')
                elif '.avif' in image_url.lower():
                    self.stdout.write(f'   📸 FORMAT: AVIF (Modern format)')
                elif any(cdn in image_url.lower() for cdn in ['cdninstagram.com', 'cdn.shopify.com', 'cloudfront.net']):
                    self.stdout.write(f'   📸 FORMAT: CDN-hosted (no extension)')
                else:
                    self.stdout.write(f'   📸 FORMAT: Standard web format')
            else:
                self.stdout.write(self.style.WARNING('   ⚠️  STATUS: NON-STANDARD FORMAT'))
            
            # Get ecommerce data if available
            if hasattr(product, 'ecommerce_data') and product.ecommerce_data:
                ecom = product.ecommerce_data
                self.stdout.write(f'\n🔗 PRODUCT LINK:')
                self.stdout.write(f'   {ecom.platform_url}')
            
            self.stdout.write('')

        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS(f'\n✅ Search complete. Found {count} product(s).\n'))

    def _is_valid_image_url(self, url):
        """Check if URL is a valid image"""
        if not url:
            return False
        
        # Check for standard image extensions
        if re.search(r'\.(jpg|jpeg|png|gif|webp|bmp|tiff)(\?|$)', url, re.IGNORECASE):
            return True
        
        # Known image CDNs
        image_cdns = [
            'cdninstagram.com',
            'cdn.shopify.com',
            'cloudfront.net',
            'imgur.com',
            'i.imgur.com',
        ]
        
        url_lower = url.lower()
        if any(cdn in url_lower for cdn in image_cdns):
            return True
        
        return False

