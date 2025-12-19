#!/usr/bin/env python
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from products.models import CoreProduct, EcommerceProduct, InstagramProduct, Wishlist


TARGET_MAIN = "Books & Stationery"
SUBCATS = [
    "Academic Books",
    "Novels & Literature",
    "Self-help & Business",
    "Stationery",
]


class Command(BaseCommand):
    help = "Delete all products (and related) under Books & Stationery categories"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", default=False, help="Preview only; no deletions")
        parser.add_argument("--batch", type=int, default=1000, help="batch size for deletion")

    @transaction.atomic
    def handle(self, *args, **options):
        dry = options["dry_run"]
        batch_size = options["batch"]

        q = Q(category__main_category=TARGET_MAIN) | Q(category__name__in=SUBCATS) | Q(category__subcategory__in=SUBCATS)
        ids = list(CoreProduct.objects.filter(q).values_list("id", flat=True))
        total = len(ids)
        self.stdout.write(f"Found {total} CoreProduct rows to delete")

        deleted_wishlist = 0
        deleted_ecomm = 0
        deleted_instagram = 0
        deleted_products = 0

        for i in range(0, total, batch_size):
            chunk = ids[i:i+batch_size]
            if not chunk:
                continue
            # delete dependents first
            if not dry:
                deleted_wishlist += Wishlist.objects.filter(product_id__in=chunk).delete()[0]
                deleted_ecomm += EcommerceProduct.objects.filter(product_id__in=chunk).delete()[0]
                deleted_instagram += InstagramProduct.objects.filter(product_id__in=chunk).delete()[0]
                deleted_products += CoreProduct.objects.filter(id__in=chunk).delete()[0]
            else:
                self.stdout.write(f"Dry-run: would delete batch of {len(chunk)} products")

        self.stdout.write(f"Wishlist deleted: {deleted_wishlist}")
        self.stdout.write(f"EcommerceProduct deleted: {deleted_ecomm}")
        self.stdout.write(f"InstagramProduct deleted: {deleted_instagram}")
        self.stdout.write(self.style.SUCCESS(f"CoreProduct deleted: {deleted_products}"))


