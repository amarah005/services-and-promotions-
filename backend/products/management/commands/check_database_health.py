#!/usr/bin/env python3
from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from products.models import CoreProduct
import re


PLACEHOLDER_KEYWORDS = [
    'logo', 'placeholder', 'default', 'sprite', 'icon', 'noimage', 'no-image',
    'nimage', 'bvh', 'buyvaulthub', 'favicon', 'brand', 'dummy'
]

SAFE_CDN_HINTS = [
    'cloudfront.net', 'cdn.shopify.com', 'cdninstagram.com', 'alfatah.com.pk'
]


def is_placeholder(url: str) -> bool:
    if not url:
        return True
    lower = url.lower()
    if any(k in lower for k in PLACEHOLDER_KEYWORDS):
        # allowlist for known real CDNs to avoid false positives
        if any(h in lower for h in SAFE_CDN_HINTS):
            return False
        return True
    if lower.endswith('.svg'):
        return True
    if lower == 'https://:0' or lower.startswith('https://:0'):
        return True
    return False


def is_vendor_or_category(url: str) -> bool:
    if not url:
        return True
    u = url.lower()
    patterns = [
        '/collections/vendors', '/collections/', '/category/', '/categories/',
        '/brand/', '/brands/', '/search', '?q='
    ]
    return any(p in u for p in patterns)


class Command(BaseCommand):
    help = "Comprehensive database health check for products. Reports counts and common issues."

    def add_arguments(self, parser):
        parser.add_argument('--platform', type=str, default='', help='Filter by platform display name (icontains)')
        parser.add_argument('--limit', type=int, default=10, help='Sample size per issue list')

    def handle(self, *args, **options):
        platform = options['platform']
        limit = options['limit']

        qs = CoreProduct.objects.filter(is_active=True).select_related('ecommerce_data__platform')
        if platform:
            qs = qs.filter(ecommerce_data__platform__display_name__icontains=platform)

        total = qs.count()
        self.stdout.write(self.style.SUCCESS(f"Total active products: {total}"))

        by_platform = (
            qs.values('ecommerce_data__platform__display_name')
            .annotate(c=Count('id')).order_by('-c')
        )
        self.stdout.write("\nBy platform:")
        for row in by_platform:
            name = row['ecommerce_data__platform__display_name'] or 'Unknown'
            self.stdout.write(f" - {name}: {row['c']}")

        # Checks
        issues = {}

        # 1) Missing images
        missing_img = qs.filter(Q(main_image_url__isnull=True) | Q(main_image_url=''))
        issues['missing_images'] = list(missing_img[:limit])
        self.stdout.write(self.style.WARNING(f"\nMissing images: {missing_img.count()}"))

        # 2) Placeholder/dummy images
        placeholders = [p.id for p in qs.exclude(main_image_url__isnull=True).exclude(main_image_url='')
                        if is_placeholder(p.main_image_url or '')]
        ph_qs = qs.filter(id__in=placeholders)
        issues['placeholder_images'] = list(ph_qs[:limit])
        self.stdout.write(self.style.WARNING(f"Placeholder/logo images: {ph_qs.count()}"))

        # 3) Invalid image URLs
        invalid = [p.id for p in qs if (p.main_image_url and not p.main_image_url.lower().startswith('http')) or (p.main_image_url and len(p.main_image_url) > 1000)]
        inv_qs = qs.filter(id__in=invalid)
        issues['invalid_image_urls'] = list(inv_qs[:limit])
        self.stdout.write(self.style.WARNING(f"Invalid image URLs: {inv_qs.count()}"))

        # 4) Vendor/category platform URLs (bad for hydration)
        vendor_urls = [p.id for p in qs.exclude(ecommerce_data__platform_url__isnull=True).exclude(ecommerce_data__platform_url='')
                       if is_vendor_or_category(getattr(getattr(p, 'ecommerce_data', None), 'platform_url', ''))]
        ven_qs = qs.filter(id__in=vendor_urls)
        issues['vendor_platform_urls'] = list(ven_qs[:limit])
        self.stdout.write(self.style.WARNING(f"Vendor/category platform URLs: {ven_qs.count()}"))

        # 5) Duplicates by seller+name
        dup_keys = (
            qs.values('seller_id', 'name')
            .annotate(c=Count('id')).filter(c__gt=1)
        )
        dup_total = sum(r['c'] for r in dup_keys)
        self.stdout.write(self.style.WARNING(f"Duplicates by seller+name groups: {dup_keys.count()} (total rows in groups: {dup_total})"))

        # Print samples
        def show_list(title, items):
            if not items:
                return
            self.stdout.write(self.style.SUCCESS(f"\n{title}:"))
            for p in items:
                plat = getattr(getattr(p, 'ecommerce_data', None), 'platform', None)
                plat_name = plat.display_name if plat else 'Unknown'
                url = getattr(getattr(p, 'ecommerce_data', None), 'platform_url', '')
                self.stdout.write(f" - {p.name[:90]} | {plat_name}\n   img: {p.main_image_url}\n   url: {url}")

        show_list('SAMPLE Missing images', issues['missing_images'])
        show_list('SAMPLE Placeholder/logo images', issues['placeholder_images'])
        show_list('SAMPLE Invalid image URLs', issues['invalid_image_urls'])
        show_list('SAMPLE Vendor/category platform URLs', issues['vendor_platform_urls'])

        self.stdout.write(self.style.SUCCESS("\nHealth check complete."))


