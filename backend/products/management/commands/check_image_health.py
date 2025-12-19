#!/usr/bin/env python3
"""
Safe, read-only command to check image health across entire database
Reports statistics on missing, broken, and placeholder images
"""

from django.core.management.base import BaseCommand
from django.db.models import Q, Count, Case, When, IntegerField
from products.models import CoreProduct
from urllib.parse import urlparse
import re


class Command(BaseCommand):
    help = 'Safe check of image URL health across entire database (read-only)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed breakdown by category and platform'
        )
        parser.add_argument(
            '--show-samples',
            type=int,
            default=0,
            help='Show N sample products with issues (default: 0)'
        )

    def handle(self, *args, **options):
        detailed = options['detailed']
        show_samples = options['show_samples']

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('IMAGE HEALTH CHECK - ENTIRE DATABASE'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        # Get all active products
        total_products = CoreProduct.objects.filter(is_active=True).count()
        
        self.stdout.write(f'\n📊 Total Active Products: {total_products:,}')

        # 1. Completely missing/null images
        null_or_empty = CoreProduct.objects.filter(
            is_active=True
        ).filter(
            Q(main_image_url__isnull=True) | 
            Q(main_image_url='') |
            Q(main_image_url='null') |
            Q(main_image_url='undefined')
        ).count()

        # 2. Placeholder images (via.placeholder.com, placeholder, default, etc.)
        placeholder_patterns = [
            'placeholder',
            'via.placeholder.com',
            'placehold',
            'default',
            'noimage',
            'no-image',
            'dummy',
            'sample',
            '/logo',
            'favicon',
        ]
        
        placeholder_q = Q()
        for pattern in placeholder_patterns:
            placeholder_q |= Q(main_image_url__icontains=pattern)
        
        placeholder_count = CoreProduct.objects.filter(
            is_active=True
        ).exclude(
            Q(main_image_url__isnull=True) | Q(main_image_url='')
        ).filter(placeholder_q).count()

        # 3. Invalid URL format (starts with https://:0 or http://:0)
        invalid_format = CoreProduct.objects.filter(
            is_active=True
        ).exclude(
            Q(main_image_url__isnull=True) | Q(main_image_url='')
        ).filter(
            Q(main_image_url__startswith='https://:0') |
            Q(main_image_url__startswith='http://:0') |
            Q(main_image_url__startswith=':')
        ).count()

        # 4. Non-image URLs (no common image extension)
        products_with_urls = CoreProduct.objects.filter(
            is_active=True
        ).exclude(
            Q(main_image_url__isnull=True) | Q(main_image_url='')
        ).values_list('id', 'main_image_url')

        non_image_count = 0
        svg_count = 0
        
        for pid, url in products_with_urls:
            if url:
                url_lower = url.lower()
                # SVGs (often logos/icons, not product images)
                if url_lower.endswith('.svg'):
                    svg_count += 1
                # Check if it looks like an image
                elif not self._is_probable_image_url(url):
                    non_image_count += 1

        # 5. Products with valid-looking images
        total_with_issues = null_or_empty + placeholder_count + invalid_format + non_image_count + svg_count
        healthy_images = total_products - total_with_issues

        # Display summary
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('📈 OVERALL SUMMARY'))
        self.stdout.write('=' * 80)
        
        self.stdout.write(f'\n✅ Products with healthy images:     {healthy_images:,} ({self._percentage(healthy_images, total_products)}%)')
        self.stdout.write(f'❌ Products with image issues:       {total_with_issues:,} ({self._percentage(total_with_issues, total_products)}%)')
        
        self.stdout.write('\n' + '-' * 80)
        self.stdout.write(self.style.WARNING('BREAKDOWN BY ISSUE TYPE:'))
        self.stdout.write('-' * 80)
        
        self.stdout.write(f'🚫 Null/Empty URLs:                  {null_or_empty:,} ({self._percentage(null_or_empty, total_products)}%)')
        self.stdout.write(f'🖼️  Placeholder images:               {placeholder_count:,} ({self._percentage(placeholder_count, total_products)}%)')
        self.stdout.write(f'⚠️  Invalid URL format:               {invalid_format:,} ({self._percentage(invalid_format, total_products)}%)')
        self.stdout.write(f'📄 Non-image URLs:                   {non_image_count:,} ({self._percentage(non_image_count, total_products)}%)')
        self.stdout.write(f'🎨 SVG files (logos/icons):          {svg_count:,} ({self._percentage(svg_count, total_products)}%)')

        # Detailed breakdown by category
        if detailed:
            self.stdout.write('\n' + '=' * 80)
            self.stdout.write(self.style.SUCCESS('📂 BREAKDOWN BY CATEGORY'))
            self.stdout.write('=' * 80)
            
            categories = CoreProduct.objects.filter(
                is_active=True,
                category__isnull=False
            ).values(
                'category__main_category'
            ).annotate(
                total=Count('id'),
                missing=Count(Case(
                    When(
                        Q(main_image_url__isnull=True) | 
                        Q(main_image_url='') |
                        Q(main_image_url='null'),
                        then=1
                    ),
                    output_field=IntegerField()
                ))
            ).order_by('-total')

            for cat in categories:
                cat_name = cat['category__main_category'] or 'Uncategorized'
                total = cat['total']
                missing = cat['missing']
                healthy = total - missing
                self.stdout.write(
                    f"\n{cat_name:30} | Total: {total:6,} | "
                    f"Healthy: {healthy:6,} ({self._percentage(healthy, total):5.1f}%) | "
                    f"Missing: {missing:6,} ({self._percentage(missing, total):5.1f}%)"
                )

            # Breakdown by platform
            self.stdout.write('\n' + '=' * 80)
            self.stdout.write(self.style.SUCCESS('🏪 BREAKDOWN BY PLATFORM'))
            self.stdout.write('=' * 80)

            platforms = CoreProduct.objects.filter(
                is_active=True,
                seller__isnull=False
            ).values(
                'seller__display_name'
            ).annotate(
                total=Count('id'),
                missing=Count(Case(
                    When(
                        Q(main_image_url__isnull=True) | 
                        Q(main_image_url='') |
                        Q(main_image_url='null'),
                        then=1
                    ),
                    output_field=IntegerField()
                ))
            ).order_by('-total')[:20]  # Top 20 platforms

            for plat in platforms:
                plat_name = plat['seller__display_name'] or 'Unknown'
                total = plat['total']
                missing = plat['missing']
                healthy = total - missing
                self.stdout.write(
                    f"{plat_name:30} | Total: {total:6,} | "
                    f"Healthy: {healthy:6,} ({self._percentage(healthy, total):5.1f}%) | "
                    f"Missing: {missing:6,} ({self._percentage(missing, total):5.1f}%)"
                )

        # Show sample problematic products
        if show_samples > 0:
            self.stdout.write('\n' + '=' * 80)
            self.stdout.write(self.style.WARNING(f'🔍 SAMPLE PRODUCTS WITH ISSUES (showing {show_samples})'))
            self.stdout.write('=' * 80)

            # Get samples of each type
            samples = {
                'Null/Empty': CoreProduct.objects.filter(
                    is_active=True,
                    main_image_url__isnull=True
                )[:show_samples],
                
                'Placeholder': CoreProduct.objects.filter(
                    is_active=True,
                    main_image_url__icontains='placeholder'
                )[:show_samples],
                
                'Invalid Format': CoreProduct.objects.filter(
                    is_active=True,
                    main_image_url__startswith='https://:0'
                )[:show_samples],
            }

            for issue_type, products in samples.items():
                if products.exists():
                    self.stdout.write(f'\n--- {issue_type} ---')
                    for p in products:
                        self.stdout.write(
                            f"ID: {p.id:6} | {p.name[:60]:60} | "
                            f"URL: {(p.main_image_url or 'NULL')[:50]}"
                        )

        # Final summary
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('✅ CHECK COMPLETE'))
        self.stdout.write('=' * 80)
        
        if total_with_issues > 0:
            self.stdout.write(
                f'\n⚠️  {total_with_issues:,} products need image attention '
                f'({self._percentage(total_with_issues, total_products):.1f}% of database)'
            )
        else:
            self.stdout.write('\n🎉 All products have valid images!')

        self.stdout.write('\n💡 Tip: Use existing commands to fix issues:')
        self.stdout.write('   - python manage.py hydrate_missing_images')
        self.stdout.write('   - python manage.py cleanup_placeholder_images')
        self.stdout.write('   - python manage.py clear_invalid_image_urls\n')

    def _percentage(self, part, total):
        """Calculate percentage safely"""
        if total == 0:
            return 0.0
        return round((part / total) * 100, 1)

    def _is_probable_image_url(self, url):
        """Check if URL likely points to an image"""
        if not url:
            return False
        
        # Check for image extensions
        if re.search(r'\.(jpg|jpeg|png|gif|webp|bmp|tiff)(\?|$)', url, re.IGNORECASE):
            return True
        
        # Known image CDNs that may not have extensions
        image_cdns = [
            'cdninstagram.com',
            'cdn.shopify.com',
            'cloudfront.net',
            'imgur.com',
            'i.imgur.com',
        ]
        
        url_lower = url.lower()
        if any(cdn in url_lower for cdn in image_cdns):
            return True
        
        return False

