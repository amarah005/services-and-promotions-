from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from products.models import CoreProduct, ProductCategory, ProductAuditLog
from products.utils.categories_utils import suggest_category


TARGET_PATTERNS = [
    'water dispenser', 'air purifier', 'fan', 'vacuum cleaner',
    'soundbar', 'portable speaker', 'bluetooth speaker',
    'nintendo switch', 'playstation', 'ps5', 'xbox',
]


class Command(BaseCommand):
    help = (
        "Reassign product categories based on hard rules from suggest_category.\n"
        "Applies only to products whose names/descriptions match targeted patterns."
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show changes without saving')
        parser.add_argument('--limit', type=int, default=500, help='Max products to process')
        parser.add_argument('--confirm', action='store_true', help='Required to persist changes when not dry-run')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        confirm = options['confirm']

        query = Q()
        for p in TARGET_PATTERNS:
            query |= Q(name__icontains=p) | Q(description__icontains=p)

        qs = CoreProduct.objects.filter(is_active=True).select_related('category')
        qs = qs.filter(query)[:limit]

        to_update = []
        for product in qs:
            current = product.category.name if product.category else None
            suggested = suggest_category(product.name or '', product.description or '')
            if suggested and suggested != current:
                to_update.append((product, current, suggested))

        self.stdout.write(self.style.NOTICE(f"Candidates: {len(to_update)}"))

        if dry_run or not confirm:
            self.stdout.write(self.style.WARNING("Dry-run (or missing --confirm). Sample changes:"))
            for product, current, suggested in to_update[:50]:
                self.stdout.write(f"id={product.id} | {current} -> {suggested} | {product.name[:120]}")
            if dry_run:
                return
            if not confirm:
                self.stdout.write(self.style.WARNING("Add --confirm to persist changes."))
                return

        changed = 0
        with transaction.atomic():
            for product, current, suggested in to_update:
                # Find or create the target category by name
                target_cat = ProductCategory.objects.filter(name=suggested).first()
                if not target_cat:
                    # Skip if the exact category name does not exist; we keep DB as source of truth
                    continue
                old_values = {'category': current}
                product.category = target_cat
                product.save(update_fields=['category'])
                ProductAuditLog.objects.create(
                    product=product,
                    action='updated',
                    changed_fields=['category'],
                    old_values=old_values,
                    new_values={'category': target_cat.name},
                    change_source='reassign_categories'
                )
                changed += 1

        self.stdout.write(self.style.SUCCESS(f"Reassigned categories for {changed} products"))


