#!/usr/bin/env python3
from django.core.management.base import BaseCommand
from django.db.models import Q
from products.models import CoreProduct
import re


# Broader patterns commonly seen for non-product images
PLACEHOLDER_KEYWORDS = [
    'logo', 'placeholder', 'default', 'sprite', 'icon', 'noimage', 'no-image',
    'nimage', 'bvh', 'buyvaulthub', 'favicon', 'brand', 'dummy'
]

# Domain/file hints for known logos/bad images
PLACEHOLDER_PATTERNS = [
    r"/logo[\w-]*\.(?:png|jpg|jpeg|svg)$",
    r"/logos?/",
    r"/placeholders?/",
    r"/brand[s]?/",
    r"/favicon[\w-]*\.(?:png|ico|svg)$",
    r"shophive\.com/.*/logo",
    r"telemart\.pk/.*/logo",
    r"cdninstagram\.com/.*/sprite",
]

def is_placeholder_url(url: str) -> bool:
    if not url:
        return False
    lower = url.lower()
    if any(k in lower for k in PLACEHOLDER_KEYWORDS):
        return True
    for pat in PLACEHOLDER_PATTERNS:
        if re.search(pat, lower):
            return True
    # Very small SVGs are often icons/logos
    if lower.endswith('.svg'):
        return True
    return False


class Command(BaseCommand):
    help = "Null out placeholder/logo image URLs so the hydrator can refill real images."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show counts only, do not modify')
        parser.add_argument('--limit', type=int, default=0, help='Limit records to inspect/update')
        parser.add_argument('--platform', type=str, default='', help='Filter by ecommerce platform display name (icontains)')

    def handle(self, *args, **options):
        # Start from active products with any image set
        base_qs = CoreProduct.objects.filter(is_active=True).exclude(main_image_url__isnull=True).exclude(main_image_url='')
        if options['platform']:
            base_qs = base_qs.filter(
                ecommerce_data__platform__display_name__icontains=options['platform']
            )

        # Pull candidates and filter in Python with robust matcher
        candidates = list(base_qs.values('id', 'name', 'main_image_url')[: options['limit'] or 100000])
        ids_to_clear = [c['id'] for c in candidates if is_placeholder_url(c['main_image_url'] or '')]

        affected = CoreProduct.objects.filter(id__in=ids_to_clear)
        count = affected.count()
        self.stdout.write(f"Found {count} products with placeholder-like images")
        if options['dry_run']:
            return

        updated = affected.update(main_image_url='')
        self.stdout.write(self.style.SUCCESS(f"Cleared main_image_url for {updated} products"))


