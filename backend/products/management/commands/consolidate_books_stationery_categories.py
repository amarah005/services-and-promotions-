#!/usr/bin/env python
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from products.models import ProductCategory, CoreProduct


BOOKS_PARENT_NAME = "Books & Stationery"
SUBCATS = [
    "Academic Books",
    "Novels & Literature",
    "Self-help & Business",
    "Stationery",
]


class Command(BaseCommand):
    help = "Consolidate duplicate Books & Stationery child categories and relink products"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", default=False)

    @transaction.atomic
    def handle(self, *args, **options):
        dry = options["dry_run"]

        # Ensure one parent exists
        parent = ProductCategory.objects.filter(name=BOOKS_PARENT_NAME).first()
        if not parent:
            parent = ProductCategory.objects.create(
                name=BOOKS_PARENT_NAME,
                slug="books-stationery",
                main_category=BOOKS_PARENT_NAME,
                subcategory="",
                is_active=True,
            )
        self.stdout.write(f"Parent id={parent.id}")

        total_relinked = 0
        total_deleted = 0
        for name in SUBCATS:
            # Find all categories with this name
            cats = list(ProductCategory.objects.filter(name=name))
            if not cats:
                # create canonical
                canonical = ProductCategory(
                    name=name,
                    slug=name.lower().replace(" ", "-")[:110],
                    main_category=BOOKS_PARENT_NAME,
                    subcategory=name,
                    parent=parent,
                    is_active=True,
                )
                if not dry:
                    canonical.save()
                self.stdout.write(f"Created canonical for {name} (id={getattr(canonical, 'id', None)})")
                continue

            # Pick canonical: prefer one with parent=parent, else first
            canonical = None
            for c in cats:
                if c.parent_id == parent.id:
                    canonical = c
                    break
            canonical = canonical or cats[0]

            # Normalize canonical fields
            canonical.main_category = BOOKS_PARENT_NAME
            canonical.subcategory = name
            canonical.parent = parent
            if not dry:
                canonical.save(update_fields=["main_category", "subcategory", "parent"])

            # Move products from duplicates to canonical
            for dup in cats:
                if dup.id == canonical.id:
                    continue
                cnt = CoreProduct.objects.filter(category_id=dup.id).update(category_id=canonical.id)
                total_relinked += cnt
                # delete duplicate category
                if not dry:
                    dup.delete()
                total_deleted += 1
                self.stdout.write(f"Merged {dup.id} -> {canonical.id} (moved {cnt} products)")

        self.stdout.write(self.style.SUCCESS(f"Relinked products: {total_relinked}, Deleted duplicate categories: {total_deleted}"))


