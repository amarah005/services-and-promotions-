#!/usr/bin/env python3
"""
Validation utilities for BuyVaultHub Scrapers
Ensures data quality and prevents common scraping issues
"""

import re
from typing import Dict, Any, List, Optional
from decimal import Decimal, InvalidOperation

class DataValidator:
    """Validates scraped product data for quality and consistency"""
    
    # Price validation patterns
    PRICE_PATTERNS = [
        r'[\d,]+\.?\d*\s*(?:PKR|Rs|Rs\.|rupees?)',  # PKR formats
        r'[\d,]+\.?\d*\s*(?:USD|\$|dollars?)',      # USD formats
        r'[\d,]+\.?\d*',                            # Plain numbers
    ]
    
    # URL validation patterns
    VALID_URL_PATTERNS = [
        r'https?://[^\s/$.?#].[^\s]*',              # Basic HTTP/HTTPS URLs
        r'/[^/]*product[^/]*/',                     # Product page patterns
        r'/[^/]*item[^/]*/',                        # Item page patterns
    ]
    
    # Invalid price indicators (too low/high)
    MIN_REALISTIC_PRICES = {
        'electronics': 100,      # Minimum realistic price for electronics
        'mobile': 5000,          # Minimum realistic price for mobiles
        'laptop': 20000,         # Minimum realistic price for laptops
        'ac': 50000,             # Minimum realistic price for ACs
        'refrigerator': 30000,   # Minimum realistic price for refrigerators
    }
    
    MAX_REALISTIC_PRICES = {
        'electronics': 5000000,  # Maximum realistic price
        'mobile': 500000,        # Maximum realistic price for mobiles
        'laptop': 1000000,       # Maximum realistic price for laptops
        'ac': 500000,            # Maximum realistic price for ACs
        'refrigerator': 800000,  # Maximum realistic price for refrigerators
    }
    
    @classmethod
    def validate_price(cls, price_str: str, category: str = 'electronics') -> Dict[str, Any]:
        """
        Validate and clean price data
        
        Returns:
            Dict with 'is_valid', 'cleaned_price', 'currency', 'warnings'
        """
        result = {
            'is_valid': False,
            'cleaned_price': None,
            'currency': 'PKR',
            'warnings': []
        }
        
        if not price_str or not str(price_str).strip():
            result['warnings'].append('Empty price')
            return result
        
        price_str = str(price_str).strip()
        
        # Check for obviously wrong prices (like single digits)
        if re.match(r'^\d{1,2}$', price_str):
            result['warnings'].append(f'Price "{price_str}" seems too low for {category}')
            return result
        
        # Extract price and currency
        for pattern in cls.PRICE_PATTERNS:
            match = re.search(pattern, price_str, re.IGNORECASE)
            if match:
                price_part = match.group(0)
                
                # Extract currency
                if re.search(r'PKR|Rs|rupees?', price_part, re.IGNORECASE):
                    result['currency'] = 'PKR'
                elif re.search(r'USD|\$|dollars?', price_part, re.IGNORECASE):
                    result['currency'] = 'USD'
                
                # Extract numeric value
                numeric_match = re.search(r'[\d,]+\.?\d*', price_part)
                if numeric_match:
                    try:
                        # Clean and parse
                        numeric_str = numeric_match.group(0).replace(',', '')
                        price = Decimal(numeric_str)
                        
                        # Convert PKR format (e.g., "11 PKR" -> 11000)
                        if 'PKR' in price_part.upper() and price < 1000:
                            price = price * 1000
                            result['warnings'].append(f'Converted "{price_str}" to {price} (PKR format)')
                        
                        # Validate realistic range
                        min_price = cls.MIN_REALISTIC_PRICES.get(category, 100)
                        max_price = cls.MAX_REALISTIC_PRICES.get(category, 1000000)
                        
                        if price < min_price:
                            result['warnings'].append(f'Price {price} seems too low for {category} (min: {min_price})')
                        elif price > max_price:
                            result['warnings'].append(f'Price {price} seems too high for {category} (max: {max_price})')
                        
                        result['is_valid'] = True
                        result['cleaned_price'] = float(price)
                        
                    except (InvalidOperation, ValueError):
                        result['warnings'].append(f'Could not parse price: {price_str}')
                
                break
        
        if not result['is_valid']:
            result['warnings'].append(f'No valid price pattern found in: {price_str}')
        
        return result
    
    @classmethod
    def validate_url(cls, url: str) -> Dict[str, Any]:
        """Validate product URL"""
        result = {
            'is_valid': False,
            'is_product_url': False,
            'warnings': []
        }
        
        if not url or not str(url).strip():
            result['warnings'].append('Empty URL')
            return result
        
        url = str(url).strip()
        
        # Check basic URL format
        if not re.match(cls.VALID_URL_PATTERNS[0], url):
            result['warnings'].append(f'Invalid URL format: {url}')
            return result
        
        result['is_valid'] = True
        
        # Check if it's a product URL
        product_indicators = ['/product/', '/item/', '/p/', '/shop/']
        if any(indicator in url.lower() for indicator in product_indicators):
            result['is_product_url'] = True
        elif '/category/' in url.lower() or '/cat/' in url.lower():
            result['warnings'].append('URL appears to be a category page, not a product page')
        
        return result
    
    @classmethod
    def validate_product_data(cls, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate complete product data"""
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'cleaned_data': product_data.copy()
        }
        
        # Validate required fields
        required_fields = ['name', 'price', 'url']
        for field in required_fields:
            if not product_data.get(field):
                result['errors'].append(f'Missing required field: {field}')
                result['is_valid'] = False
        
        # Validate price
        if product_data.get('price'):
            category = product_data.get('category', 'electronics')
            price_validation = cls.validate_price(product_data['price'], category)
            result['warnings'].extend(price_validation['warnings'])
            
            if price_validation['is_valid']:
                result['cleaned_data']['price'] = price_validation['cleaned_price']
                result['cleaned_data']['currency'] = price_validation['currency']
            else:
                result['errors'].append('Invalid price data')
                result['is_valid'] = False
        
        # Validate URL
        if product_data.get('url'):
            url_validation = cls.validate_url(product_data['url'])
            result['warnings'].extend(url_validation['warnings'])
            
            if not url_validation['is_valid']:
                result['errors'].append('Invalid URL data')
                result['is_valid'] = False
            elif not url_validation['is_product_url']:
                result['warnings'].append('URL may not be a product page')
        
        # Validate name length
        name = product_data.get('name', '')
        if len(name) < 3:
            result['warnings'].append('Product name too short')
        elif len(name) > 300:
            result['warnings'].append('Product name too long')
            result['cleaned_data']['name'] = name[:300]
        
        return result

def validate_scraped_data(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate a batch of scraped products"""
    validator = DataValidator()
    
    results = {
        'total_products': len(products),
        'valid_products': 0,
        'invalid_products': 0,
        'warnings_count': 0,
        'common_issues': {},
        'cleaned_products': []
    }
    
    issue_counts = {}
    
    for product in products:
        validation = validator.validate_product_data(product)
        
        if validation['is_valid']:
            results['valid_products'] += 1
            results['cleaned_products'].append(validation['cleaned_data'])
        else:
            results['invalid_products'] += 1
        
        results['warnings_count'] += len(validation['warnings'])
        
        # Count common issues
        for error in validation['errors']:
            issue_counts[error] = issue_counts.get(error, 0) + 1
        for warning in validation['warnings']:
            issue_counts[warning] = issue_counts.get(warning, 0) + 1
    
    results['common_issues'] = dict(sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:10])
    
    return results
