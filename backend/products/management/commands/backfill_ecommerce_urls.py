#!/usr/bin/env python3
"""
Backfill Ecommerce URLs for CoreProducts missing ecommerce_data

Strategy:
- For each CoreProduct (platform_type='ecommerce') with no ecommerce_data:
  - Determine seller.platform.base_url (site to search)
  - Use site search endpoint if available (friendshome: /search?q=)
  - Parse results, collect product detail links containing '/products/'
  - Fuzzy-match product titles to CoreProduct.name
  - Create EcommerceProduct with resolved platform_url (dry-run supported)

Safety:
- Configurable limit, timeout, retries, delay
- Dry-run mode (default false)
- Validations on URLs and lengths
"""

import re
import time
import logging
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db import transaction

from products.models import CoreProduct, EcommerceProduct, Platform

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Backfill ecommerce platform_url for products missing ecommerce_data"

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=20, help='Max products to process (default 20)')
        parser.add_argument('--delay', type=float, default=1.5, help='Delay between requests (s)')
        parser.add_argument('--timeout', type=int, default=10, help='HTTP timeout (s)')
        parser.add_argument('--max-retries', type=int, default=2, help='Max retries per request')
        parser.add_argument('--platform', type=str, default='', help='Filter by seller.platform.display_name contains')
        parser.add_argument('--dry-run', action='store_true', help='Do not write to DB')

    def handle(self, *args, **options):
        limit = max(1, min(options['limit'], 200))
        delay = max(0.5, options['delay'])
        timeout = max(5, options['timeout'])
        max_retries = max(0, min(options['max_retries'], 3))
        platform_filter = options['platform']
        dry_run = options['dry_run']

        qs = CoreProduct.objects.filter(platform_type='ecommerce', ecommerce_data__isnull=True, is_active=True)
        if platform_filter:
            qs = qs.filter(seller__platform__display_name__icontains=platform_filter)

        total = qs.count()
        products = qs.select_related('seller__platform')[:limit]

        self.stdout.write(self.style.SUCCESS(f"Backfilling URLs (total candidates: {total}, processing: {len(products)})"))
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - no DB writes'))

        created = 0
        skipped = 0
        failed = 0

        for idx, product in enumerate(products, start=1):
            self.stdout.write(f"[{idx}/{len(products)}] {product.name[:70]}")
            platform = getattr(product.seller, 'platform', None)
            if not platform or not platform.base_url:
                self.stdout.write("  ⚠️  Missing seller platform/base_url; skipping")
                skipped += 1
                continue

            search_url = self.build_site_search_url(platform.base_url, product.name)
            if not search_url:
                self.stdout.write("  ⚠️  No search URL pattern for platform; skipping")
                skipped += 1
                continue

            try:
                resolved = self.search_and_resolve_product_url(search_url, platform.base_url, product.name, timeout, max_retries)
            except Exception as e:
                logger.warning(f"Search failed for {product.id}: {e}")
                failed += 1
                continue

            if not resolved:
                self.stdout.write("  ❌ No matching product URL found")
                failed += 1
                continue

            if not self.is_safe_url(resolved):
                self.stdout.write("  🚫 Resolved URL deemed unsafe; skipping")
                failed += 1
                continue

            self.stdout.write(self.style.SUCCESS(f"  🔗 Resolved: {resolved}"))

            if dry_run:
                created += 1
            else:
                try:
                    with transaction.atomic():
                        # Derive a stable platform_product_id from URL path (Shopify handle)
                        platform_product_id = self.extract_product_id_from_url(resolved)
                        ep = EcommerceProduct.objects.create(
                            product=product,
                            platform=platform,
                            platform_product_id=platform_product_id,
                            platform_url=resolved,
                            scraping_source='backfill-search'
                        )
                        created += 1
                        self.stdout.write(f"  💾 ecommerce_data created (id: {platform_product_id})")
                except Exception as e:
                    self.stdout.write(f"  ❌ Create failed: {e}")
                    failed += 1
                    continue

            if delay > 0:
                time.sleep(delay)

        self.stdout.write(self.style.SUCCESS("\nBackfill complete"))
        self.stdout.write(f"  ✅ Created: {created}")
        self.stdout.write(f"  ⚠️  Skipped: {skipped}")
        self.stdout.write(f"  ❌ Failed: {failed}")

    # --- Helpers ---
    def build_site_search_url(self, base_url: str, query: str) -> str:
        """Return a site-specific search URL pattern when known."""
        try:
            base = base_url.rstrip('/')
            # Friendshome (Shopify-like)
            if 'friendshome.pk' in base:
                return f"{base}/search?q={requests.utils.quote(query)}"
            # Add more site patterns here as needed
        except Exception:
            return ''
        return ''

    def search_and_resolve_product_url(self, search_url: str, base_url: str, product_name: str, timeout: int, max_retries: int) -> str:
        """Fetch search page, collect '/products/' links, return best match."""
        content = self.fetch_with_retries(search_url, timeout, max_retries)
        if not content:
            return ''
        soup = BeautifulSoup(content, 'html.parser')
        candidates = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/products/' not in href:
                continue
            abs_url = self.to_absolute_url(href, base_url)
            title_text = (a.get_text() or '').strip()
            if not title_text:
                title_el = a.find(['h1','h2','h3','h4']) or a.find_next(['h1','h2','h3','h4'])
                if title_el:
                    title_text = (title_el.get_text() or '').strip()
            score = self.score_title_similarity(product_name, title_text)
            candidates.append((score, abs_url))

        if not candidates:
            return ''
        candidates.sort(reverse=True, key=lambda x: x[0])
        top_score, top_url = candidates[0]
        return top_url if top_score >= 0.3 else ''

    def fetch_with_retries(self, url: str, timeout: int, max_retries: int) -> bytes:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        for attempt in range(max_retries + 1):
            try:
                resp = requests.get(url, headers=headers, timeout=timeout)
                resp.raise_for_status()
                return resp.content
            except requests.RequestException:
                if attempt >= max_retries:
                    return b''
                time.sleep(2 ** attempt)
        return b''

    def score_title_similarity(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        tokenize = lambda s: set(re.findall(r"[a-z0-9]+", s.lower()))
        ta, tb = tokenize(a), tokenize(b)
        if not ta or not tb:
            return 0.0
        inter = len(ta & tb)
        union = len(ta | tb)
        return inter / union if union else 0.0

    def to_absolute_url(self, href: str, base_url: str) -> str:
        if not href:
            return ''
        if href.startswith('http'):
            return href
        if href.startswith('//'):
            return 'https:' + href
        if href.startswith('/'):
            parsed = urlparse(base_url)
            return f"{parsed.scheme}://{parsed.netloc}{href}"
        return urljoin(base_url, href)

    def extract_product_id_from_url(self, url: str) -> str:
        """Extract a stable product handle/id from typical Shopify-like URLs."""
        try:
            parsed = urlparse(url)
            path = parsed.path  # /products/<handle>
            # Remove trailing slashes
            if path.endswith('/'):
                path = path[:-1]
            # Take last segment
            handle = path.split('/')[-1]
            # Normalize handle
            handle = re.sub(r"[^a-z0-9\-_.]", "", handle.lower())
            return handle[:200] if handle else parsed.path[:200]
        except Exception:
            return ''

    def is_safe_url(self, url: str) -> bool:
        try:
            if not url or len(url) > 1200:
                return False
            parsed = urlparse(url)
            if not parsed.scheme.startswith('http') or not parsed.netloc:
                return False
            dangerous = ['javascript:', 'data:', 'file:', 'ftp:']
            return not any(url.lower().startswith(p) for p in dangerous)
        except Exception:
            return False


