import sys
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Case, When, IntegerField

from products.models import CoreProduct


class Command(BaseCommand):
    help = "Safely deduplicate CoreProduct rows by (seller, name). Keeps the best record and deactivates the rest."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only report actions without modifying the database.",
        )
        parser.add_argument(
            "--limit-groups",
            type=int,
            default=200,
            help="Maximum number of duplicate groups to process in one run.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        limit_groups = max(1, min(int(options.get("limit_groups") or 200), 2000))

        self.stdout.write(self.style.NOTICE("🔎 Scanning for duplicate CoreProduct groups (seller + name)..."))

        dup_groups = (
            CoreProduct.objects.values("seller_id", "name")
            .annotate(c=Count("id"))
            .filter(c__gt=1)
            .order_by("-c")[:limit_groups]
        )

        total_groups = dup_groups.count()
        if total_groups == 0:
            self.stdout.write(self.style.SUCCESS("✅ No duplicate groups found."))
            return

        self.stdout.write(self.style.WARNING(f"Found {total_groups} duplicate groups. Processing up to {limit_groups}..."))

        processed_groups = 0
        deactivated = 0

        for grp in dup_groups:
            seller_id = grp["seller_id"]
            name = grp["name"]

            # Rank candidates by completeness
            candidates = (
                CoreProduct.objects.filter(seller_id=seller_id, name=name)
                .annotate(
                    has_url=Case(
                        When(
                            ecommerce_data__platform_url__isnull=False,
                            ecommerce_data__platform_url__gt="",
                            then=1,
                        ),
                        default=0,
                        output_field=IntegerField(),
                    ),
                    has_image=Case(
                        When(main_image_url__isnull=False, main_image_url__gt="", then=1),
                        default=0,
                        output_field=IntegerField(),
                    ),
                )
                .order_by("-has_url", "-has_image", "-created_at")
            )

            keep = candidates.first()
            to_deactivate = list(candidates[1:])

            if not keep or not to_deactivate:
                continue

            processed_groups += 1
            self.stdout.write(
                f"Group seller={seller_id} name='{name}' -> keep id={keep.id} (url={keep.ecommerce_data.platform_url if getattr(keep, 'ecommerce_data', None) else None}, image={bool(keep.main_image_url)}) deactivate {len(to_deactivate)}"
            )

            if dry_run:
                # Just report
                continue

            with transaction.atomic():
                for prod in to_deactivate:
                    # Soft deactivate instead of delete to remain safe
                    prod.is_active = False
                    prod.save(update_fields=["is_active"])
                    deactivated += 1

        if dry_run:
            self.stdout.write(self.style.NOTICE(f"🔬 Dry-run complete. Groups analyzed: {processed_groups}. No changes applied."))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Deduplication complete. Groups processed: {processed_groups}. Deactivated: {deactivated}"))


