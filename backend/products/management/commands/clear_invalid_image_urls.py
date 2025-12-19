from django.core.management.base import BaseCommand
from django.db.models import Q

from products.models import CoreProduct


class Command(BaseCommand):
    help = "Clear invalid product image URLs (e.g., data: placeholders) so hydrator can refill them."

    def add_arguments(self, parser):
        parser.add_argument('--main-category', default=None, help='Optional main category filter')
        parser.add_argument('--platform', default=None, help='Optional platform display name filter')

    def handle(self, *args, **options):
        main_category = options['main_category']
        platform = options['platform']

        qs = CoreProduct.objects.filter(is_active=True)

        if main_category:
            qs = qs.filter(category__main_category=main_category)

        if platform:
            qs = qs.filter(
                Q(platform_type='instagram') & Q(seller__platform__display_name__icontains=platform)
                |
                Q(platform_type='ecommerce') & Q(ecommerce_data__platform__display_name__icontains=platform)
            )

        targets = qs.filter(
            Q(main_image_url__istartswith='data:') | Q(main_image_url__iexact='null') | Q(main_image_url__iexact='undefined')
        )

        count = targets.count()
        self.stdout.write(self.style.NOTICE(f"Found {count} products with invalid image URLs"))

        updated = 0
        for p in targets.only('id', 'main_image_url'):
            p.main_image_url = ''
            p.save(update_fields=['main_image_url'])
            updated += 1

        self.stdout.write(self.style.SUCCESS(f"Cleared invalid image URLs on {updated} products"))


