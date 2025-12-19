#!/usr/bin/env python3
"""
Verify if an image URL actually returns a valid image by testing HTTP request
"""

from django.core.management.base import BaseCommand
from products.models import CoreProduct
import requests
from PIL import Image
from io import BytesIO


class Command(BaseCommand):
    help = 'Verify if a specific product has a working image URL by testing HTTP request'

    def add_arguments(self, parser):
        parser.add_argument('product_name', type=str, help='Product name to search for')

    def handle(self, *args, **options):
        search_term = options['product_name']
        
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS(f'VERIFYING IMAGE URL FOR: "{search_term}"'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        # Search for products
        products = CoreProduct.objects.filter(
            name__icontains=search_term,
            is_active=True
        )

        count = products.count()

        if count == 0:
            self.stdout.write(self.style.WARNING(f'\n❌ No products found matching: "{search_term}"\n'))
            return

        self.stdout.write(f'\n✅ Found {count} product(s). Testing image URL(s)...\n')

        for i, product in enumerate(products, 1):
            self.stdout.write('=' * 80)
            self.stdout.write(f'\n📦 PRODUCT #{i}: {product.name}')
            self.stdout.write(f'   ID: {product.id}')
            
            image_url = product.main_image_url
            
            if not image_url or image_url in ['', 'null', 'undefined', 'N/A']:
                self.stdout.write(self.style.ERROR('\n   ❌ NO IMAGE URL - Cannot test\n'))
                continue
            
            self.stdout.write(f'\n🔗 Testing URL: {image_url}')
            
            # Test the URL
            try:
                self.stdout.write('   🔄 Sending HTTP request...')
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                response = requests.get(image_url, headers=headers, timeout=10, allow_redirects=True)
                
                self.stdout.write(f'   📡 HTTP Status Code: {response.status_code}')
                
                if response.status_code == 200:
                    self.stdout.write(self.style.SUCCESS('   ✅ HTTP 200 OK - URL is accessible'))
                    
                    # Check content type
                    content_type = response.headers.get('Content-Type', '')
                    self.stdout.write(f'   📄 Content-Type: {content_type}')
                    
                    if 'image' in content_type.lower():
                        self.stdout.write(self.style.SUCCESS('   ✅ Content-Type confirms this is an image'))
                        
                        # Try to load the image
                        try:
                            img = Image.open(BytesIO(response.content))
                            width, height = img.size
                            format_type = img.format
                            mode = img.mode
                            
                            self.stdout.write(self.style.SUCCESS(f'   ✅ Image successfully loaded and verified!'))
                            self.stdout.write(f'   📸 Format: {format_type}')
                            self.stdout.write(f'   📐 Dimensions: {width} x {height} pixels')
                            self.stdout.write(f'   🎨 Color Mode: {mode}')
                            self.stdout.write(f'   💾 File Size: {len(response.content):,} bytes ({len(response.content)/1024:.2f} KB)')
                            
                            self.stdout.write(self.style.SUCCESS('\n   🎉 VERDICT: FULLY VALID AND WORKING IMAGE! ✅'))
                            
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'   ❌ Failed to parse image: {str(e)}'))
                            self.stdout.write(self.style.WARNING('   ⚠️  VERDICT: URL works but content is not a valid image'))
                    else:
                        self.stdout.write(self.style.WARNING(f'   ⚠️  Content-Type is not an image type'))
                        self.stdout.write(self.style.WARNING('   ⚠️  VERDICT: URL works but may not be an image'))
                        
                elif response.status_code == 404:
                    self.stdout.write(self.style.ERROR('   ❌ HTTP 404 - Image not found'))
                    self.stdout.write(self.style.ERROR('   ❌ VERDICT: BROKEN URL - Image does not exist'))
                    
                elif response.status_code == 403:
                    self.stdout.write(self.style.WARNING('   ⚠️  HTTP 403 - Access forbidden'))
                    self.stdout.write(self.style.WARNING('   ⚠️  VERDICT: URL blocked (may need authentication or cookies)'))
                    
                else:
                    self.stdout.write(self.style.WARNING(f'   ⚠️  Unexpected HTTP status: {response.status_code}'))
                    self.stdout.write(self.style.WARNING('   ⚠️  VERDICT: URL may have issues'))
                    
            except requests.exceptions.Timeout:
                self.stdout.write(self.style.ERROR('   ❌ Request timed out after 10 seconds'))
                self.stdout.write(self.style.ERROR('   ❌ VERDICT: URL not responding'))
                
            except requests.exceptions.ConnectionError:
                self.stdout.write(self.style.ERROR('   ❌ Connection error - Cannot reach server'))
                self.stdout.write(self.style.ERROR('   ❌ VERDICT: Server not reachable'))
                
            except requests.exceptions.SSLError:
                self.stdout.write(self.style.ERROR('   ❌ SSL/TLS error'))
                self.stdout.write(self.style.ERROR('   ❌ VERDICT: SSL certificate issue'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ❌ Error: {str(e)}'))
                self.stdout.write(self.style.ERROR('   ❌ VERDICT: Failed to verify URL'))
            
            self.stdout.write('')

        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS('\n✅ Verification complete.\n'))

