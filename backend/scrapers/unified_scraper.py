#!/usr/bin/env python3
"""
Unified Scraper Engine for BuyVaultHub
Simple, fast, config-driven web scraping system
"""

import os
import json
import time
import csv
import logging
import uuid
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import requests
try:
    from .bs_fallback import parse_products as bs_parse_products  # when run as package module
except Exception:
    try:
        from bs_fallback import parse_products as bs_parse_products  # when run as script
    except Exception:
        bs_parse_products = None


class UnifiedScraper:
    """
    Simple, config-driven web scraper
    Loads platform configs from JSON files and scrapes efficiently
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.wait = None
        self.scraped_data = []
        self.logger = self._setup_logger()
        self._requests = requests.Session()
        self._requests.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def _now_str(self) -> str:
        return time.strftime('%Y-%m-%d %H:%M:%S')

    def _ensure_absolute(self, base: str, href: str) -> str:
        return urljoin(base, href) if href else ''

    def _normalize_product_record(self, config: Dict[str, Any], item: Dict[str, Any], listing_page_url: str = '') -> Dict[str, Any]:
        """Ensure required fields exist for CSV importer and frontend compatibility."""
        normalized = dict(item or {})
        normalized['platform_name'] = config.get('platform_name')
        normalized['platform_display_name'] = config.get('platform_display_name')
        normalized['platform_type'] = config.get('platform_type', 'ecommerce')
        normalized['platform_base_url'] = config.get('base_url')
        normalized['scraper_type'] = normalized.get('scraper_type') or 'unified_scraper'
        normalized['seller_username'] = config.get('seller_username', '')
        normalized['seller_display_name'] = config.get('seller_display_name', '')
        normalized['seller_profile_url'] = config.get('seller_profile_url', '')
        normalized['currency'] = normalized.get('currency') or config.get('currency', 'PKR')
        normalized['scraped_at'] = normalized.get('scraped_at') or self._now_str()
        # product name fallback from URL
        name = (normalized.get('product_name') or '').strip()
        if not name:
            try:
                parsed = urlparse(normalized.get('product_url') or '')
                last_seg = [s for s in (parsed.path or '').split('/') if s][-1] if parsed.path else ''
                if last_seg:
                    name = last_seg.replace('-', ' ').replace('_', ' ').strip().title()[:300]
            except Exception:
                name = ''
        normalized['product_name'] = name

        # price normalize to digits
        if 'price' in normalized and normalized['price']:
            normalized['price'] = self._clean_price(str(normalized['price']))

        # image absolute
        if normalized.get('image_url'):
            normalized['image_url'] = self._ensure_absolute(config['base_url'], normalized['image_url'])

        # redirect url
        normalized['product_url'] = self._ensure_absolute(config['base_url'], normalized.get('product_url') or '')
        normalized['redirect_url'] = normalized.get('product_url') or ''

        # listing page
        normalized['listing_page_url'] = listing_page_url or normalized.get('listing_page_url') or ''

        # categorization
        normalized['main_category'] = normalized.get('main_category') or config.get('main_category', 'Electronics')
        subcat = normalized.get('subcategory') or self._detect_subcategory(normalized.get('product_name', ''), config.get('keywords', {}), config.get('synonyms', {})) or config.get('subcategory', '')
        normalized['subcategory'] = subcat
        normalized['sub_category'] = subcat

        # uuid and slug
        import uuid
        normalized['uuid'] = normalized.get('uuid') or str(uuid.uuid4())
        normalized['product_slug'] = normalized.get('product_slug') or self._generate_slug(normalized.get('product_name') or '')

        # defaults expected by importer
        normalized.setdefault('brand_name', '')
        normalized.setdefault('description', '')
        normalized.setdefault('short_description', normalized.get('product_name', '')[:200])
        normalized.setdefault('original_price', '')
        normalized.setdefault('model_number', '')
        normalized.setdefault('sku', '')
        normalized.setdefault('in_stock', True)
        normalized.setdefault('stock_quantity', None)
        normalized.setdefault('stock_status', 'In Stock')
        normalized.setdefault('shipping_cost', '0')
        normalized.setdefault('shipping_time', '')
        normalized.setdefault('free_shipping', False)
        normalized.setdefault('warranty_period', '')
        normalized.setdefault('return_policy', '')
        normalized.setdefault('specifications_json', '{}')
        normalized.setdefault('features_json', '[]')
        normalized.setdefault('average_rating', normalized.get('average_rating'))
        normalized.setdefault('review_count', normalized.get('review_count', 0))
        normalized.setdefault('original_category_path', '')

        return normalized
        
    def _setup_logger(self):
        """Setup logging"""
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)
    
    def _setup_driver(self):
        """Setup Chrome driver with optimized options. Lazily called only when Selenium is needed."""
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument('--headless')
            
            # Performance optimizations
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.add_argument('--disable-notifications')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument('--disable-background-networking')
            chrome_options.add_argument('--disable-component-extensions-with-background-pages')
            # NOTE: Do not disable JS/CSS/images for SPA sites like Telemart
            
            # User agent
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            # Try local ChromeDriver first, then webdriver-manager
            try:
                driver_path = os.path.join(os.path.dirname(__file__), 'chromedriver.exe' if os.name == 'nt' else 'chromedriver')
                if os.path.exists(driver_path):
                    self.driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
                else:
                    raise FileNotFoundError("Local ChromeDriver not found")
            except Exception:
                try:
                    from webdriver_manager.chrome import ChromeDriverManager
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                except ImportError:
                    self.driver = webdriver.Chrome(options=chrome_options)
            
            self.driver.set_page_load_timeout(30)
            self.wait = WebDriverWait(self.driver, 10)
            self.logger.info("Chrome driver setup completed")
            
        except Exception as e:
            self.logger.error(f"Failed to setup Chrome driver: {e}")
            raise
    
    def load_config(self, platform_name: str) -> Dict[str, Any]:
        """Load platform configuration from JSON file"""
        config_path = os.path.join(os.path.dirname(__file__), 'configs', f'{platform_name}.json')
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        self.logger.info(f"Loaded config for {platform_name}")
        return config
    
    def scrape_products(self, platform_name: str, categories: List[str] = None, max_pages: int = 3) -> List[Dict[str, Any]]:
        """
        Main scraping method
        
        Args:
            platform_name: Name of platform (config file name)
            categories: List of categories to scrape (optional, if None, scrapes all categories from config)
            max_pages: Maximum pages to scrape per category
        """
        try:
            # Load platform config
            config = self.load_config(platform_name)
            
            # We setup Selenium lazily only if needed (after API/BS attempts)
            
            # Determine categories to scrape
            if categories is None:
                # Auto-discover all categories from config
                categories = self._discover_categories(config)
                self.logger.info(f"Auto-discovered {len(categories)} categories: {list(categories)}")
            
            # Scrape each category
            all_products = []
            
            for category in categories:
                self.logger.info(f"Scraping category: {str(category)}")
                products = self._scrape_category(config, category, max_pages)
                all_products.extend(products)
                self.logger.info(f"Found {len(products)} products in {str(category)}")
            
            self.scraped_data = all_products
            return all_products
            
        except Exception as e:
            self.logger.error(f"Scraping failed: {e}")
            raise
        finally:
            if self.driver:
                self.driver.quit()
    
    def _scrape_category(self, config: Dict[str, Any], category: str, max_pages: int) -> List[Dict[str, Any]]:
        """Scrape a single category using API → BeautifulSoup → Selenium strategy."""
        products: List[Dict[str, Any]] = []
        base_url = config['base_url']
        settings = config.get('settings', {})
        page_load_delay = int(settings.get('page_load_delay', 2))
        scroll_pause = float(settings.get('scroll_pause', 1))
        timeout_seconds = int(settings.get('timeout', 30))
        
        # Build category URL
        if category == 'default':
            category_url = base_url
        else:
            category_paths = config.get('category_paths', {}).get(category, {})
            if isinstance(category_paths, dict) and category_paths:
                # Get the first subcategory path
                first_subcategory = list(category_paths.values())[0]
                category_url = urljoin(base_url, first_subcategory)
            elif isinstance(category_paths, list) and category_paths:
                # Take the first URL from the list
                category_url = urljoin(base_url, category_paths[0])
            else:
                # Fallback to default pattern
                category_url = urljoin(base_url, f'/category/{str(category)}/')
        
        self.logger.info(f"Scraping URL: {category_url}")
        
        # 1) Try API
        try:
            api_products = self._try_api_fetch(config, category, max_pages)
            if api_products:
                self.logger.info(f"API fetch succeeded: {len(api_products)} products")
                return api_products
        except Exception as e:
            self.logger.info(f"API fetch not available/failed: {e}")

        # 2) Try static BeautifulSoup (skip if force_selenium is true)
        if not settings.get('force_selenium', False):
            try:
                bs_products = self._try_bs_listing(config, category_url)
                if bs_products:
                    self.logger.info(f"BeautifulSoup listing extracted {len(bs_products)} products")
                    return bs_products
            except Exception as e:
                self.logger.info(f"BS listing failed: {e}")

        # 3) Use Selenium (dynamic)
        if settings.get('force_selenium', False):
            self.logger.info("Using Selenium as requested (force_selenium=true)")
        else:
            self.logger.info("Falling back to Selenium for dynamic rendering")
        if not self.driver:
            self._setup_driver()
        
        # Navigate to category page
        self.driver.set_page_load_timeout(timeout_seconds)
        self.wait._timeout = min(timeout_seconds, 60)
        self.driver.get(category_url)
        time.sleep(page_load_delay)
        
        # Optional dynamic handling
        if bool(settings.get('handle_popups', False)) or bool(settings.get('close_ads', False)):
            self._handle_ads_and_popups(config)
        if bool(settings.get('scroll_to_bottom', False)):
            self._progressive_scroll(scroll_pause)
        if bool(settings.get('click_load_more', False)):
            self._click_all_load_more(config)
        if bool(settings.get('wait_for_lazy_images', False)):
            time.sleep(max(1, int(scroll_pause)))
        
        # Scrape pages with Selenium
        for page in range(1, max_pages + 1):
            self.logger.info(f"Scraping page {page}")
            page_products = self._extract_products_from_page(config)
            products.extend(page_products)
            if page < max_pages:
                if not self._go_to_next_page(config):
                    self.logger.info("No more pages found")
                    break
        
        return products

    def _try_api_fetch(self, config: Dict[str, Any], category: str, max_pages: int) -> List[Dict[str, Any]]:
        """Attempt to fetch products via JSON APIs (detected or configured). Supports Shopify-like endpoints and explicit config.api_endpoints.

        Config options:
          - api_endpoints: list of absolute or relative endpoints with {page} placeholder
          - api_parser: 'shopify_products_json' to parse Shopify /products.json
        """
        api_products: List[Dict[str, Any]] = []
        base_url = config['base_url']
        endpoints: List[str] = []

        # 1) Explicit endpoints from config
        for ep in config.get('api_endpoints', []) or []:
            if isinstance(ep, str):
                endpoints.append(ep)

        # 2) Heuristic for Shopify
        # Try common collection products.json; prefer category path when provided
        category_path = config.get('category_paths', {}).get(category, '') if category != 'default' else ''
        if category_path:
            endpoints.append(urljoin(base_url, category_path.strip('/') + '/products.json?page={page}'))
        # Also try top-level products.json
        endpoints.append(urljoin(base_url, 'products.json?page={page}'))

        parser_kind = (config.get('api_parser') or '').lower()
        for ep_template in endpoints:
            for page in range(1, max_pages + 1):
                ep = ep_template.replace('{page}', str(page))
                try:
                    resp = self._requests.get(ep, timeout=15)
                    if resp.status_code != 200 or 'application/json' not in resp.headers.get('Content-Type', ''):
                        # Not JSON; skip to next
                        break
                    data = resp.json()
                    parsed_page = self._parse_api_payload(data, config, parser_kind)
                    if not parsed_page:
                        break
                    api_products.extend(parsed_page)
                except Exception:
                    break

        return api_products

    def _parse_api_payload(self, data: Dict[str, Any], config: Dict[str, Any], parser_kind: str) -> List[Dict[str, Any]]:
        """Parse known API payloads into our normalized product dicts."""
        items: List[Dict[str, Any]] = []
        products = []
        # Shopify /products.json shape
        if parser_kind == 'shopify_products_json' or ('products' in data and isinstance(data['products'], list)):
            products = data.get('products', [])
            for p in products:
                title = (p.get('title') or '').strip()
                handle = (p.get('handle') or '').strip()
                # choose first image
                img = ''
                try:
                    if p.get('images'):
                        img = p['images'][0].get('src') or ''
                except Exception:
                    img = ''
                # choose first variant price
                price = ''
                try:
                    if p.get('variants'):
                        price = str(p['variants'][0].get('price') or '')
                except Exception:
                    price = ''
                product_url = urljoin(config['base_url'], f"products/{handle}") if handle else ''
                item = {
                    'product_name': title,
                    'price': str(price),
                    'image_url': img,
                    'product_url': product_url,
                }
                items.append(self._normalize_product_record(config, item, listing_page_url=urljoin(config['base_url'], 'collections/all')))
        return items

    def _try_bs_listing(self, config: Dict[str, Any], category_url: str) -> List[Dict[str, Any]]:
        """Fetch listing page via requests and parse with BeautifulSoup (fast path)."""
        try:
            resp = self._requests.get(category_url, timeout=20)
            if resp.status_code != 200:
                return []
                
            html = resp.text
            soup = BeautifulSoup(html, 'html.parser')
            selectors = config.get('selectors', {})
            
            # Find product containers
            product_containers = soup.select(selectors.get('product_container', '.product-item, .pickgradient-products'))
            
            if not product_containers:
                self.logger.warning(f"No product containers found with selector: {selectors.get('product_container')}")
                return []
            
            self.logger.info(f"BeautifulSoup found {len(product_containers)} product containers")
            
            products = []
            for container in product_containers:
                try:
                    product = self._extract_product_from_container(container, config, category_url)
                    if product:
                        products.append(product)
                except Exception as e:
                    self.logger.warning(f"Failed to extract product from container: {e}")
                    continue
            
            return products
            
        except Exception as e:
            self.logger.warning(f"BeautifulSoup parsing failed: {e}")
            return []
    
    def _extract_product_from_container(self, container, config: Dict[str, Any], listing_page_url: str) -> Dict[str, Any]:
        """Extract product data from a BeautifulSoup container element."""
        selectors = config.get('selectors', {})
        
        # Extract product name
        name_elem = container.select_one(selectors.get('product_name', 'h5, .product-title'))
        product_name = name_elem.get_text(strip=True) if name_elem else ''
        
        # Extract product URL
        url_elem = container.select_one(selectors.get('product_url', 'a[href*="/collections/"]'))
        product_url = url_elem.get('href', '') if url_elem else ''
        if product_url and not product_url.startswith('http'):
            product_url = urljoin(config['base_url'], product_url)
        
        # Extract price
        price_elem = container.select_one(selectors.get('product_price', '.price, .money'))
        price = price_elem.get_text(strip=True) if price_elem else ''
        
        # Extract image URL
        img_elem = container.select_one(selectors.get('product_image', 'img'))
        image_url = img_elem.get('src', '') or img_elem.get('data-src', '') if img_elem else ''
        if image_url and not image_url.startswith('http'):
            image_url = urljoin(config['base_url'], image_url)
        
        # Extract description
        desc_elem = container.select_one(selectors.get('product_description', '.collection-description'))
        description = desc_elem.get_text(strip=True) if desc_elem else ''
        
        # Extract availability/stock info
        stock_elem = container.select_one(selectors.get('product_availability', '.collection-count'))
        stock_info = stock_elem.get_text(strip=True) if stock_elem else ''
        
        # Create full product record with all required fields
        product = {
            # Platform/Seller info
            'platform_name': config.get('platform_name', 'ascender'),
            'platform_display_name': config.get('platform_display_name', 'Ascender Outdoors'),
            'platform_type': config.get('platform_type', 'ecommerce'),
            'platform_base_url': config.get('base_url', 'https://ascender.pk'),
            'seller_username': config.get('seller_username', 'ascender'),
            'seller_display_name': config.get('seller_display_name', 'Ascender Outdoors'),
            'seller_profile_url': config.get('seller_profile_url', 'https://ascender.pk'),
            
            # Identity
            'uuid': str(uuid.uuid4()),
            'product_slug': self._generate_slug(product_name) if product_name else '',
            'product_name': product_name,
            'brand_name': config.get('brand_name', ''),
            'scraper_type': 'beautifulsoup',
            'scraped_at': datetime.now().isoformat(),
            
            # Pricing/Stock
            'price': price,
            'currency': config.get('currency', 'PKR'),
            'original_price': '',
            'in_stock': True,
            'stock_quantity': '',
            'stock_status': 'in_stock',
            
            # Links/Images
            'product_url': product_url,
            'redirect_url': product_url,
            'image_url': image_url,
            'listing_page_url': listing_page_url,
            
            # Categorization
            'main_category': config.get('main_category', 'Sports & Fitness'),
            'subcategory': config.get('subcategory', 'Outdoor & Adventure'),
            'sub_category': config.get('subcategory', 'Outdoor & Adventure'),
            
            # Meta
            'description': description,
            'short_description': description[:200] if description else '',
            'original_category_path': '',
            'specifications_json': '{}',
            'features_json': '{}',
            
            # Reviews/Misc
            'average_rating': '',
            'review_count': '',
            'model_number': '',
            'sku': '',
            'shipping_cost': '',
            'shipping_time': '',
            'free_shipping': '',
            'warranty_period': '',
            'return_policy': '',
        }
        
        return product
    
    def _extract_products_from_page(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract products from current page"""
        products = []
        selectors = config['selectors']
        settings = config.get('settings', {})
        scroll_pause = float(settings.get('scroll_pause', 1))
        
        used_bs_fallback = False
        try:
            # Wait for product containers
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selectors['product_container'])))
            
            # Find all product containers
            containers = self.driver.find_elements(By.CSS_SELECTOR, selectors['product_container'])
            self.logger.info(f"Found {len(containers)} product containers")
            time.sleep(scroll_pause)
            
            if not containers:
                raise TimeoutException("No containers; trying BS fallback")
            
            for container in containers:
                try:
                    product = self._extract_product_data(container, config)
                    if product:
                        products.append(product)
                except Exception as e:
                    self.logger.warning(f"Failed to extract product: {e}")
                    continue
            
        except TimeoutException:
            self.logger.warning("No product containers found on page; attempting BeautifulSoup fallback")
            try:
                html = self.driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
                selectors = config.get('selectors', {})
                product_containers = soup.select(selectors.get('product_container', '.product-item, .pickgradient-products'))
                
                if product_containers:
                    for container in product_containers:
                        try:
                            product = self._extract_product_from_container(container, config, self.driver.current_url)
                            if product:
                                products.append(product)
                        except Exception as e:
                            self.logger.warning(f"Failed to extract product from container: {e}")
                            continue
                    
                    used_bs_fallback = True
                    self.logger.info(f"BS fallback extracted {len(products)} products")
            except Exception as e:
                self.logger.warning(f"BS fallback failed: {e}")
        
        return products

    def _progressive_scroll(self, pause_seconds: float = 1.0, max_scrolls: int = 10):
        """Scroll down the page progressively to load dynamic content."""
        try:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            for _ in range(max_scrolls):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(pause_seconds)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
        except Exception:
            pass

    def _handle_ads_and_popups(self, config: Dict[str, Any]):
        """Handle ads, popups, and modal dialogs"""
        settings = config.get('settings', {})
        handle_popups = settings.get('handle_popups', False)
        close_ads = settings.get('close_ads', False)
        wait_for_ads = int(settings.get('wait_for_ads', 0))
        
        if not handle_popups and not close_ads:
            return
        
        try:
            # Wait for potential ads to load
            if wait_for_ads > 0:
                time.sleep(wait_for_ads)
            
            # Common ad/popup close selectors (including Plant.Pk specific)
            close_selectors = [
                # Plant.Pk specific Google ads selectors
                '#dismiss-button', '.close-button', '[aria-label="Close ad"]',
                '[id*="ad_position_box"]', '[id*="ad_iframe"]',
                # General selectors
                '.close', '.modal-close', '.popup-close', '.ad-close',
                '.close-button', '.close-btn', '.x-close', '.close-icon',
                '[aria-label="Close"]', '[aria-label="close"]',
                '.fa-times', '.fa-close', '.fa-x', '.fa-remove',
                'button[class*="close"]', 'div[class*="close"]',
                '.overlay-close', '.dialog-close', '.modal-close-btn'
            ]
            
            # Try to close any popups/ads
            for selector in close_selectors:
                try:
                    close_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in close_elements:
                        if element.is_displayed() and element.is_enabled():
                            try:
                                element.click()
                                time.sleep(0.5)
                                self.logger.info(f"Closed popup/ad with selector: {selector}")
                            except:
                                pass
                except:
                    pass
            
            # Handle any remaining overlays
            try:
                # Press Escape key to close any modal dialogs
                from selenium.webdriver.common.keys import Keys
                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(0.5)
            except:
                pass
                
        except Exception as e:
            self.logger.warning(f"Error handling ads/popups: {e}")

    def _click_all_load_more(self, config: Dict[str, Any], max_clicks: int = 5):
        """Click any load more buttons found on the page a few times."""
        selectors = config.get('selectors', {})
        next_sel = selectors.get('next_page')
        if not next_sel:
            return
        for _ in range(max_clicks):
            try:
                button = self.driver.find_element(By.CSS_SELECTOR, next_sel)
                if button and button.is_displayed() and button.is_enabled():
                    button.click()
                    time.sleep(1.5)
                else:
                    break
            except NoSuchElementException:
                break
    
    def _extract_product_data(self, container, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract product data from a single container"""
        selectors = config['selectors']
        
        try:
            # Extract basic product info
            product = {
                'platform_name': config['platform_name'],
                'platform_display_name': config['platform_display_name'],
                'platform_type': config['platform_type'],
                'platform_base_url': config['base_url'],
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'scraper_type': 'unified_scraper'
            }
            
            # Title (with resilient fallback)
            product_name_value = ''
            try:
                title_element = container.find_element(By.CSS_SELECTOR, selectors['product_name'])
                product_name_value = (title_element.text or '').strip()
            except Exception:
                product_name_value = ''
            
            # Price
            try:
                price_element = container.find_element(By.CSS_SELECTOR, selectors['product_price'])
                price_text = price_element.text.strip()
                product['price'] = self._clean_price(price_text)
                product['currency'] = config.get('currency', 'PKR')
            except NoSuchElementException:
                product['price'] = ''
                product['currency'] = config.get('currency', 'PKR')
            
            # Image URL
            try:
                img_element = container.find_element(By.CSS_SELECTOR, selectors['product_image'])
                img_src = img_element.get_attribute('src') or img_element.get_attribute('data-src')
                product['image_url'] = urljoin(config['base_url'], img_src) if img_src else ''
            except NoSuchElementException:
                product['image_url'] = ''
            
            # Product URL (with resilient fallback)
            try:
                if selectors['product_link'] == 'self':
                    url_element = container
                else:
                    url_element = container.find_element(By.CSS_SELECTOR, selectors['product_link'])
                href = url_element.get_attribute('href')
                product['product_url'] = urljoin(config['base_url'], href) if href else ''
            except Exception:
                # Fallback: try to auto-detect a product link using heuristics
                chosen_href = ''
                try:
                    anchors = container.find_elements(By.CSS_SELECTOR, "a[href]")
                    candidates = []
                    for a in anchors:
                        try:
                            h = (a.get_attribute('href') or '').strip()
                            if not h:
                                continue
                            if h.startswith('javascript:') or h.endswith('#'):
                                continue
                            parsed = urlparse(h)
                            path = parsed.path or ''
                            # Skip obvious category/listing paths
                            if any(seg in path.lower() for seg in ['/men', '/women', '/kids', '/new', '/sale', '/accessories', '/collections', '/category', '/search']):
                                # allow deeper product-like paths under these only if depth >= 3
                                if len([s for s in path.split('/') if s]) < 3:
                                    continue
                            depth = len([s for s in path.split('/') if s])
                            # Prefer deeper paths which are more likely product detail pages
                            candidates.append((depth, len(h), h))
                        except Exception:
                            continue
                    if candidates:
                        # sort by depth desc, then href length desc
                        candidates.sort(key=lambda t: (t[0], t[1]), reverse=True)
                        chosen_href = candidates[0][2]
                except Exception:
                    chosen_href = ''
                product['product_url'] = urljoin(config['base_url'], chosen_href) if chosen_href else ''

            # If name still empty, derive from URL slug
            if not product_name_value:
                try:
                    parsed = urlparse(product.get('product_url') or '')
                    last_seg = [s for s in parsed.path.split('/') if s][-1] if parsed.path else ''
                    if last_seg:
                        derived = last_seg.replace('-', ' ').replace('_', ' ').strip()
                        product_name_value = derived.title()[:300]
                except Exception:
                    pass

            product['product_name'] = product_name_value or ''
            
            # Brand (if available)
            try:
                if 'product_brand' in selectors:
                    brand_element = container.find_element(By.CSS_SELECTOR, selectors['product_brand'])
                    product['brand_name'] = brand_element.text.strip()
                else:
                    product['brand_name'] = ''
            except (NoSuchElementException, KeyError):
                product['brand_name'] = ''
            
            # Rating (if available)
            try:
                if 'rating' in selectors:
                    rating_element = container.find_element(By.CSS_SELECTOR, selectors['rating'])
                    rating_text = rating_element.text.strip()
                    # Extract numeric rating (e.g., "4.00" from "4.00 ⭐")
                    import re
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        product['average_rating'] = float(rating_match.group(1))
                    else:
                        product['average_rating'] = None
                else:
                    product['average_rating'] = None
            except (NoSuchElementException, ValueError):
                product['average_rating'] = None
            
            # Review Count (if available)
            try:
                if 'review_count' in selectors:
                    review_element = container.find_element(By.CSS_SELECTOR, selectors['review_count'])
                    review_text = review_element.text.strip()
                    # Extract numeric count (e.g., "15" from "(15)")
                    import re
                    count_match = re.search(r'\((\d+)\)', review_text)
                    if count_match:
                        product['review_count'] = int(count_match.group(1))
                    else:
                        product['review_count'] = 0
                else:
                    product['review_count'] = 0
            except (NoSuchElementException, ValueError):
                product['review_count'] = 0
            
            # Generate UUID for product
            import uuid
            product['uuid'] = str(uuid.uuid4())
            
            # Generate slug
            product['product_slug'] = self._generate_slug(product['product_name'])
            
            # Set default values
            product.update({
                'seller_username': config.get('seller_username', ''),
                'seller_display_name': config.get('seller_display_name', ''),
                'seller_profile_url': config.get('seller_profile_url', ''),
                'description': '',
                'short_description': product['product_name'][:200],
                'original_price': '',
                'main_category': config.get('main_category', 'Electronics'),
                'subcategory': self._detect_subcategory(product['product_name'], config.get('keywords', {}), config.get('synonyms', {})) or config.get('subcategory', 'Electronics'),
                'sub_category': None,  # duplicate for frontend compatibility
                'model_number': '',
                'sku': '',
                'listing_page_url': self.driver.current_url if self.driver else '',
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
                'average_rating': product.get('average_rating'),
                'review_count': product.get('review_count', 0),
                'original_category_path': '',
            })

            # Normalize required fields
            product = self._normalize_product_record(config, product, listing_page_url=product.get('listing_page_url') or '')
            
            return product
            
        except Exception as e:
            self.logger.warning(f"Failed to extract product data: {e}")
            return None
    
    def _clean_price(self, price_text: str) -> str:
        """Clean and normalize price text"""
        import re
        
        # Extract the largest number from the price text (usually the current price)
        numbers = re.findall(r'[\d,]+', price_text)
        
        if not numbers:
            return ''
        
        # Get the largest number (current price is usually larger)
        largest_number = max(numbers, key=lambda x: int(x.replace(',', '')))
        
        # Clean the number
        cleaned = largest_number.replace(',', '')
        
        # Handle PKR format (e.g., "11 PKR" -> "11000")
        if 'PKR' in price_text.upper() and cleaned.isdigit():
            if int(cleaned) < 1000:  # Likely in thousands format
                cleaned = str(int(cleaned) * 1000)
        
        return cleaned
    
    def _detect_subcategory(self, product_name: str, keywords: Dict[str, List[str]], synonyms: Dict[str, List[str]] = None) -> Optional[str]:
        """Detect subcategory using keyword matching with simple stemming, synonyms, and case-insensitive partials."""
        if not keywords:
            return None
            
        def normalize_token(t: str) -> str:
            t = t.lower().strip()
            t = t.replace('-', ' ').replace('_', ' ')
            # naive plural handling
            if t.endswith('ies'):
                t = t[:-3] + 'y'
            elif t.endswith('es') and len(t) > 3:
                t = t[:-2]
            elif t.endswith('s') and len(t) > 2:
                t = t[:-1]
            return t

        syn_map = {normalize_token(k): [normalize_token(v) for v in vs] for k, vs in (synonyms or {}).items()}

        name_norm = normalize_token(product_name)

        category_scores: Dict[str, int] = {}
        for subcat, kw_list in keywords.items():
            score = 0
            for kw in kw_list:
                base_kw = normalize_token(kw)
                forms = set([base_kw] + syn_map.get(base_kw, []))
                # partial contains matching
                for form in forms:
                    if form and form in name_norm:
                        score += 1
                        break
            if score > 0:
                category_scores[subcat] = score
        
        if category_scores:
            return max(category_scores.items(), key=lambda x: x[1])[0]
        return None
    
    def _discover_categories(self, config: Dict[str, Any]) -> List[str]:
        """Auto-discover categories from config file"""
        categories = []
        
        # Get all category paths from config
        category_paths = config.get('category_paths', {})
        
        # Add all categories except 'default'
        for category_name in category_paths.keys():
            if category_name != 'default':
                categories.append(category_name)
        
        # If no categories found, add default
        if not categories:
            categories = ['default']
            
        return categories
    
    def _generate_slug(self, text: str) -> str:
        """Generate URL-friendly slug"""
        import re
        
        # Convert to lowercase and replace spaces with hyphens
        slug = re.sub(r'[^\w\s-]', '', text.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')
    
    def _go_to_next_page(self, config: Dict[str, Any]) -> bool:
        """Navigate to next page"""
        selectors = config['selectors']
        
        try:
            next_button = self.driver.find_element(By.CSS_SELECTOR, selectors['next_page'])
            if next_button.is_enabled():
                next_button.click()
                time.sleep(2)
                return True
        except NoSuchElementException:
            pass
        
        return False
    
    def export_to_csv(self, filename: str = None) -> str:
        """Export scraped data to CSV"""
        if not self.scraped_data:
            raise ValueError("No data to export")
        
        if not filename:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = f"scraped_products_{timestamp}.csv"
        
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        # Get all unique keys
        all_keys = set()
        for product in self.scraped_data:
            all_keys.update(product.keys())
        
        # Write CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=sorted(all_keys))
            writer.writeheader()
            writer.writerows(self.scraped_data)
        
        self.logger.info(f"Exported {len(self.scraped_data)} products to {filepath}")
        return filepath


def main():
    """CLI interface for unified scraper"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Unified Scraper Engine')
    parser.add_argument('--platform', required=True, help='Platform name (config file name)')
    parser.add_argument('--categories', nargs='+', help='Categories to scrape')
    parser.add_argument('--max-pages', type=int, default=3, help='Maximum pages per category')
    parser.add_argument('--headless', action='store_true', default=True, help='Run in headless mode')
    parser.add_argument('--output', help='Output CSV filename')
    parser.add_argument('--preview-count', type=int, default=10, help='Preview N items before full run')
    parser.add_argument('--no-interactive', action='store_true', help='Disable confirmation prompt and run full scrape')
    
    args = parser.parse_args()
    
    # Create scraper
    scraper = UnifiedScraper(headless=args.headless)
    
    try:
        # Load config to discover categories for preview
        config = scraper.load_config(args.platform)
        categories = args.categories or scraper._discover_categories(config)

        # Preview: scrape minimal (first category, 1 page) until preview-count reached using API→BS→Selenium
        preview_items: List[Dict[str, Any]] = []
        for cat in categories:
            items = scraper._scrape_category(config, cat, max_pages=1)
            preview_items.extend(items)
            if len(preview_items) >= args.preview_count:
                break
        preview_items = preview_items[: args.preview_count]
        scraper.scraped_data = preview_items
        # Ensure redirect_url present
        for it in scraper.scraped_data:
            it['redirect_url'] = it.get('product_url') or it.get('redirect_url') or ''
            if 'sub_category' not in it:
                it['sub_category'] = it.get('subcategory')

        # Show preview
        print(f"🔎 Preview ({len(preview_items)} items):")
        for i, it in enumerate(preview_items, 1):
            print(json.dumps({
                'name': it.get('product_name'),
                'price': it.get('price'),
                'subcategory': it.get('subcategory'),
                'redirect_url': it.get('redirect_url')
            }, ensure_ascii=False))

        proceed = 'y'
        if not args.no_interactive:
            proceed = input("Do you want to continue scraping the full dataset? (y/n) ").strip().lower()

        if proceed != 'y':
            # Export only preview to make it useful, but do not continue
            csv_file = scraper.export_to_csv(args.output)
            print(f"🛑 Stopped after preview. Exported preview to: {csv_file}")
            return 0

        # Full scrape
        products = []
        for cat in categories:
            products.extend(scraper._scrape_category(config, cat, max_pages=args.max_pages))
        scraper.scraped_data = products
        
        # Export to CSV
        csv_file = scraper.export_to_csv(args.output)
        
        print(f"✅ Scraping completed!")
        print(f"📊 Found {len(products)} products")
        print(f"💾 Exported to: {csv_file}")
        
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
