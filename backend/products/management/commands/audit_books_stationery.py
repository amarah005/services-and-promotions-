#!/usr/bin/env python
from django.core.management.base import BaseCommand
from django.db.models import Count, Min, Max, Q

from products.models import CoreProduct


TARGET_MAIN = "Books & Stationery"
SUBCATS = [
    "Academic Books",
    "Novels & Literature",
    "Self-help & Business",
    "Stationery",
]


class Command(BaseCommand):
    help = "Audit scraped Books & Stationery data: counts, prices, sample rows, anomalies"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=5, help="sample size per subcategory")

    def handle(self, *args, **options):
        limit = options["limit"]

        # Overall counts
        total = CoreProduct.objects.filter(
            Q(category__main_category=TARGET_MAIN) | Q(category__name__in=SUBCATS)
        ).count()
        self.stdout.write(f"Total Books & Stationery products: {total}")

        # Counts per subcategory
        per_sub = (
            CoreProduct.objects.filter(
                Q(category__main_category=TARGET_MAIN) | Q(category__name__in=SUBCATS)
            )
            .values("category__name")
            .annotate(c=Count("id"))
            .order_by("-c")
        )
        self.stdout.write("Counts by category name:")
        for row in per_sub:
            self.stdout.write(f"  {row['category__name'] or 'Unknown'}: {row['c']}")

        # Price stats only for rows with numeric price
        price_stats = CoreProduct.objects.filter(
            Q(category__main_category=TARGET_MAIN) | Q(category__name__in=SUBCATS),
            price__isnull=False,
        ).aggregate(min_price=Min("price"), max_price=Max("price"), count=Count("id"))
        self.stdout.write(
            f"Price stats (with price): min={price_stats['min_price']} max={price_stats['max_price']} count={price_stats['count']}"
        )

        # Missing/zero prices
        missing_prices = CoreProduct.objects.filter(
            Q(category__main_category=TARGET_MAIN) | Q(category__name__in=SUBCATS),
            Q(price__isnull=True) | Q(price=0)
        ).count()
        self.stdout.write(f"Missing/zero prices: {missing_prices}")

        # Samples per subcategory
        for sub in SUBCATS:
            qs = CoreProduct.objects.filter(
                Q(category__name=sub) | (Q(category__main_category=TARGET_MAIN) & Q(category__subcategory=sub))
            ).select_related("category", "seller__platform").order_by("-created_at")[:limit]
            self.stdout.write(f"\nSample: {sub}")
            for p in qs:
                platform = getattr(getattr(p, "seller", None), "platform", None)
                platform_name = getattr(platform, "display_name", p.platform_type)
                self.stdout.write(
                    f" - {p.name[:70]} | price={p.price} {p.currency} | cat={p.category.name if p.category else None} | main={p.category.main_category if p.category else None} | platform={platform_name} | url={(getattr(getattr(p, 'ecommerce_data', None), 'platform_url', '') or getattr(getattr(p, 'instagram_data', None), 'post_url', ''))[:80]}"
                )

        # Anomalies: category main_category not equal to target or category name equals main
        anomalies = CoreProduct.objects.filter(
            Q(category__name__in=SUBCATS) & ~Q(category__main_category=TARGET_MAIN)
        ).count()
        self.stdout.write(f"Anomalies (child with wrong main_category): {anomalies}")

        # Anomalies: Chase Value off-topic items likely slipped through
        off_topic = CoreProduct.objects.filter(
            Q(category__name="Stationery") & Q(seller__platform__display_name__icontains="Chase Value"),
        ).count()
        self.stdout.write(f"Chase Value Stationery items: {off_topic}")


