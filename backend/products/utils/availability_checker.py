#!/usr/bin/env python3
"""
Product Availability Checker
Checks if a product still exists on its source platform
"""

import requests
import logging
from urllib.parse import urlparse
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


class ProductAvailabilityChecker:
    """Check if products are still available on their source platforms"""
    
    # Configuration
    REQUEST_TIMEOUT = 10  # seconds
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    
    # Platform-specific unavailability indicators
    UNAVAILABILITY_PATTERNS = {
        'sehgalmotors.pk': {
            'status_codes': [404],
            'url_redirects': ['/', '/collections/', '/collections/all'],
            'content_keywords': ['page not found', 'product not found', 'no longer available'],
        },
        'friendshome.pk': {
            'status_codes': [404],
            'url_redirects': ['/', '/collections/'],
            'content_keywords': ['page not found', 'product not found'],
        },
        'newtokyo.pk': {
            'status_codes': [404],
            'url_redirects': ['/', '/collections/'],
            'content_keywords': ['page not found', 'product not found'],
        },
        'www.alfatah.com.pk': {
            'status_codes': [404],
            'url_redirects': ['/', '/products/'],
            'content_keywords': ['not found', 'product not available'],
        },
        'www.shophive.com': {
            'status_codes': [404],
            'url_redirects': ['/'],
            'content_keywords': ['page not found', '404'],
        },
        # Default pattern for other platforms
        'default': {
            'status_codes': [404, 410],  # 410 = Gone
            'url_redirects': ['/', '/home', '/products'],
            'content_keywords': ['not found', 'page not found', 'product not found', 
                               'no longer available', 'removed', 'discontinued'],
        }
    }
    
    def __init__(self, product):
        """
        Initialize checker for a specific product
        
        Args:
            product: CoreProduct instance
        """
        self.product = product
        self.platform_url = self._get_platform_url()
        self.domain = self._extract_domain()
        
    def _get_platform_url(self):
        """Get the source platform URL for the product"""
        # For ecommerce products, use the platform_url from EcommerceProduct
        if self.product.platform_type == 'ecommerce':
            try:
                return self.product.ecommerce_data.platform_url
            except:
                pass
        
        # For Instagram products
        if self.product.platform_type == 'instagram':
            try:
                return self.product.instagram_data.post_url
            except:
                pass
        
        return None
    
    def _extract_domain(self):
        """Extract domain from platform URL"""
        if not self.platform_url:
            return None
        try:
            parsed = urlparse(self.platform_url)
            return parsed.netloc.lower()
        except:
            return None
    
    def _get_platform_patterns(self):
        """Get unavailability patterns for the product's platform"""
        if self.domain in self.UNAVAILABILITY_PATTERNS:
            return self.UNAVAILABILITY_PATTERNS[self.domain]
        return self.UNAVAILABILITY_PATTERNS['default']
    
    def check_availability(self):
        """
        Check if product is still available on source platform
        
        Returns:
            dict: {
                'available': bool,
                'status': str ('active', 'unavailable', 'error'),
                'status_code': int or None,
                'reason': str,
                'checked_at': datetime
            }
        """
        result = {
            'available': None,
            'status': 'error',
            'status_code': None,
            'reason': 'Unknown error',
            'checked_at': timezone.now()
        }
        
        # Validate we have a URL to check
        if not self.platform_url:
            result['status'] = 'error'
            result['reason'] = 'No source platform URL available for this product'
            return result
        
        logger.info(f"Checking availability for product {self.product.id}: {self.platform_url}")
        
        try:
            # Make request to product page
            headers = {'User-Agent': self.USER_AGENT}
            response = requests.get(
                self.platform_url,
                headers=headers,
                timeout=self.REQUEST_TIMEOUT,
                allow_redirects=True
            )
            
            result['status_code'] = response.status_code
            patterns = self._get_platform_patterns()
            
            # Check 1: HTTP status code
            if response.status_code in patterns['status_codes']:
                result['available'] = False
                result['status'] = 'unavailable'
                result['reason'] = f'Product page returns {response.status_code} error'
                logger.warning(f"Product {self.product.id} unavailable: HTTP {response.status_code}")
                return result
            
            # Check 2: URL redirect (redirected to homepage/listing page)
            if response.url != self.platform_url:
                final_path = urlparse(response.url).path.rstrip('/')
                if any(final_path == redirect.rstrip('/') for redirect in patterns['url_redirects']):
                    result['available'] = False
                    result['status'] = 'unavailable'
                    result['reason'] = 'Product page redirects to homepage (product removed)'
                    logger.warning(f"Product {self.product.id} unavailable: Redirected to {response.url}")
                    return result
            
            # Check 3: Page content analysis
            if response.status_code == 200:
                content_lower = response.text.lower()
                for keyword in patterns['content_keywords']:
                    if keyword in content_lower:
                        result['available'] = False
                        result['status'] = 'unavailable'
                        result['reason'] = f'Product page shows "{keyword}" message'
                        logger.warning(f"Product {self.product.id} unavailable: Found '{keyword}' in content")
                        return result
            
            # If we got here, product appears to be available
            result['available'] = True
            result['status'] = 'active'
            result['reason'] = 'Product page is accessible and appears valid'
            logger.info(f"Product {self.product.id} is available on platform")
            return result
            
        except requests.exceptions.Timeout:
            result['status'] = 'error'
            result['reason'] = f'Request timed out after {self.REQUEST_TIMEOUT} seconds'
            logger.error(f"Timeout checking product {self.product.id}")
            return result
            
        except requests.exceptions.ConnectionError:
            result['status'] = 'error'
            result['reason'] = 'Could not connect to platform server'
            logger.error(f"Connection error checking product {self.product.id}")
            return result
            
        except Exception as e:
            result['status'] = 'error'
            result['reason'] = f'Unexpected error: {str(e)[:100]}'
            logger.error(f"Error checking product {self.product.id}: {str(e)}")
            return result
    
    def should_check_now(self, force=False):
        """
        Determine if we should check availability now
        
        Args:
            force: If True, always check regardless of last check time
        
        Returns:
            bool: True if we should check now
        """
        if force:
            return True
        
        # Always check if never checked before
        if not self.product.last_availability_check:
            return True
        
        # Check if enough time has passed since last check (24 hours)
        time_since_check = timezone.now() - self.product.last_availability_check
        if time_since_check > timedelta(hours=24):
            return True
        
        # If status is unavailable or error, recheck more frequently (6 hours)
        if self.product.availability_status in ['unavailable', 'error']:
            if time_since_check > timedelta(hours=6):
                return True
        
        return False
    
    def update_product_status(self, check_result):
        """
        Update product database fields based on availability check
        
        Args:
            check_result: dict returned from check_availability()
        """
        from products.models import CoreProduct
        
        # Update availability status
        self.product.availability_status = check_result['status']
        self.product.last_availability_check = check_result['checked_at']
        
        # Handle consecutive failures
        if check_result['status'] == 'unavailable':
            self.product.consecutive_failures += 1
            
            # Set user-friendly message
            platform_name = self.product.seller.display_name if self.product.seller else "the platform"
            self.product.availability_check_message = (
                f"⚠️ This product is no longer available on {platform_name}. "
                f"We're working to update our catalog. Please check back soon or explore similar products."
            )
            
            # Mark as inactive after 3 consecutive failures
            if self.product.consecutive_failures >= 3:
                self.product.is_active = False
                logger.warning(f"Product {self.product.id} marked as INACTIVE after 3 failed checks")
                
        elif check_result['status'] == 'active':
            # Reset failures counter if product is back
            self.product.consecutive_failures = 0
            self.product.availability_check_message = ''
            
            # Reactivate if was inactive due to availability
            if not self.product.is_active and self.product.availability_status == 'unavailable':
                self.product.is_active = True
                logger.info(f"Product {self.product.id} REACTIVATED - now available again")
        
        # Save changes
        self.product.save(update_fields=[
            'availability_status',
            'last_availability_check',
            'consecutive_failures',
            'availability_check_message',
            'is_active'
        ])
        
        logger.info(f"Updated product {self.product.id} availability: {check_result['status']}")


def check_product_availability(product, force=False, update_db=True):
    """
    Convenience function to check product availability
    
    Args:
        product: CoreProduct instance
        force: Force check even if recently checked
        update_db: Update database with results
    
    Returns:
        dict: Availability check result
    """
    checker = ProductAvailabilityChecker(product)
    
    # Check if we should actually check now
    if not checker.should_check_now(force=force):
        return {
            'available': None,
            'status': product.availability_status,
            'reason': 'Skipped - recently checked',
            'checked_at': product.last_availability_check
        }
    
    # Perform the check
    result = checker.check_availability()
    
    # Update database if requested
    if update_db:
        checker.update_product_status(result)
    
    return result

