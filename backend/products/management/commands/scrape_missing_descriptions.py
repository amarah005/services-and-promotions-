#!/usr/bin/env python
"""
Scrape missing descriptions from original product pages
Fetches real descriptions from ecommerce URLs
"""
import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from django.core.management.base import BaseCommand
from products.models import CoreProduct
from django.db.models import Q

class Command(BaseCommand):
    help = 'Scrapes missing descriptions from original product URLs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Do not save changes to the database.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Limit the number of products to process.',
        )
        parser.add_argument(
            '--platform',
            type=str,
            help='Target specific platform (e.g., sehgalmotors, vroom)',
        )

    def fetch_description(self, url, platform_name=''):
        """Fetch description from product page based on platform"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Platform-specific selectors
            description = None
            
            # Shopify stores (Vroom, SehgalMotors, etc.)
            if 'shopify' in url or '.pk' in url or 'vroom' in platform_name.lower() or 'sehgal' in platform_name.lower():
                selectors = [
                    '.product-single__description',
                    '.product__description',
                    '.product-description',
                    '[itemprop="description"]',
                    '.rte',
                    '.product-single__description-full',
                ]
                
                for selector in selectors:
                    elem = soup.select_one(selector)
                    if elem:
                        # Get HTML content to preserve formatting
                        description = str(elem)
                        # Clean up some common issues
                        description = description.replace('<!--', '').replace('-->', '')
                        break
            
            # WooCommerce stores (Plants.com.pk, etc.)
            elif 'woocommerce' in response.text.lower() or 'wp-content' in response.text.lower():
                selectors = [
                    '.woocommerce-product-details__short-description',
                    '[itemprop="description"]',
                    '.product-short-description',
                    '#tab-description',
                    '.woocommerce-Tabs-panel--description',
                ]
                
                for selector in selectors:
                    elem = soup.select_one(selector)
                    if elem:
                        description = str(elem)
                        break
            
            # Generic fallback
            if not description:
                # Try meta description
                meta_desc = soup.find('meta', {'name': 'description'})
                if meta_desc and meta_desc.get('content'):
                    description = f'<p>{meta_desc["content"]}</p>'
                
                # Try og:description
                if not description:
                    og_desc = soup.find('meta', property='og:description')
                    if og_desc and og_desc.get('content'):
                        description = f'<p>{og_desc["content"]}</p>'
            
            return description
            
        except Exception as e:
            return None

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        platform_filter = options.get('platform')
        
        self.stdout.write('\n📝 SCRAPING MISSING DESCRIPTIONS')
        self.stdout.write('='*60)
        
        # Build query
        query = Q(description__isnull=True) | Q(description='')
        
        # Only process products with ecommerce data (have URLs to scrape)
        query &= Q(ecommerce_data__isnull=False)
        
        if platform_filter:
            query &= Q(seller__platform__name__icontains=platform_filter)
            self.stdout.write(f'🎯 Platform: {platform_filter}')
        
        products = CoreProduct.objects.filter(query).select_related(
            'ecommerce_data', 'seller__platform', 'brand', 'category'
        )[:limit]
        
        total = products.count()
        
        self.stdout.write(f'📊 Products to process: {total:,}')
        
        if total == 0:
            self.stdout.write('✅ No products need descriptions!')
            return
        
        if dry_run:
            self.stdout.write('\n🔍 DRY RUN - No changes will be made\n')
        
        scraped = 0
        failed = 0
        
        for i, product in enumerate(products, 1):
            self.stdout.write(f'\n[{i}/{total}] {product.name[:55]}...')
            self.stdout.write(f'  Platform: {product.seller.platform.display_name}')
            
            url = product.ecommerce_data.platform_url
            self.stdout.write(f'  URL: {url[:70]}...')
            
            description = self.fetch_description(
                url, 
                product.seller.platform.name
            )
            
            if description and len(description.strip()) > 20:
                self.stdout.write(f'  ✅ Found: {len(description)} characters')
                
                if not dry_run:
                    product.description = description
                    product.save()
                    self.stdout.write(f'  💾 Saved!')
                
                scraped += 1
            else:
                self.stdout.write(f'  ❌ No description found')
                failed += 1
            
            # Be respectful to servers
            time.sleep(0.5)
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(f'📊 SUMMARY:')
        self.stdout.write(f'   Descriptions scraped: {scraped}')
        self.stdout.write(f'   Failed: {failed}')
        self.stdout.write(f'   Success rate: {(scraped/total*100) if total > 0 else 0:.1f}%')
        
        if dry_run:
            self.stdout.write('\n💡 Run without --dry-run to save descriptions')
        else:
            self.stdout.write('\n✅ DESCRIPTION SCRAPING COMPLETE!')

