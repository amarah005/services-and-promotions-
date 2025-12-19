#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import uuid
import hashlib
from decimal import Decimal, InvalidOperation
from typing import Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, IntegrityError
from django.utils.text import slugify as dj_slugify

from products.models import (
    Platform, Brand, Seller, ProductCategory,
    CoreProduct, EcommerceProduct
)
from products.utils.categories_utils import suggest_category


def slugify(text: str) -> str:
    s = (text or "").strip()
    s = dj_slugify(s)
    return s or str(uuid.uuid4())


def parse_bool(val: str) -> bool:
    return str(val).strip().lower() in {"1", "true", "yes", "y"}


def parse_int(val: str) -> Optional[int]:
    try:
        return int(str(val).strip()) if str(val).strip() else None
    except Exception:
        return None


def parse_decimal(val: str) -> Optional[Decimal]:
    t = str(val).strip()
    if not t:
        return None
    
    # Handle PKR format like "11 PKR" -> 11000
    if "PKR" in t.upper():
        # Extract number part
        number_part = t.upper().replace("PKR", "").strip()
        if number_part:
            try:
                # Convert 11 to 11000 (multiply by 1000)
                return Decimal(number_part) * 1000
            except InvalidOperation:
                return None
    
    # remove commas and non-numeric except dot
    cleaned = "".join(ch for ch in t if ch.isdigit() or ch == ".")
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def load_json(val: str, default):
    t = (val or "").strip()
    if not t:
        return default
    try:
        return json.loads(t)
    except Exception:
        return default


def trim_len(val: str, max_len: int) -> str:
    v = (val or "").strip()
    return v[:max_len]


