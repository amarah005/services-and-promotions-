"""
BeautifulSoup fallback parser for product listing pages.
Used when Selenium is slow, times out, or returns 0 containers.
"""

from typing import Dict, List, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup


def _derive_name_from_url(href: str) -> str:
    try:
        path = urlparse(href).path
        segs = [s for s in path.split('/') if s]
        if not segs:
            return ''
        last = segs[-1]
        return last.replace('-', ' ').replace('_', ' ').strip().title()[:300]
    except Exception:
        return ''


def parse_products(html: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse products from HTML using CSS selectors from config.

    Expected config keys:
      - base_url
      - selectors: product_container, title, price, image, url, brand (optional)
    """
    products: List[Dict[str, Any]] = []
    if not html:
        return products

    soup = BeautifulSoup(html, 'html.parser')
    selectors = config.get('selectors', {})
    container_sel = selectors.get('product_container') or ''

    containers = soup.select(container_sel) if container_sel else []
    if not containers:
        return products

    for el in containers:
        try:
            product: Dict[str, Any] = {
                'platform_name': config.get('platform_name', ''),
                'platform_display_name': config.get('platform_display_name', ''),
                'platform_type': config.get('platform_type', 'ecommerce'),
                'platform_base_url': config.get('base_url', ''),
                'scraper_type': 'bs_fallback',
            }

            # Title
            name_val = ''
            title_sel = selectors.get('title')
            if title_sel:
                tnode = el.select_one(title_sel)
                name_val = (tnode.get_text(strip=True) if tnode else '')

            # URL
            url_val = ''
            url_sel = selectors.get('url')
            if url_sel:
                unode = el.select_one(url_sel)
                if unode and unode.has_attr('href'):
                    url_val = unode['href']
            if not url_val:
                # heuristics: choose deepest anchor
                anchors = el.select('a[href]')
                candidates = []
                for a in anchors:
                    href = a.get('href', '')
                    if not href:
                        continue
                    if href.startswith('javascript:') or href.endswith('#'):
                        continue
                    depth = len([s for s in urlparse(href).path.split('/') if s])
                    candidates.append((depth, len(href), href))
                if candidates:
                    candidates.sort(key=lambda t: (t[0], t[1]), reverse=True)
                    url_val = candidates[0][2]

            product['product_url'] = urljoin(config.get('base_url', ''), url_val) if url_val else ''

            # Derive name if missing
            if not name_val and product['product_url']:
                name_val = _derive_name_from_url(product['product_url'])
            product['product_name'] = name_val or ''

            # Price
            price_val = ''
            price_sel = selectors.get('price')
            if price_sel:
                pnode = el.select_one(price_sel)
                price_val = (pnode.get_text(strip=True) if pnode else '')
            product['price'] = price_val
            product['currency'] = config.get('currency', 'PKR')

            # Image
            image_val = ''
            img_sel = selectors.get('image')
            if img_sel:
                inode = el.select_one(img_sel)
                if inode:
                    image_val = inode.get('src') or inode.get('data-src') or ''
            product['image_url'] = urljoin(config.get('base_url', ''), image_val) if image_val else ''

            # Brand (optional)
            brand_sel = selectors.get('brand')
            if brand_sel:
                bnode = el.select_one(brand_sel)
                product['brand_name'] = (bnode.get_text(strip=True) if bnode else '')
            else:
                product['brand_name'] = ''

            # Defaults needed by importer
            product.update({
                'original_price': '',
                'main_category': config.get('main_category', 'Sports & Fitness'),
                'subcategory': config.get('subcategory', ''),
                'description': '',
                'short_description': (name_val or '')[:200],
                'listing_page_url': '',
                'in_stock': True,
                'stock_quantity': None,
                'stock_status': 'In Stock',
                'shipping_cost': '0',
                'shipping_time': '',
                'free_shipping': False,
                'warranty_period': '',
                'return_policy': '',
                'specifications_json': '{}',
                'features_json': '[]',
                'average_rating': None,
                'review_count': 0,
                'original_category_path': '',
            })

            products.append(product)
        except Exception:
            continue

    return products


