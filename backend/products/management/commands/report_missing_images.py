#!/usr/bin/env python3
from django.core.management.base import BaseCommand
from django.db.models import Q
from products.models import CoreProduct
import re


PLACEHOLDER_KEYWORDS = [
    'logo', 'placeholder', 'default', 'sprite', 'icon', 'noimage', 'no-image',
    'nimage', 'bvh', 'buyvaulthub', 'favicon', 'brand', 'dummy'
]

def is_placeholder(url: str) -> bool:
    if not url:
        return True
    lower = url.lower()
    if any(k in lower for k in PLACEHOLDER_KEYWORDS):
        return True
    if lower.endswith('.svg'):
        return True
    return False


class Command(BaseCommand):
    help = 'Report products with missing or placeholder images, grouped by platform'

    def add_arguments(self, parser):
        parser.add_argument('--platforms', type=str, default='', help='Comma-separated platform names (icontains). Example: Telemart,Friends')
        parser.add_argument('--limit', type=int, default=50, help='Max samples per platform to display')

    def handle(self, *args, **options):
        platforms = [p.strip() for p in options['platforms'].split(',') if p.strip()] or []
        limit = options['limit']

        base_qs = CoreProduct.objects.filter(is_active=True).select_related('ecommerce_data__platform')
        if platforms:
            q = Q()
            for p in platforms:
                q |= Q(ecommerce_data__platform__display_name__icontains=p)
            base_qs = base_qs.filter(q)

        # Split into missing and placeholder
        missing = base_qs.filter(Q(main_image_url__isnull=True) | Q(main_image_url=''))
        placeholder_ids = [p.id for p in base_qs.exclude(main_image_url__isnull=True).exclude(main_image_url='')
                           if is_placeholder(p.main_image_url or '')]
        placeholder = base_qs.filter(id__in=placeholder_ids)

        # Group by platform
        def summarize(qs, title):
            by_platform = {}
            for p in qs:
                plat = getattr(getattr(p, 'ecommerce_data', None), 'platform', None)
                name = plat.display_name if plat else 'Unknown'
                by_platform.setdefault(name, []).append(p)

            self.stdout.write(self.style.SUCCESS(f"\n=== {title} ==="))
            total = 0
            for plat_name, items in by_platform.items():
                total += len(items)
                self.stdout.write(self.style.WARNING(f"{plat_name}: {len(items)}"))
                for p in items[:limit]:
                    url = getattr(getattr(p, 'ecommerce_data', None), 'platform_url', '')
                    self.stdout.write(f" - {p.name[:80]}\n   image: {p.main_image_url or ''}\n   url:   {url}")
            self.stdout.write(self.style.SUCCESS(f"Total {title.lower()}: {total}"))

        summarize(list(missing), 'MISSING IMAGES')
        summarize(list(placeholder), 'PLACEHOLDER/LOGO IMAGES')


