import re
from urllib.parse import urlparse

from django.core.management.base import BaseCommand
from django.db.models import Q

from products.models import CoreProduct


ALLOWED_HOSTS = {
    'cdninstagram.com',
    'scontent.cdninstagram.com',
    'shophive.com',
    'www.shophive.com',
    'd1iv6qgcmtzm6l.cloudfront.net',
    'cdn.shopify.com',
    'alfatah.pk',
    'furniturehub.pk',
    'www.furniturehub.pk',
    'friendshome.pk',
    'www.friendshome.pk',
    'almumtaz.com.pk',
    'www.almumtaz.com.pk',
    'jalalelectronics.com',
    'www.jalalelectronics.com',
    'newtokyo.pk',
    'www.newtokyo.pk',
    'telemart.pk',
    'www.telemart.pk',
}


def is_missing_or_placeholder(url: str | None) -> bool:
    if not url:
        return True
    val = str(url).strip().lower()
    if val in {'', 'null', 'undefined'}:
        return True
    # Common bad placeholders
    if val.startswith('https://:0') or val.startswith('http://:0'):
        return True
    return False


def is_probable_image_url(url: str) -> bool:
    # Heuristic: ends with image extension or known image CDNs that omit extension
    if re.search(r"\.(jpg|jpeg|png|gif|webp|svg)(\?|$)", url, re.IGNORECASE):
        return True
    # Instagram/Shopify/CloudFront often omit extensions but are valid
    if any(h in url for h in ['cdninstagram.com', 'cdn.shopify.com', 'cloudfront.net']):
        return True
    return False


def url_host(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ''


class Command(BaseCommand):
    help = (
        "Diagnose missing/invalid product images for Home & Living.\n"
        "Prints summary counts and top offenders with sample product IDs."
    )

    def add_arguments(self, parser):
        parser.add_argument('--main-category', default='Home & Living', help='Main category to analyze')
        parser.add_argument('--limit', type=int, default=50, help='Sample size to print for problematic products')
        parser.add_argument('--platform', default=None, help='Optional platform name filter (display_name contains)')

    def handle(self, *args, **options):
        main_category = options['main_category']
        limit = options['limit']
        platform = options['platform']

        qs = CoreProduct.objects.filter(is_active=True, category__isnull=False)
        qs = qs.filter(category__main_category=main_category)
        if platform:
            qs = qs.filter(
                Q(platform_type='instagram') & Q(seller__platform__display_name__icontains=platform)
                |
                Q(platform_type='ecommerce') & Q(ecommerce_data__platform__display_name__icontains=platform)
            )

        total = qs.count()
        with_image = qs.exclude(main_image_url__isnull=True).exclude(main_image_url__in=['', 'null', 'undefined']).count()
        missing = total - with_image

        self.stdout.write(self.style.NOTICE(f"Category: {main_category}"))
        self.stdout.write(self.style.NOTICE(f"Total products: {total}"))
        self.stdout.write(self.style.NOTICE(f"With non-empty image: {with_image}"))
        self.stdout.write(self.style.NOTICE(f"Missing/empty image: {missing}"))

        # Drill down into reasons for products lacking usable images
        problems = []
        for p in qs.only('id', 'name', 'main_image_url', 'platform_type')[: min(total, 5000)]:
            url = p.main_image_url
            if is_missing_or_placeholder(url):
                problems.append((p.id, 'empty_or_placeholder', url))
                continue
            u = str(url)
            if not is_probable_image_url(u):
                problems.append((p.id, 'non_image_like_url', u))
                continue
            host = url_host(u)
            # If absolute URL and host not in allowlist, it may be blocked by proxy
            if host and (not any(host == h or host.endswith('.' + h) for h in ALLOWED_HOSTS)):
                problems.append((p.id, 'host_not_allowlisted', host))

        problem_counts = {}
        for _, reason, _ in problems:
            problem_counts[reason] = problem_counts.get(reason, 0) + 1

        self.stdout.write(self.style.WARNING("\nProblem breakdown:"))
        for reason, cnt in sorted(problem_counts.items(), key=lambda x: -x[1]):
            self.stdout.write(f"- {reason}: {cnt}")

        # Sample rows
        if problems:
            self.stdout.write(self.style.WARNING("\nSample problematic products:"))
            for pid, reason, detail in problems[:limit]:
                self.stdout.write(f"id={pid} | {reason} | {detail}")

        # Domains present among valid-looking URLs
        domains = {}
        for p in qs.exclude(main_image_url__isnull=True).exclude(main_image_url__in=['', 'null', 'undefined']).only('main_image_url')[: min(total, 5000)]:
            host = url_host(p.main_image_url)
            if host:
                domains[host] = domains.get(host, 0) + 1

        self.stdout.write(self.style.NOTICE("\nTop image domains:"))
        for host, cnt in sorted(domains.items(), key=lambda x: -x[1])[:20]:
            allow = 'allowed' if any(host == h or host.endswith('.' + h) for h in ALLOWED_HOSTS) else 'NOT-ALLOWED'
            self.stdout.write(f"- {host}: {cnt} ({allow})")

        self.stdout.write(self.style.SUCCESS("\nDiagnosis complete."))


