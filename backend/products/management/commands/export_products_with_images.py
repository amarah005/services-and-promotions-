#!/usr/bin/env python3
"""
Export all products to CSV with image URLs for easy checking
"""

import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from products.models import CoreProduct
import os


class Command(BaseCommand):
    help = 'Export all products with image URLs to CSV for easy checking'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='./backups/products_export_{timestamp}.csv',
            help='Output CSV file path'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limit number of products (0 for all)'
        )

    def handle(self, *args, **options):
        output_path = options['output']
        limit = options['limit']

        # Replace {timestamp} with actual timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = output_path.replace('{timestamp}', timestamp)

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('EXPORTING PRODUCTS TO CSV'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        # Get products
        queryset = CoreProduct.objects.filter(
            is_active=True
        ).select_related('seller', 'category', 'brand')

        if limit > 0:
            queryset = queryset[:limit]

        total_count = queryset.count()

        self.stdout.write(f'\n📊 Total products to export: {total_count:,}')
        self.stdout.write(f'📁 Output file: {output_path}')

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Export to CSV
        self.stdout.write('\n📝 Writing to CSV...')

        with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = [
                'ID',
                'Name',
                'Category',
                'Seller',
                'Platform',
                'Price',
                'Image_URL',
                'Image_Status',
                'Product_URL',
                'Created_At',
                'Last_Scraped',
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for i, product in enumerate(queryset, 1):
                # Progress indicator
                if i % 100 == 0:
                    self.stdout.write(f'   Progress: {i:,}/{total_count:,} ({i/total_count*100:.1f}%)', ending='\r')
                    self.stdout.flush()

                # Determine image status
                image_url = product.main_image_url or ''
                
                if not image_url or image_url in ['', 'null', 'undefined', 'N/A']:
                    image_status = 'MISSING'
                elif 'placeholder' in image_url.lower():
                    image_status = 'PLACEHOLDER'
                elif image_url.startswith('https://:0') or image_url.startswith('http://:0'):
                    image_status = 'INVALID_FORMAT'
                elif '.heic' in image_url.lower():
                    image_status = 'HEIC'
                elif '.avif' in image_url.lower():
                    image_status = 'AVIF'
                elif any(ext in image_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    image_status = 'OK'
                elif any(cdn in image_url.lower() for cdn in ['cdninstagram.com', 'cdn.shopify.com', 'cloudfront.net']):
                    image_status = 'OK_CDN'
                else:
                    image_status = 'UNKNOWN'

                # Get product URL
                product_url = ''
                if hasattr(product, 'ecommerce_data') and product.ecommerce_data:
                    product_url = product.ecommerce_data.platform_url
                elif hasattr(product, 'instagram_data') and product.instagram_data:
                    product_url = product.instagram_data.post_url

                writer.writerow({
                    'ID': product.id,
                    'Name': product.name[:100] if product.name else '',
                    'Category': product.category.name if product.category else '',
                    'Seller': product.seller.display_name if product.seller else '',
                    'Platform': product.platform_type,
                    'Price': f'{product.price:.2f}' if product.price else '',
                    'Image_URL': image_url[:500],  # Truncate very long URLs
                    'Image_Status': image_status,
                    'Product_URL': product_url[:500],
                    'Created_At': product.created_at.strftime('%Y-%m-%d %H:%M:%S') if product.created_at else '',
                    'Last_Scraped': product.last_scraped.strftime('%Y-%m-%d %H:%M:%S') if product.last_scraped else '',
                })

        # Clear progress line
        self.stdout.write(' ' * 80)

        # Statistics
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('✅ EXPORT COMPLETE'))
        self.stdout.write('=' * 80)

        # Count by image status
        self.stdout.write('\n📊 Image Status Summary:')
        
        status_counts = {}
        for product in queryset:
            image_url = product.main_image_url or ''
            
            if not image_url or image_url in ['', 'null', 'undefined', 'N/A']:
                status = 'MISSING'
            elif 'placeholder' in image_url.lower():
                status = 'PLACEHOLDER'
            elif image_url.startswith('https://:0') or image_url.startswith('http://:0'):
                status = 'INVALID_FORMAT'
            elif '.heic' in image_url.lower():
                status = 'HEIC'
            elif '.avif' in image_url.lower():
                status = 'AVIF'
            elif any(ext in image_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                status = 'OK'
            elif any(cdn in image_url.lower() for cdn in ['cdninstagram.com', 'cdn.shopify.com', 'cloudfront.net']):
                status = 'OK_CDN'
            else:
                status = 'UNKNOWN'
            
            status_counts[status] = status_counts.get(status, 0) + 1

        for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
            percentage = (count / total_count * 100) if total_count > 0 else 0
            self.stdout.write(f'   {status:20} : {count:6,} ({percentage:5.1f}%)')

        self.stdout.write(f'\n✅ Total products exported: {total_count:,}')
        self.stdout.write(f'📁 File saved to: {output_path}')
        self.stdout.write(f'💾 File size: {os.path.getsize(output_path):,} bytes ({os.path.getsize(output_path)/1024:.2f} KB)')
        
        self.stdout.write('\n💡 Tip: Open this CSV in Excel/Google Sheets to:')
        self.stdout.write('   • Filter by Image_Status to find issues')
        self.stdout.write('   • Sort by Seller to group products')
        self.stdout.write('   • Click Image_URL to test if images work')
        self.stdout.write('   • Use Product_URL to visit source page\n')