def derive_platform_product_id(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return str(uuid.uuid4())
    # stable short hash
    return hashlib.sha1(u.encode("utf-8")).hexdigest()[:40]


class Command(BaseCommand):
    help = "Import products from unified CSV into the database"

    def add_arguments(self, parser):
        parser.add_argument("--csv-path", required=True, help="Path to CSV file")
        parser.add_argument("--dry-run", action="store_true", help="Validate only; no writes")
        parser.add_argument("--limit", type=int, default=0, help="Limit rows for import (0 = all)")

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        dry_run = options["dry_run"]
        limit = options["limit"]

        counters = {
            "platform": 0,
            "brand": 0,
            "seller": 0,
            "category": 0,
            "product_created": 0,
            "product_updated": 0,
            "ecomm_created": 0,
            "ecomm_updated": 0,
            "skipped": 0,
            "skipped_category": 0,
            "skipped_no_price": 0,
        }

        required_headers = [
            # Platform
            "platform_name","platform_display_name","platform_type","platform_base_url",
            # Seller
            "seller_username","seller_display_name","seller_profile_url",
            # Core product
            "uuid","product_name","product_slug","description","short_description",
            "price","original_price","currency","brand_name","main_category","subcategory",
            "model_number","sku","image_url",
            # Links
            "listing_page_url","product_url",
            # Stock & shipping
            "in_stock","stock_quantity","stock_status","shipping_cost","shipping_time","free_shipping",
            # Policies & extra
            "warranty_period","return_policy","specifications_json","features_json",
            "average_rating","review_count","original_category_path",
            # Scraper meta
            "scraper_type","scraped_at",
        ]

        try:
            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                missing = [h for h in required_headers if h not in reader.fieldnames]
                if missing:
                    raise CommandError(f"CSV missing required columns: {', '.join(missing)}")

                rows = list(reader)
        except FileNotFoundError:
            raise CommandError(f"CSV not found: {csv_path}")

        if limit and limit > 0:
            rows = rows[:limit]

        self.stdout.write(self.style.NOTICE(f"Importing {len(rows)} rows from {csv_path} (dry_run={dry_run})"))

        def import_row(row):
            # Skip category URLs - only import actual products
            product_url = (row.get("product_url") or "").strip()
            if not product_url or "product-category" in product_url:
                counters["skipped_category"] += 1
                return
            
            # Skip if no price (likely not a real product)
            price_str = (row.get("price") or "").strip()
            if not price_str:
                counters["skipped_no_price"] += 1
                return
            
            # Platform
            platform_name = (row["platform_name"] or "").strip().lower() or "platform"
            platform_display = (row["platform_display_name"] or platform_name).strip() or platform_name
            platform_type = (row["platform_type"] or "ecommerce").strip().lower()
            base_url = (row["platform_base_url"] or "").strip()

            platform, created = Platform.objects.get_or_create(
                name=platform_name,
                defaults={
                    "display_name": platform_display,
                    "platform_type": platform_type or "ecommerce",
                    "base_url": base_url,
                    "is_active": True,
                    "scraping_enabled": True,
                },
            )
            if created:
                counters["platform"] += 1
            else:
                # keep display_name/base_url fresh if provided
                changed = False
                if platform.display_name != platform_display and platform_display:
                    platform.display_name = platform_display; changed = True
                if base_url and platform.base_url != base_url:
                    platform.base_url = base_url; changed = True
                if changed and not dry_run:
                    platform.save()

            # Seller
            seller_username = (row["seller_username"] or platform_name).strip() or platform_name
            seller_display = (row["seller_display_name"] or seller_username).strip()
            seller_profile_url = (row["seller_profile_url"] or "").strip()

            seller, created = Seller.objects.get_or_create(
                platform=platform, username=seller_username,
                defaults={
                    "display_name": seller_display,
                    "profile_url": seller_profile_url,
                },
            )
            if created:
                counters["seller"] += 1

            # Brand (optional create if present)
            brand = None
            brand_name = (row["brand_name"] or "").strip()
            if brand_name:
                brand_slug = slugify(brand_name)
                brand, created = Brand.objects.get_or_create(
                    slug=brand_slug,
                    defaults={"name": brand_name, "display_name": brand_name},
                )
                if created:
                    counters["brand"] += 1

            # Category (main+sub) - Use automatic category matching if no category specified
            product_name = (row["product_name"] or "").strip()
            product_description = (row["description"] or "").strip()
            # Fallback: derive a readable name from product URL slug if missing
            if not product_name:
                url_for_name = (row.get("product_url") or "").strip()
                if url_for_name:
                    try:
                        from urllib.parse import urlparse
                        path = urlparse(url_for_name).path
                        # take last non-empty segment
                        seg = next((s for s in reversed(path.split('/')) if s), '')
                        if seg:
                            # replace hyphens/underscores with spaces and title-case
                            derived = seg.replace('-', ' ').replace('_', ' ').strip()
                            if derived:
                                product_name = derived.title()[:300]
                    except Exception:
                        pass
            
            # Try automatic category matching first
            suggested_category = suggest_category(product_name, product_description)
            
            if suggested_category:
                # Use suggested category
                main_category = "General"  # Will be updated based on suggested category
                subcategory = suggested_category
                
                # Find the actual category in database to get correct main_category
                try:
                    existing_category = ProductCategory.objects.get(name=suggested_category)
                    main_category = existing_category.main_category
                    category = existing_category
                    created = False
                except ProductCategory.DoesNotExist:
                    # Create new category with suggested name
                    cat_slug = slugify(suggested_category)
                    category, created = ProductCategory.objects.get_or_create(
                        slug=cat_slug,
                        defaults={
                            "name": suggested_category,
                            "main_category": "General",  # Will be updated later
                            "subcategory": suggested_category,
                            "is_active": True,
                        },
                    )
            else:
                # Fall back to CSV data
                main_category = (row["main_category"] or "").strip() or "General"
                subcategory = (row["subcategory"] or "").strip()
                cat_slug = slugify(f"{main_category}-{subcategory}" if subcategory else main_category)
                category, created = ProductCategory.objects.get_or_create(
                    slug=cat_slug,
                    defaults={
                        "name": subcategory or main_category,
                        "main_category": main_category,
                        "subcategory": subcategory,
                        "is_active": True,
                    },
                )
            if created:
                counters["category"] += 1

            # CoreProduct
            prod_uuid = (row["uuid"].strip() or str(uuid.uuid4())) if row["uuid"] else str(uuid.uuid4())
            name = (row["product_name"] or product_name or "").strip() or "Unnamed Product"
            slug = (row["product_slug"] or slugify(f"{name}-{seller_username}"))
            description = (row["description"] or "").strip()
            short_description = (row["short_description"] or description[:200]).strip()

            price = parse_decimal(row["price"])
            original_price = parse_decimal(row["original_price"])
            currency = (row["currency"] or "PKR").strip().upper()[:3]

            # ensure unique slug
            base_slug = slug
            i = 1
            while CoreProduct.objects.filter(slug=slug).exclude(uuid=prod_uuid).exists():
                slug = f"{base_slug}-{i}"
                i += 1

            core_defaults = {
                "name": name,
                "description": description,
                "short_description": short_description,
                "price": price,
                "original_price": original_price,
                "currency": currency,
                "brand": brand,
                "category": category,
                "seller": seller,
                "model_number": (row["model_number"] or "").strip(),
                "sku": (row["sku"] or "").strip(),
                "main_image_url": (row["image_url"] or "").strip(),
                "platform_type": "ecommerce",
            }

            try:
                core, created_core = CoreProduct.objects.update_or_create(
                    uuid=prod_uuid,
                    defaults={"slug": slug, **core_defaults},
                )
            except IntegrityError:
                # fallback by slug if needed
                core, created_core = CoreProduct.objects.update_or_create(
                    slug=slug,
                    defaults={"uuid": prod_uuid, **core_defaults},
                )

            if created_core:
                counters["product_created"] += 1
            else:
                counters["product_updated"] += 1

            # EcommerceProduct
            in_stock = parse_bool(row["in_stock"])
            stock_quantity = parse_int(row["stock_quantity"])
            stock_status = (row["stock_status"] or "").strip()
            platform_url = (row["product_url"] or "").strip()
            shipping_cost = parse_decimal(row["shipping_cost"]) or Decimal("0")
            shipping_time = (row["shipping_time"] or "").strip()
            free_shipping = parse_bool(row["free_shipping"])
            warranty_period = (row["warranty_period"] or "").strip()
            return_policy = (row["return_policy"] or "").strip()
            specs = load_json(row["specifications_json"], {})
            features = load_json(row["features_json"], [])
            original_category_path = (row["original_category_path"] or "").strip()
            scraping_source = (row["scraper_type"] or "csv").strip()

            platform_product_id = trim_len(derive_platform_product_id(platform_url), 200)

            ecomm_defaults = {
                "platform": platform,
                "platform_product_id": platform_product_id,
                "platform_url": trim_len(platform_url, 1000),
                "in_stock": in_stock,
                "stock_quantity": stock_quantity,
                "stock_status": trim_len(stock_status, 100),
                "shipping_cost": shipping_cost,
                "shipping_time": trim_len(shipping_time, 100),
                "free_shipping": free_shipping,
                "warranty_period": trim_len(warranty_period, 100),
                "return_policy": return_policy,
                "specifications": specs,
                "features": features,
                "average_rating": parse_decimal(row["average_rating"]) and float(parse_decimal(row["average_rating"])) or None,
                "review_count": parse_int(row["review_count"]) or 0,
                "original_category_path": trim_len(original_category_path, 500),
                "scraping_source": scraping_source,
            }

            # Use platform_url as the unique lookup to avoid IntegrityError on duplicates
            # If platform_url is empty, skip this row
            if not platform_url:
                counters["skipped"] += 1
                return

            # Update or create by (platform, platform_product_id) which is unique_together
            try:
                ecomm, created_e = EcommerceProduct.objects.update_or_create(
                    platform=platform,
                    platform_product_id=platform_product_id,
                    defaults={**ecomm_defaults, "product": core},
                )
            except IntegrityError:
                # As a fallback, try to fetch and update manually
                try:
                    ecomm = EcommerceProduct.objects.get(platform=platform, platform_product_id=platform_product_id)
                    for k, v in {**ecomm_defaults, "product": core}.items():
                        setattr(ecomm, k, v)
                    ecomm.save()
                    created_e = False
                except EcommerceProduct.DoesNotExist:
                    ecomm = EcommerceProduct.objects.create(**{**ecomm_defaults, "product": core})
                    created_e = True
            if created_e:
                counters["ecomm_created"] += 1
            else:
                counters["ecomm_updated"] += 1

        # Import rows (optionally in a single rollback-able transaction for dry_run)
        try:
            if dry_run:
                try:
                    with transaction.atomic():
                        for idx, row in enumerate(rows, start=1):
                            import_row(row)
                        # force rollback
                        raise RuntimeError("DRY_RUN")
                except RuntimeError as e:
                    if str(e) != "DRY_RUN":
                        raise
            else:
                for idx, row in enumerate(rows, start=1):
                    try:
                        import_row(row)
                    except Exception as e:
                        counters["skipped"] += 1
                        self.stderr.write(self.style.ERROR(f"Row {idx} error: {e}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Fatal import error: {e}"))

        # Summary
        self.stdout.write(self.style.SUCCESS("\nImport completed"))
        for k, v in counters.items():
            self.stdout.write(f"{k}: {v}")

        self.stdout.write(self.style.SUCCESS("Done."))
