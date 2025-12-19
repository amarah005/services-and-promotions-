#!/usr/bin/env python3
"""
Find all products with broken (404) image URLs
"""

from django.core.management.base import BaseCommand
from django.db.models import Q
from products.models import CoreProduct
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


class Command(BaseCommand):
    help = 'Find products with broken (404) image URLs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sample-size',
            type=int,
            default=50,
            help='Number of products to test (default: 50)'
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=5,
            help='Request timeout in seconds (default: 5)'
        )
        parser.add_argument(
            '--workers',
            type=int,
            default=10,
            help='Number of parallel workers (default: 10)'
        )

    def test_image_url(self, product, timeout):
        """Test if an image URL is accessible"""
        try:
            response = requests.head(
                product.main_image_url,
                timeout=timeout,
                allow_redirects=True
            )
            return {
                'product': product,
                'status': response.status_code,
                'working': response.status_code == 200,
                'error': None
            }
        except requests.exceptions.Timeout:
            return {
                'product': product,
                'status': None,
                'working': False,
                'error': 'Timeout'
            }
        except requests.exceptions.ConnectionError:
            return {
                'product': product,
                'status': None,
                'working': False,
                'error': 'Connection Error'
            }
        except Exception as e:
            return {
                'product': product,
                'status': None,
                'working': False,
                'error': str(e)[:50]
            }

    def handle(self, *args, **options):
        sample_size = options['sample_size']
        timeout = options['timeout']
        workers = options['workers']

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('FIND BROKEN IMAGE URLs'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        # Get active products with images
        products = CoreProduct.objects.filter(
            is_active=True,
            main_image_url__isnull=False
        ).exclude(
            Q(main_image_url='') | 
            Q(main_image_url='null') | 
            Q(main_image_url='undefined')
        )

        total = products.count()
        self.stdout.write(f"\n📊 Total active products with images: {total:,}")
        self.stdout.write(f"🔍 Testing sample of {sample_size} products...")
        self.stdout.write(f"⚙️ Using {workers} parallel workers\n")

        # Get sample
        sample = list(products[:sample_size])
        
        # Test URLs in parallel
        broken = []
        working = 0
        errors = []

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(self.test_image_url, p, timeout): p 
                for p in sample
            }
            
            for i, future in enumerate(as_completed(futures), 1):
                result = future.result()
                
                # Progress indicator
                if i % 10 == 0:
                    self.stdout.write(f"  Tested {i}/{len(sample)}...")
                
                if result['working']:
                    working += 1
                elif result['status'] == 404:
                    broken.append(result)
                else:
                    errors.append(result)

        # Results
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('RESULTS'))
        self.stdout.write('=' * 80)
        
        self.stdout.write(f"\n✅ Working images: {working}/{len(sample)}")
        self.stdout.write(f"❌ Broken (404): {len(broken)}/{len(sample)}")
        self.stdout.write(f"⚠️ Errors (timeout/connection): {len(errors)}/{len(sample)}")
        
        # Show broken images
        if broken:
            self.stdout.write('\n' + '-' * 80)
            self.stdout.write(self.style.ERROR(f'❌ BROKEN IMAGES (404):'))
            self.stdout.write('-' * 80)
            
            for result in broken[:10]:  # Show first 10
                p = result['product']
                self.stdout.write(f"\nID: {p.id}")
                self.stdout.write(f"Name: {p.name[:70]}")
                self.stdout.write(f"URL: {p.main_image_url[:80]}...")
                self.stdout.write(f"Platform: {p.platform_type}")
            
            if len(broken) > 10:
                self.stdout.write(f"\n... and {len(broken) - 10} more")
        
        # Estimate total broken
        if len(sample) > 0:
            broken_percentage = (len(broken) / len(sample)) * 100
            estimated_total_broken = int((len(broken) / len(sample)) * total)
            
            self.stdout.write('\n' + '=' * 80)
            self.stdout.write(f"📈 ESTIMATED IMPACT:")
            self.stdout.write(f"   {broken_percentage:.1f}% of images are broken (404)")
            self.stdout.write(f"   ~{estimated_total_broken:,} products affected out of {total:,} total")
            self.stdout.write('=' * 80)
        
        # Recommendations
        if len(broken) > 0:
            self.stdout.write('\n' + self.style.WARNING('💡 RECOMMENDATIONS:'))
            self.stdout.write('   1. Re-scrape affected products to get updated image URLs')
            self.stdout.write('   2. Mark products with broken images as inactive')
            self.stdout.write('   3. Set up periodic image health checks')
            self.stdout.write('   4. Implement fallback/placeholder images in frontend')

