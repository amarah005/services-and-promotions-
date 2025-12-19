from django.core.management.base import BaseCommand
from django.db.models import Q

from products.models import CoreProduct, ProductCategory
from products.utils.categories_utils import suggest_category


class Command(BaseCommand):
    help = (
        "Verify product category assignments by comparing current category to a simple suggestion engine.\n"
        "Reports mismatches and top offenders to help refine rules or mappings."
    )

    def add_arguments(self, parser):
        parser.add_argument('--main-category', default=None, help='Filter by ProductCategory.main_category')
        parser.add_argument('--platform', default=None, help='Filter by platform display name (contains)')
        parser.add_argument('--limit', type=int, default=50, help='Sample size to print for mismatches')

    def handle(self, *args, **options):
        main_category = options['main_category']
        platform = options['platform']
        limit = options['limit']

        qs = CoreProduct.objects.filter(is_active=True).select_related('category', 'brand', 'seller')
        if main_category:
            qs = qs.filter(category__main_category=main_category)
        if platform:
            qs = qs.filter(
                Q(platform_type='ecommerce') & Q(ecommerce_data__platform__display_name__icontains=platform)
                |
                Q(platform_type='instagram') & Q(seller__platform__display_name__icontains=platform)
            )

        total = qs.count()
        mismatches = []
        missing_category = []

        for p in qs[: min(total, 20000)]:
            current = p.category.name if p.category else None
            suggestion = suggest_category(p.name or '', p.description or '')
            if not current:
                if suggestion:
                    missing_category.append((p.id, suggestion, p.name[:120] if p.name else ''))
                continue
            # If we have a suggestion and it differs from current, mark as mismatch
            if suggestion and suggestion != current:
                mismatches.append((p.id, current, suggestion, p.name[:120] if p.name else ''))

        self.stdout.write(self.style.NOTICE(f"Total products scanned: {total}"))
        self.stdout.write(self.style.NOTICE(f"Products with missing category but suggestable: {len(missing_category)}"))
        self.stdout.write(self.style.NOTICE(f"Category mismatches: {len(mismatches)}"))

        if missing_category:
            self.stdout.write(self.style.WARNING("\nSample missing categories (id | suggested -> name):"))
            for pid, sugg, name in missing_category[:limit]:
                self.stdout.write(f"{pid} | {sugg} -> {name}")

        if mismatches:
            self.stdout.write(self.style.WARNING("\nSample mismatches (id | current -> suggested | name):"))
            for pid, cur, sugg, name in mismatches[:limit]:
                self.stdout.write(f"{pid} | {cur} -> {sugg} | {name}")

        self.stdout.write(self.style.SUCCESS("\nVerification complete."))


