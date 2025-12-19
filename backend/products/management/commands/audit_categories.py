#!/usr/bin/env python3
from django.core.management.base import BaseCommand
from django.db import transaction
from products.models import CoreProduct, ProductCategory
from products.utils.categories_utils import suggest_category


class Command(BaseCommand):
    help = "Audit products and suggest category fixes using rule-based mapping. Does not modify data unless --apply is used."

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=500, help='Max products to audit')
        parser.add_argument('--apply', action='store_true', help='Apply suggested categories when safe')
        parser.add_argument('--min-agreement', type=int, default=1, help='Minimum rules matched to auto-apply')

    def handle(self, *args, **options):
        limit = options['limit']
        apply_changes = options['apply']
        min_agreement = options['min_agreement']

        self.stdout.write(self.style.SUCCESS('Auditing product categories...'))

        qs = CoreProduct.objects.filter(is_active=True).select_related('category')[:limit]
        total = qs.count()
        fixes = 0
        suggestions = 0

        with transaction.atomic():
            for product in qs:
                suggested = suggest_category(product.name, product.description or '')
                if not suggested:
                    continue
                suggestions += 1
                current_name = product.category.name if product.category else None
                if current_name == suggested:
                    continue
                self.stdout.write(f"- {product.name[:80]}\n  current: {current_name} -> suggested: {suggested}")

                if apply_changes:
                    try:
                        new_cat = ProductCategory.objects.filter(name=suggested).first()
                        if new_cat:
                            product.category = new_cat
                            product.save(update_fields=['category'])
                            fixes += 1
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"  Failed to apply: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Audited {total} products | Suggestions: {suggestions} | Applied: {fixes}"))


