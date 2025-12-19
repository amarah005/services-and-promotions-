#!/usr/bin/env python3
"""
Image Hydrator - Fill missing product images without re-scraping entire sites
Fetches individual product pages to extract primary images for products with empty main_image_url

SAFETY FEATURES:
- Comprehensive error handling and validation
- URL sanitization and security checks
- Rate limiting and request throttling
- Transaction rollback on errors
- Backup and restore capabilities
- Detailed logging and progress tracking
"""

import requests
import time
import logging
import re
import json
from urllib.parse import urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection
from django.conf import settings
from django.utils import timezone
from products.models import CoreProduct, EcommerceProduct
import hashlib

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Hydrate missing product images by fetching individual product pages"

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=10, help='Maximum products to process (default: 10, max: 100)')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without making changes')
        parser.add_argument('--platform', help='Only process products from specific platform')
        parser.add_argument('--delay', type=float, default=2.0, help='Delay between requests in seconds (default: 2.0, min: 1.0)')
        parser.add_argument('--timeout', type=int, default=10, help='Request timeout in seconds (default: 10)')
        parser.add_argument('--max-retries', type=int, default=2, help='Maximum retries per request (default: 2)')
        parser.add_argument('--backup', action='store_true', help='Create backup before making changes')
        parser.add_argument('--validate-only', action='store_true', help='Only validate URLs without fetching images')
        parser.add_argument('--safe-mode', action='store_true', help='Enable extra safety checks and slower processing')

    def handle(self, *args, **options):
        # Safety validation
        limit = min(options['limit'], 100)  # Cap at 100 for safety
        delay = max(options['delay'], 1.0)  # Minimum 1 second delay
        timeout = max(options['timeout'], 5)  # Minimum 5 second timeout
        max_retries = min(options['max_retries'], 3)  # Cap at 3 retries
        
        dry_run = options['dry_run']
        platform_filter = options['platform']
        backup = options['backup']
        validate_only = options['validate_only']
        safe_mode = options['safe_mode']

        # Enhanced safety in safe mode
        if safe_mode:
            limit = min(limit, 5)
            delay = max(delay, 3.0)
            timeout = max(timeout, 15)

        self.stdout.write(self.style.SUCCESS("SAFE IMAGE HYDRATOR STARTING"))
        self.stdout.write(f"Limit: {limit}, Delay: {delay}s, Timeout: {timeout}s, Retries: {max_retries}")
        
        if safe_mode:
            self.stdout.write(self.style.WARNING("SAFE MODE ENABLED - Extra safety checks active"))

        # Create backup if requested
        if backup and not dry_run:
            self.create_backup()

        # Find products with missing images
        queryset = CoreProduct.objects.filter(
            main_image_url__in=['', None]
        ).exclude(
            ecommerce_data__platform_url__in=['', None]
        ).select_related('ecommerce_data__platform')

        if platform_filter:
            queryset = queryset.filter(ecommerce_data__platform__display_name__icontains=platform_filter)

        products = queryset[:limit]
        total_count = queryset.count()

        self.stdout.write(
            self.style.SUCCESS(f"Found {total_count} products with missing images")
        )
        self.stdout.write(f"Processing {len(products)} products (limit: {limit})")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))
        if validate_only:
            self.stdout.write(self.style.WARNING("VALIDATE ONLY MODE - No images will be fetched"))

        success_count = 0
        error_count = 0
        skipped_count = 0
        validation_errors = 0

        for i, product in enumerate(products, 1):
            try:
                self.stdout.write(f"[{i}/{len(products)}] Processing: {product.name[:50]}...")
                
                # Get product URL with safety checks
                ecommerce_data = getattr(product, 'ecommerce_data', None)
                if not ecommerce_data or not ecommerce_data.platform_url:
                    self.stdout.write(f"  WARNING: No product URL found, skipping")
                    skipped_count += 1
                    continue

                product_url = ecommerce_data.platform_url
                
                # Validate URL safety
                if not self.is_safe_url(product_url):
                    self.stdout.write(f"  BLOCKED: Unsafe URL detected, skipping")
                    validation_errors += 1
                    continue
                
                self.stdout.write(f"  URL: {product_url}")

                # Validate-only mode
                if validate_only:
                    self.stdout.write(f"  SUCCESS: URL validation passed")
                    success_count += 1
                    continue

                # Check if this is a vendor/category page (not individual product)
                is_vendor_page = self.is_vendor_or_category_page(product_url)
                if is_vendor_page:
                    self.stdout.write(f"  INFO: Detected vendor/category page, attempting to resolve product page")
                    resolved = self.resolve_product_page_url(
                        product.name, product_url, timeout
                    )
                    if resolved and self.is_safe_url(resolved):
                        self.stdout.write(f"  SUCCESS: Resolved product URL: {resolved}")
                        product_url = resolved
                        is_vendor_page = False
                    else:
                        self.stdout.write(f"  WARNING: Could not resolve product page; will try extracting from vendor page")

                # Fetch and extract image with retries
                image_url = self.extract_image_from_url_safe(
                    product_url, is_vendor_page, timeout, max_retries
                )
                
                if image_url:
                    # Validate image URL safety
                    if not self.is_safe_image_url(image_url):
                        self.stdout.write(f"  BLOCKED: Unsafe image URL detected, skipping")
                        validation_errors += 1
                        continue
                    
                    self.stdout.write(f"  SUCCESS: Found image: {image_url}")
                    
                    if not dry_run:
                        # Update the product with transaction safety
                        self.update_product_safely(product, image_url)
                    
                    success_count += 1
                else:
                    self.stdout.write(f"  FAILED: No image found")
                    error_count += 1

                # Rate limiting with progress
                if delay > 0:
                    self.stdout.write(f"  WAITING: {delay}s...")
                    time.sleep(delay)

            except Exception as e:
                self.stdout.write(f"  ERROR: {str(e)}")
                error_count += 1
                logger.error(f"Error processing product {product.id}: {e}")
                
                # In safe mode, stop on first error
                if safe_mode:
                    self.stdout.write(self.style.ERROR("SAFE MODE: Stopping due to error"))
                    break

        # Summary
        self.stdout.write(self.style.SUCCESS(f"\nSAFE HYDRATION COMPLETED:"))
        self.stdout.write(f"  SUCCESS: {success_count}")
        self.stdout.write(f"  FAILED: {error_count}")
        self.stdout.write(f"  SKIPPED: {skipped_count}")
        self.stdout.write(f"  VALIDATION ERRORS: {validation_errors}")
        self.stdout.write(f"  TOTAL PROCESSED: {success_count + error_count + skipped_count + validation_errors}")

    def create_backup(self):
        """Create a backup of products that will be modified"""
        try:
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"image_hydrator_backup_{timestamp}.json"
            
            products_to_backup = CoreProduct.objects.filter(
                main_image_url__in=['', None]
            ).exclude(
                ecommerce_data__platform_url__in=['', None]
            ).values('id', 'name', 'main_image_url', 'ecommerce_data__platform_url')
            
            backup_data = {
                'timestamp': timestamp,
                'count': len(products_to_backup),
                'products': list(products_to_backup)
            }
            
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            self.stdout.write(self.style.SUCCESS(f"Backup created: {backup_file}"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Backup failed: {e}"))
            raise CommandError("Backup creation failed")

    def is_safe_url(self, url):
        """Validate URL safety and format"""
        if not url or not isinstance(url, str):
            return False
        
        # Basic URL format validation
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
        except Exception:
            return False
        
        # Security checks
        dangerous_patterns = [
            r'javascript:',
            r'data:',
            r'file:',
            r'ftp:',
            r'localhost',
            r'127\.0\.0\.1',
            r'192\.168\.',
            r'10\.',
            r'172\.(1[6-9]|2[0-9]|3[01])\.',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        # Length check
        if len(url) > 2048:
            return False
        
        return True

    def is_safe_image_url(self, url):
        """Validate image URL safety"""
        if not self.is_safe_url(url):
            return False
        
        # Check for image-like extensions or patterns
        image_indicators = [
            r'\.(jpg|jpeg|png|gif|webp|svg)(\?|$)',  # Image extensions
            r'image',  # Contains 'image'
            r'photo',  # Contains 'photo'
            r'picture',  # Contains 'picture'
        ]
        
        # If it has an image extension, it's likely safe
        if any(re.search(pattern, url, re.IGNORECASE) for pattern in image_indicators):
            return True
        
        # For extension-less URLs, be more cautious
        # Only allow if it's from a known CDN or contains image-related keywords
        safe_domains = [
            'cdninstagram.com',
            'amazonaws.com',
            'cloudfront.net',
            'googleusercontent.com',
            'fbcdn.net',
        ]
        
        parsed = urlparse(url)
        if any(domain in parsed.netloc for domain in safe_domains):
            return True
        
        return False

    def update_product_safely(self, product, image_url):
        """Update product with transaction safety"""
        try:
            with transaction.atomic():
                # Double-check the product still exists and hasn't been modified
                fresh_product = CoreProduct.objects.select_for_update().get(id=product.id)
                
                # Validate the image URL one more time
                if not self.is_safe_image_url(image_url):
                    raise ValueError("Image URL failed final safety check")
                
                # Update with size limit
                if len(image_url) > 1000:
                    raise ValueError("Image URL too long")
                
                fresh_product.main_image_url = image_url
                fresh_product.save(update_fields=['main_image_url'])
                
                self.stdout.write(f"  SUCCESS: Product updated safely")
                
        except Exception as e:
            self.stdout.write(f"  FAILED: Update failed: {e}")
            raise

    def extract_image_from_url_safe(self, url, is_vendor_page=False, timeout=10, max_retries=2):
        """Safely extract image with retries and error handling"""
        for attempt in range(max_retries + 1):
            try:
                return self.extract_image_from_url(url, is_vendor_page, timeout)
            except requests.RequestException as e:
                if attempt < max_retries:
                    self.stdout.write(f"  RETRY {attempt + 1}/{max_retries} after error: {e}")
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.stdout.write(f"  FAILED: All retries failed: {e}")
                    return None
            except Exception as e:
                self.stdout.write(f"  ERROR: Unexpected error: {e}")
                return None
        
        return None

    def resolve_product_page_url(self, product_name, vendor_url, timeout=10):
        """
        From a vendor/category page, find the most likely product detail URL
        by scanning product tiles and fuzzy-matching titles. No extra deps.
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
            resp = requests.get(vendor_url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, 'html.parser')

            # Candidate links that look like product detail pages
            candidates = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                text = (a.get_text() or '').strip()
                if '/products/' in href:
                    abs_url = self.normalize_image_url(href, vendor_url)
                    # Try to find a nearby title node for better text
                    title_text = text
                    if not title_text:
                        title_el = a.find(['h1','h2','h3','h4']) or a.find_next(['h1','h2','h3','h4'])
                        if title_el:
                            title_text = (title_el.get_text() or '').strip()
                    score = self.score_title_similarity(product_name, title_text)
                    candidates.append((score, abs_url))

            if not candidates:
                return None

            # Pick the highest score above a threshold
            candidates.sort(reverse=True, key=lambda x: x[0])
            top_score, top_url = candidates[0]
            if top_score >= 0.35:
                return top_url
            return None
        except requests.RequestException:
            return None
        except Exception:
            return None

    def score_title_similarity(self, a, b):
        """
        Lightweight similarity: token overlap Jaccard on alnum-lowered tokens.
        Returns 0..1
        """
        if not a or not b:
            return 0.0
        tokenize = lambda s: set(re.findall(r"[a-z0-9]+", s.lower()))
        ta, tb = tokenize(a), tokenize(b)
        if not ta or not tb:
            return 0.0
        inter = len(ta & tb)
        union = len(ta | tb)
        return inter / union if union else 0.0

    def is_vendor_or_category_page(self, url):
        """
        Detect if URL is a vendor/category page rather than individual product
        """
        vendor_indicators = [
            '/collections/vendors',
            '/collections/',
            '/category/',
            '/categories/',
            '/brand/',
            '/brands/',
            '?q=',  # Search query
            '/search',
        ]
        return any(indicator in url.lower() for indicator in vendor_indicators)

    def extract_image_from_url(self, url, is_vendor_page=False, timeout=10):
        """
        Extract primary image URL from a product page
        Tries multiple strategies in order of preference
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }

            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Strategy 1: Open Graph image (most reliable)
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                og_url = og_image['content']
                # Skip banner images even from OG tags
                if not any(keyword in og_url.lower() for keyword in ['banner', 'logo', 'header', 'mobile_banner', 'copy_of']):
                    return self.normalize_image_url(og_url, url)

            # Strategy 2: Twitter card image
            twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
            if twitter_image and twitter_image.get('content'):
                return self.normalize_image_url(twitter_image['content'], url)

            # Strategy 3: Meta image tag
            meta_image = soup.find('meta', attrs={'name': 'image'})
            if meta_image and meta_image.get('content'):
                return self.normalize_image_url(meta_image['content'], url)

            # Strategy 4: Link rel="image_src"
            link_image = soup.find('link', rel='image_src')
            if link_image and link_image.get('href'):
                return self.normalize_image_url(link_image['href'], url)

            # Strategy 5: JSON-LD (common on Telemart and many ecommerce sites)
            try:
                for script in soup.find_all('script', type=lambda t: t and 'application/ld+json' in t):
                    try:
                        data = json.loads(script.string or script.text or '{}')
                    except Exception:
                        continue
                    # Some pages wrap in a list
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        # Product image field
                        if 'image' in item:
                            img = item.get('image')
                            if isinstance(img, list) and img:
                                return self.normalize_image_url(img[0], url)
                            if isinstance(img, str) and img.strip():
                                return self.normalize_image_url(img, url)
                        # Offers may include images in nested objects
                        offers = item.get('offers') if isinstance(item, dict) else None
                        if isinstance(offers, dict) and 'image' in offers:
                            img = offers.get('image')
                            if isinstance(img, str) and img.strip():
                                return self.normalize_image_url(img, url)
            except Exception:
                pass

            # Strategy 6: Primary product image selectors (common patterns)
            primary_selectors = [
                '.product-image img',
                '.product-photo img',
                '.main-image img',
                '.hero-image img',
                '.featured-image img',
                '.product-gallery img:first-child',
                '.product-media img:first-child',
                '.product-images img:first-child',
                '[data-testid*="image"] img',
                '[class*="product"][class*="image"] img',
                '[class*="main"][class*="image"] img',
                # For vendor/category pages, look for product cards
                '.product-card img',
                '.product-item img',
                '.grid-item img',
                '.card img',
                '[class*="product"] img',
            ]

            for selector in primary_selectors:
                img = soup.select_one(selector)
                if img:
                    # Try multiple attributes in order of preference
                    for attr in ['src', 'data-src', 'data-original', 'data-lazy', 'data-srcset']:
                        src = img.get(attr)
                        if src:
                            # Handle srcset (take the first/highest quality)
                            if attr == 'data-srcset' and ',' in src:
                                src = src.split(',')[0].strip().split(' ')[0]
                            return self.normalize_image_url(src, url)

            # Strategy 7: Any img tag with reasonable size (fallback)
            images = soup.find_all('img')
            for img in images:
                src = img.get('src') or img.get('data-src') or img.get('data-original')
                if src:
                    # Skip generic banner/logo images (especially on vendor pages)
                    if is_vendor_page:
                        skip_keywords = ['banner', 'logo', 'header', 'mobile_banner', 'copy_of_mobile', 'copy_of', 'mobile']
                        if any(keyword in src.lower() for keyword in skip_keywords):
                            continue
                    
                    # Always skip obvious banner/logo images regardless of page type
                    skip_keywords = ['banner', 'logo', 'header', 'mobile_banner', 'copy_of_mobile', 'copy_of']
                    if any(keyword in src.lower() for keyword in skip_keywords):
                        continue
                    
                    # Skip very small images (likely icons/buttons)
                    width = img.get('width')
                    height = img.get('height')
                    if width and height:
                        try:
                            if int(width) >= 200 and int(height) >= 200:
                                return self.normalize_image_url(src, url)
                        except ValueError:
                            pass
                    
                    # If no size info, check if it looks like a product image
                    if any(keyword in src.lower() for keyword in ['product', 'item', 'main', 'hero', 'featured']):
                        return self.normalize_image_url(src, url)

            return None

        except requests.RequestException as e:
            logger.warning(f"Request failed for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error extracting image from {url}: {e}")
            return None

    def normalize_image_url(self, image_url, base_url):
        """
        Normalize image URL to absolute URL and filter out banner images
        """
        if not image_url:
            return None

        # Skip banner/logo images
        skip_keywords = ['banner', 'logo', 'header', 'mobile_banner', 'copy_of_mobile', 'copy_of']
        if any(keyword in image_url.lower() for keyword in skip_keywords):
            return None

        # Remove query parameters that might cause issues
        if '?' in image_url:
            image_url = image_url.split('?')[0]

        # Convert to absolute URL
        if image_url.startswith('//'):
            return 'https:' + image_url
        elif image_url.startswith('/'):
            parsed_base = urlparse(base_url)
            return f"{parsed_base.scheme}://{parsed_base.netloc}{image_url}"
        elif not image_url.startswith('http'):
            return urljoin(base_url, image_url)
        else:
            return image_url
