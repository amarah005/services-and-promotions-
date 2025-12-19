#!/usr/bin/env python
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from products.models import ProductCategory, CoreProduct


BOOKS_PARENT_NAME = "Books & Stationery"
SUBCATS = [
    "Academic Books",
    "Novels & Literature",
    "Self-help & Business",
    "Stationery",
]


class Command(BaseCommand):
    help = "Remap Books & Stationery categories to correct parent/main_category and re-link products"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", default=False, help="Preview changes only")

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Ensure parent exists
        parent, created = ProductCategory.objects.get_or_create(
            name=BOOKS_PARENT_NAME,
            defaults={
                "slug": slugify(BOOKS_PARENT_NAME)[:110],
                "main_category": BOOKS_PARENT_NAME,
                "subcategory": "",
                "description": "Books and Stationery",
                "is_active": True,
            },
        )
        if not created:
            # Normalize parent main_category
            parent.main_category = BOOKS_PARENT_NAME
            parent.subcategory = ""
            if not dry_run:
                parent.save(update_fields=["main_category", "subcategory"])
        self.stdout.write(self.style.SUCCESS(f"Parent category: {parent.name} (id={parent.id})"))

        # Ensure child categories exist and are correctly linked
        child_map = {}
        for name in SUBCATS:
            child, created = ProductCategory.objects.get_or_create(
                name=name,
                defaults={
                    "slug": slugify(name)[:110],
                    "main_category": BOOKS_PARENT_NAME,
                    "subcategory": name,
                    "parent": parent,
                    "is_active": True,
                },
            )
            # Normalize in case they existed with wrong fields
            child.main_category = BOOKS_PARENT_NAME
            child.subcategory = name
            child.parent = parent
            if not dry_run:
                child.save(update_fields=["main_category", "subcategory", "parent"])
            child_map[name] = child
            self.stdout.write(self.style.SUCCESS(f"Child category: {name} (id={child.id})"))

        # Fix any categories with name in SUBCATS but wrong parent/main_category
        fixes = ProductCategory.objects.filter(name__in=SUBCATS).exclude(parent_id=parent.id)
        fixed_count = 0
        for cat in fixes:
            cat.main_category = BOOKS_PARENT_NAME
            cat.subcategory = cat.name
            cat.parent = parent
            if not dry_run:
                cat.save(update_fields=["main_category", "subcategory", "parent"])
            fixed_count += 1
        self.stdout.write(f"Fixed existing child categories: {fixed_count}")

        # Relink products: if product.category name equals any SUBCATS, ensure it points to the normalized child
        relinked = 0
        for name, child in child_map.items():
            qs = CoreProduct.objects.filter(category__name=name).exclude(category_id=child.id)
            count = qs.count()
            if count:
                if not dry_run:
                    qs.update(category_id=child.id)
                relinked += count
                self.stdout.write(f"Relinked products to {name}: {count}")

        # Also handle products where category.main_category accidentally equals the subcat name
        for name, child in child_map.items():
            qs2 = CoreProduct.objects.filter(category__main_category=name).exclude(category_id=child.id)
            count2 = qs2.count()
            if count2:
                if not dry_run:
                    qs2.update(category_id=child.id)
                relinked += count2
                self.stdout.write(f"Relinked products by main_category={name}: {count2}")

        self.stdout.write(self.style.SUCCESS(f"Done. Relinked products: {relinked}"))
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run only; no changes were committed."))

