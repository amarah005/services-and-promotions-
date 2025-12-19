#!/usr/bin/env python3
"""
Safely check products for broken image URLs (404 errors)
Tests actual HTTP requests to verify images exist
"""

from django.core.management.base import BaseCommand
from products.models import CoreProduct
import requests
import time
from collections import defaultdict


class Command(BaseCommand):
    help = 'Find products with broken image URLs by testing HTTP requests (safe, read-only)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Number of products to test (default: 100, use 0 for all)'
        )
        parser.add_argument(
            '--platform',
            type=str,
            default='',
            help='Test only specific platform (e.g., "SehgalMotors")'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=0.5,
            help='Delay between requests in seconds (default: 0.5)'
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=10,
            help='Request timeout in seconds (default: 10)'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        platform = options['platform']
        delay = options['delay']
        timeout = options['timeout']

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('CHECKING FOR BROKEN IMAGE URLs'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        # Build query
        queryset = CoreProduct.objects.filter(
            is_active=True
        ).exclude(
            main_image_url__isnull=True
        ).exclude(
            main_image_url=''
        ).select_related('seller', 'category')

        if platform:
            queryset = queryset.filter(seller__display_name__icontains=platform)

        total_products = queryset.count()
        
        if limit > 0:
            products_to_test = queryset[:limit]
            test_count = min(limit, total_products)
        else:
            products_to_test = queryset
            test_count = total_products

        self.stdout.write(f'\n📊 Total products in database: {total_products:,}')
        self.stdout.write(f'🔍 Testing {test_count:,} products...')
        self.stdout.write(f'⏱️  Delay between requests: {delay}s')
        self.stdout.write(f'⏰ Timeout per request: {timeout}s')
        self.stdout.write(f'⏳ Estimated time: ~{(test_count * delay / 60):.1f} minutes\n')

        # Statistics tracking
        stats = {
            'tested': 0,
            'valid': 0,
            'broken_404': 0,
            'forbidden_403': 0,
            'timeout': 0,
            'connection_error': 0,
            'ssl_error': 0,
            'other_error': 0,
        }

        broken_products = []
        problematic_products = []

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        self.stdout.write('🔄 Testing images...\n')

        for i, product in enumerate(products_to_test, 1):
            stats['tested'] += 1
            
            # Progress indicator
            if i % 10 == 0:
                self.stdout.write(f'   Progress: {i}/{test_count} ({(i/test_count*100):.1f}%)', ending='\r')
                self.stdout.flush()

            image_url = product.main_image_url

            try:
                response = requests.head(
                    image_url, 
                    headers=headers, 
                    timeout=timeout, 
                    allow_redirects=True
                )
                
                if response.status_code == 200:
                    stats['valid'] += 1
                elif response.status_code == 404:
                    stats['broken_404'] += 1
                    broken_products.append({
                        'id': product.id,
                        'name': product.name,
                        'url': image_url,
                        'seller': product.seller.display_name if product.seller else 'Unknown',
                        'category': product.category.name if product.category else 'Uncategorized',
                        'error': 'HTTP 404 - Not Found'
                    })
                elif response.status_code == 403:
                    stats['forbidden_403'] += 1
                    problematic_products.append({
                        'id': product.id,
                        'name': product.name,
                        'url': image_url,
                        'seller': product.seller.display_name if product.seller else 'Unknown',
                        'error': 'HTTP 403 - Forbidden'
                    })
                else:
                    stats['other_error'] += 1
                    problematic_products.append({
                        'id': product.id,
                        'name': product.name,
                        'url': image_url,
                        'seller': product.seller.display_name if product.seller else 'Unknown',
                        'error': f'HTTP {response.status_code}'
                    })

            except requests.exceptions.Timeout:
                stats['timeout'] += 1
                problematic_products.append({
                    'id': product.id,
                    'name': product.name,
                    'url': image_url,
                    'seller': product.seller.display_name if product.seller else 'Unknown',
                    'error': 'Timeout'
                })

            except requests.exceptions.ConnectionError:
                stats['connection_error'] += 1
                problematic_products.append({
                    'id': product.id,
                    'name': product.name,
                    'url': image_url,
                    'seller': product.seller.display_name if product.seller else 'Unknown',
                    'error': 'Connection Error'
                })

            except requests.exceptions.SSLError:
                stats['ssl_error'] += 1
                problematic_products.append({
                    'id': product.id,
                    'name': product.name,
                    'url': image_url,
                    'seller': product.seller.display_name if product.seller else 'Unknown',
                    'error': 'SSL Error'
                })

            except Exception as e:
                stats['other_error'] += 1
                problematic_products.append({
                    'id': product.id,
                    'name': product.name,
                    'url': image_url,
                    'seller': product.seller.display_name if product.seller else 'Unknown',
                    'error': str(e)[:50]
                })

            # Rate limiting
            time.sleep(delay)

        # Clear progress line
        self.stdout.write(' ' * 80)

        # Display results
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('📊 TEST RESULTS'))
        self.stdout.write('=' * 80)

        self.stdout.write(f'\n✅ Products tested: {stats["tested"]:,}')
        self.stdout.write(f'✅ Valid images (HTTP 200): {stats["valid"]:,} ({stats["valid"]/stats["tested"]*100:.1f}%)')
        self.stdout.write(f'❌ Broken images (HTTP 404): {stats["broken_404"]:,} ({stats["broken_404"]/stats["tested"]*100:.1f}%)')
        
        if stats['forbidden_403'] > 0:
            self.stdout.write(f'⚠️  Forbidden (HTTP 403): {stats["forbidden_403"]:,}')
        if stats['timeout'] > 0:
            self.stdout.write(f'⚠️  Timeouts: {stats["timeout"]:,}')
        if stats['connection_error'] > 0:
            self.stdout.write(f'⚠️  Connection errors: {stats["connection_error"]:,}')
        if stats['ssl_error'] > 0:
            self.stdout.write(f'⚠️  SSL errors: {stats["ssl_error"]:,}')
        if stats['other_error'] > 0:
            self.stdout.write(f'⚠️  Other errors: {stats["other_error"]:,}')

        # Show broken products (404s)
        if broken_products:
            self.stdout.write('\n' + '=' * 80)
            self.stdout.write(self.style.ERROR(f'❌ BROKEN IMAGES (404) - {len(broken_products)} products'))
            self.stdout.write('=' * 80)
            
            # Group by seller
            by_seller = defaultdict(list)
            for p in broken_products:
                by_seller[p['seller']].append(p)
            
            for seller, products in sorted(by_seller.items(), key=lambda x: -len(x[1])):
                self.stdout.write(f'\n🏪 {seller}: {len(products)} broken image(s)')
                for p in products[:5]:  # Show first 5 per seller
                    self.stdout.write(f'   • ID {p["id"]}: {p["name"][:60]}')
                if len(products) > 5:
                    self.stdout.write(f'   ... and {len(products) - 5} more')

        # Show problematic products (other issues)
        if problematic_products:
            self.stdout.write('\n' + '=' * 80)
            self.stdout.write(self.style.WARNING(f'⚠️  PROBLEMATIC IMAGES - {len(problematic_products)} products'))
            self.stdout.write('=' * 80)
            
            for p in problematic_products[:10]:  # Show first 10
                self.stdout.write(f'   • ID {p["id"]}: {p["error"]} - {p["name"][:50]}')
            if len(problematic_products) > 10:
                self.stdout.write(f'   ... and {len(problematic_products) - 10} more')

        # Summary
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('✅ CHECK COMPLETE'))
        self.stdout.write('=' * 80)
        
        total_issues = stats['broken_404'] + stats['forbidden_403'] + stats['timeout'] + stats['connection_error'] + stats['ssl_error'] + stats['other_error']
        
        if total_issues > 0:
            self.stdout.write(f'\n⚠️  {total_issues} product(s) have image issues out of {stats["tested"]} tested')
            self.stdout.write(f'📊 Success rate: {stats["valid"]/stats["tested"]*100:.1f}%')
            
            if stats['broken_404'] > 0:
                self.stdout.write(f'\n💡 To remove {stats["broken_404"]} products with 404 errors, create a deletion command')
        else:
            self.stdout.write('\n🎉 All tested images are working perfectly!')
        
        self.stdout.write('')

