#!/usr/bin/env python
from django.core.management.base import BaseCommand
from django.db import transaction

from products.models import ProductCategory


BOOKS_PARENT_NAME = "Books & Stationery"
SUBCATS = [
    "Academic Books",
    "Novels & Literature",
    "Self-help & Business",
    "Stationery",
]


class Command(BaseCommand):
    help = "Delete Books & Stationery parent and child ProductCategory rows (use after deleting products)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", default=False)

    @transaction.atomic
    def handle(self, *args, **options):
        dry = options["dry_run"]

        # Delete children
        child_qs = ProductCategory.objects.filter(name__in=SUBCATS)
        child_count = child_qs.count()
        if not dry:
            child_qs.delete()
        self.stdout.write(f"Deleted child categories: {child_count}")

        # Delete parent
        parent_qs = ProductCategory.objects.filter(name=BOOKS_PARENT_NAME)
        parent_count = parent_qs.count()
        if not dry:
            parent_qs.delete()
        self.stdout.write(f"Deleted parent categories: {parent_count}")


