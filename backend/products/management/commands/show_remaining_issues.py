#!/usr/bin/env python3
"""
Show the exact 19 products that still need attention
"""

from django.core.management.base import BaseCommand
from products.models import CoreProduct
import re


class Command(BaseCommand):
    help = 'Show the exact products with remaining image issues'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('FINDING REMAINING PRODUCTS WITH IMAGE ISSUES'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        # Get all products with URLs
        all_products = CoreProduct.objects.filter(
            is_active=True
        ).exclude(
            main_image_url__isnull=True
        ).exclude(
            main_image_url=''
        )

        non_image_products = []

        for product in all_products:
            url = product.main_image_url
            if url and not self._is_probable_image_url(url):
                non_image_products.append(product)

        self.stdout.write(f'\n📊 Found {len(non_image_products)} products with non-image URLs\n')

        if len(non_image_products) == 0:
            self.stdout.write(self.style.SUCCESS('🎉 All products have valid image URLs!\n'))
            return

        # Show all of them
        self.stdout.write('=' * 80)
        for i, p in enumerate(non_image_products, 1):
            seller_name = p.seller.display_name if p.seller else 'Unknown'
            category_name = p.category.name if p.category else 'Uncategorized'
            
            self.stdout.write(f'\n{i}. ID: {p.id}')
            self.stdout.write(f'   Name: {p.name[:70]}')
            self.stdout.write(f'   Image URL: {p.main_image_url}')
            self.stdout.write(f'   Seller: {seller_name}')
            self.stdout.write(f'   Category: {category_name}')
            self.stdout.write('-' * 80)

    def _is_probable_image_url(self, url):
        """Check if URL likely points to an image"""
        if not url:
            return False
        
        # Check for image extensions
        if re.search(r'\.(jpg|jpeg|png|gif|webp|bmp|tiff)(\?|$)', url, re.IGNORECASE):
            return True
        
        # Known image CDNs that may not have extensions
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

