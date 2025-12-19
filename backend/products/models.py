#!/usr/bin/env python3
"""
OPTIMIZED DJANGO MODELS FOR E-COMMERCE SCRAPING
Professional database design with normalization, indexing, and performance optimization
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
import uuid
import json

# ============================================================================
# CORE ENTITIES (Normalized)
# ============================================================================

class Platform(models.Model):
    """Normalized platform entities (Instagram, E-commerce sites, etc.)"""
    name = models.CharField(max_length=50, unique=True, db_index=True)
    display_name = models.CharField(max_length=100)
    platform_type = models.CharField(
        max_length=20,
        choices=[
            ('social', 'Social Media'),
            ('ecommerce', 'E-commerce'),
            ('marketplace', 'Marketplace'),
        ],
        db_index=True
    )
    base_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    scraping_enabled = models.BooleanField(default=True)
    
    # Scraping configuration
    rate_limit_per_hour = models.IntegerField(default=100)
    requires_authentication = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['platform_type', 'is_active']),
            models.Index(fields=['name', 'platform_type']),
        ]
        ordering = ['display_name']
    
    def __str__(self):
        return f"{self.display_name} ({self.platform_type})"

class Brand(models.Model):
    """Normalized brand entities"""
    name = models.CharField(max_length=100, unique=True, db_index=True)
    display_name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=110, unique=True, db_index=True)
    logo_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    
    # Brand metadata
    country_of_origin = models.CharField(max_length=100, blank=True)
    founded_year = models.IntegerField(null=True, blank=True)
    is_verified = models.BooleanField(default=False, db_index=True)
    
    # SEO and search
    search_vector = SearchVectorField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['name', 'is_verified']),
            models.Index(fields=['slug']),
            GinIndex(fields=['search_vector']),  # Full-text search
        ]
        ordering = ['display_name']
    
    def __str__(self):
        return self.display_name

class Seller(models.Model):
    """Normalized seller entities (Instagram accounts, store owners, etc.)"""
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, related_name='sellers')
    username = models.CharField(max_length=200, db_index=True)
    display_name = models.CharField(max_length=250, blank=True)
    
    # Contact information
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_whatsapp = models.CharField(max_length=20, blank=True)
    contact_address = models.TextField(blank=True)
    
    # Social/Platform specific
    profile_url = models.URLField(blank=True)
    profile_image_url = models.URLField(blank=True)
    follower_count = models.IntegerField(default=0, db_index=True)
    verified = models.BooleanField(default=False, db_index=True)
    
    # Business information
    business_type = models.CharField(
        max_length=20,
        choices=[
            ('individual', 'Individual'),
            ('business', 'Business'),
            ('brand', 'Brand'),
            ('reseller', 'Reseller'),
        ],
        default='individual',
        db_index=True
    )
    
    # Quality metrics
    response_rate = models.FloatField(null=True, blank=True)
    average_rating = models.FloatField(null=True, blank=True, db_index=True)
    total_products = models.IntegerField(default=0, db_index=True)
    
    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    last_active = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['platform', 'username']
        indexes = [
            models.Index(fields=['platform', 'username']),
            models.Index(fields=['platform', 'verified', 'is_active']),
            models.Index(fields=['business_type', 'average_rating']),
            models.Index(fields=['follower_count']),
        ]
        ordering = ['-follower_count', 'display_name']
    
    def __str__(self):
        return f"@{self.username} on {self.platform.display_name}"

class ProductCategory(models.Model):
    """Hierarchical category system with frontend mapping"""
    name = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(max_length=110, unique=True, db_index=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    # Hierarchy levels
    main_category = models.CharField(max_length=100, db_index=True)  # Electronics, Home Appliances
    subcategory = models.CharField(max_length=100, blank=True, db_index=True)  # Phones, Air Conditioners
    
    # Category metadata
    description = models.TextField(blank=True)
    url = models.URLField(blank=True, help_text="Category URL for scraping")
    icon_class = models.CharField(max_length=50, blank=True)  # CSS icon class
    color_code = models.CharField(max_length=7, blank=True)  # Hex color for UI
    
    # SEO and keywords
    keywords = models.TextField(blank=True, help_text="Comma-separated keywords for product matching")
    meta_description = models.CharField(max_length=160, blank=True)
    
    # Category metrics
    product_count = models.IntegerField(default=0, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    sort_order = models.IntegerField(default=0, db_index=True)
    
    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['main_category', 'subcategory']),
            models.Index(fields=['parent', 'is_active', 'sort_order']),
            models.Index(fields=['is_featured', 'product_count']),
        ]
        verbose_name_plural = "Product Categories"
        ordering = ['main_category', 'sort_order', 'name']
    
    def __str__(self):
        if self.subcategory:
            return f"{self.main_category} > {self.subcategory}"
        return self.main_category
    
    @property
    def full_path(self):
        """Get full category path for breadcrumbs"""
        if self.parent:
            return f"{self.parent.full_path} > {self.name}"
        return self.name
    
    def get_keyword_list(self):
        """Get keywords as list for matching"""
        return [k.strip().lower() for k in self.keywords.split(',') if k.strip()]

# ============================================================================
# CORE PRODUCT MODEL
# ============================================================================

class CoreProduct(models.Model):
    """Core product information shared across all platforms"""
    # Unique identifier
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    
    # Basic product information
    name = models.CharField(max_length=300, db_index=True)
    slug = models.SlugField(max_length=320, unique=True, db_index=True)
    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=500, blank=True)
    
    # Pricing
    price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)],
        db_index=True
    )
    original_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)]
    )
    currency = models.CharField(max_length=3, default='PKR', db_index=True)
    
    # Relationships
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name='products')
    
    # Product details
    model_number = models.CharField(max_length=150, blank=True, db_index=True)
    sku = models.CharField(max_length=100, blank=True, db_index=True)
    
    # Images (main image)
    main_image_url = models.URLField(max_length=1000, blank=True)
    
    # Platform identification
    platform_type = models.CharField(
        max_length=20,
        choices=[
            ('instagram', 'Instagram'),
            ('ecommerce', 'E-commerce'),
            ('marketplace', 'Marketplace'),
        ],
        db_index=True
    )
    
    # Product metrics
    view_count = models.IntegerField(default=0, db_index=True)
    wishlist_count = models.IntegerField(default=0, db_index=True)
    
    # Quality and status
    quality_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)],
        db_index=True,
        help_text="Calculated quality score based on data completeness and seller reputation"
    )
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    is_verified = models.BooleanField(default=False, db_index=True)
    
    # Availability tracking (reactive checking when users visit)
    availability_status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active - Available on platform'),
            ('checking', 'Checking - Availability being verified'),
            ('unavailable', 'Unavailable - Not found on platform'),
            ('error', 'Error - Could not verify'),
            ('unknown', 'Unknown - Not checked yet')
        ],
        default='unknown',
        db_index=True
    )
    last_availability_check = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Last time we checked if product exists on source platform'
    )
    consecutive_failures = models.IntegerField(
        default=0,
        help_text='Number of consecutive failed availability checks'
    )
    availability_check_message = models.TextField(
        blank=True,
        help_text='Message to show users when product is unavailable'
    )
    
    # SEO and search
    search_vector = SearchVectorField(null=True, blank=True)
    
    # AI Semantic Search (Phase 1) - stores numpy array as binary
    search_embedding = models.BinaryField(null=True, blank=True, editable=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_scraped = models.DateTimeField(null=True, blank=True, db_index=True)
    
    class Meta:
        indexes = [
            # Performance-critical indexes
            models.Index(fields=['platform_type', 'is_active', 'created_at']),
            models.Index(fields=['category', 'brand', 'price']),
            models.Index(fields=['seller', 'is_active']),
            models.Index(fields=['price', 'currency']),
            models.Index(fields=['is_featured', 'quality_score']),
            models.Index(fields=['brand', 'category']),
            
            # Search and filtering
            models.Index(fields=['name', 'brand']),
            models.Index(fields=['model_number']),
            models.Index(fields=['sku']),
            
            # Analytics indexes
            models.Index(fields=['created_at', 'platform_type']),
            models.Index(fields=['view_count']),
            models.Index(fields=['wishlist_count']),
            
            # Full-text search
            GinIndex(fields=['search_vector']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.seller.username}"
    
    @property
    def display_price(self):
        """Get formatted price for display"""
        if self.price:
            return f"₨ {self.price:,.0f}"
        return "Contact Seller"
    
    @property
    def discount_percentage(self):
        """Calculate discount percentage"""
        if self.original_price and self.price and self.original_price > self.price:
            return round(((self.original_price - self.price) / self.original_price) * 100)
        return 0
    
    @property
    def platform_data(self):
        """Get platform-specific data"""
        if self.platform_type == 'instagram':
            return getattr(self, 'instagram_data', None)
        elif self.platform_type == 'ecommerce':
            return getattr(self, 'ecommerce_data', None)
        return None

# ============================================================================
# PLATFORM-SPECIFIC MODELS
# ============================================================================

class InstagramProduct(models.Model):
    """Instagram-specific product data"""
    product = models.OneToOneField(CoreProduct, on_delete=models.CASCADE, related_name='instagram_data')
    
    # Instagram post information
    post_id = models.CharField(max_length=200, unique=True, db_index=True)
    post_url = models.URLField(max_length=500)
    caption = models.TextField(blank=True)
    hashtags = models.TextField(blank=True, help_text="Comma-separated hashtags")
    
    # Engagement metrics
    likes_count = models.IntegerField(default=0, db_index=True)
    comments_count = models.IntegerField(default=0, db_index=True)
    engagement_rate = models.FloatField(null=True, blank=True, db_index=True)
    
    # Post metadata
    posted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    is_story = models.BooleanField(default=False)
    is_reel = models.BooleanField(default=False)
    
    # Contact information
    contact_info = models.CharField(max_length=300, blank=True)
    
    # Scraping metadata
    last_scraped = models.DateTimeField(auto_now=True)
    scraping_source = models.CharField(max_length=50, default='apify')
    
    class Meta:
        indexes = [
            models.Index(fields=['post_id']),
            models.Index(fields=['likes_count', 'comments_count']),
            models.Index(fields=['engagement_rate']),
            models.Index(fields=['posted_at']),
            models.Index(fields=['last_scraped']),
        ]
    
    def __str__(self):
        return f"Instagram: {self.product.name}"
    
    @property
    def engagement_display(self):
        """Format engagement for display"""
        return f"{self.likes_count:,} likes, {self.comments_count:,} comments"
    
    def get_hashtag_list(self):
        """Get hashtags as list"""
        return [h.strip() for h in self.hashtags.split(',') if h.strip()]

class EcommerceProduct(models.Model):
    """E-commerce platform-specific product data"""
    product = models.OneToOneField(CoreProduct, on_delete=models.CASCADE, related_name='ecommerce_data')
    
    # Platform identification
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, related_name='ecommerce_products')
    platform_product_id = models.CharField(max_length=200, blank=True, db_index=True)
    platform_url = models.URLField(max_length=1000, unique=True)
    
    # Inventory and availability
    in_stock = models.BooleanField(default=True, db_index=True)
    stock_quantity = models.IntegerField(null=True, blank=True, db_index=True)
    stock_status = models.CharField(max_length=100, blank=True)
    
    # Shipping and fulfillment
    shipping_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    shipping_time = models.CharField(max_length=100, blank=True)
    free_shipping = models.BooleanField(default=False, db_index=True)
    
    # Product details
    warranty_period = models.CharField(max_length=100, blank=True)
    return_policy = models.TextField(blank=True)
    
    # Technical specifications (flexible JSON storage)
    specifications = models.JSONField(default=dict, blank=True)
    features = models.JSONField(default=list, blank=True)
    
    # Reviews and ratings
    average_rating = models.FloatField(null=True, blank=True, db_index=True)
    review_count = models.IntegerField(default=0, db_index=True)
    
    # Scraping metadata
    original_category_path = models.CharField(max_length=500, blank=True)
    last_scraped = models.DateTimeField(auto_now=True)
    scraping_source = models.CharField(max_length=50, default='selenium')
    
    class Meta:
        indexes = [
            models.Index(fields=['platform', 'in_stock']),
            models.Index(fields=['platform_product_id']),
            models.Index(fields=['stock_quantity']),
            models.Index(fields=['average_rating', 'review_count']),
            models.Index(fields=['free_shipping']),
            models.Index(fields=['last_scraped']),
        ]
        unique_together = ['platform', 'platform_product_id']
    
    def __str__(self):
        return f"{self.platform.display_name}: {self.product.name}"
    
    @property
    def stock_display(self):
        """Format stock status for display"""
        if not self.in_stock:
            return "Out of Stock"
        elif self.stock_quantity:
            return f"{self.stock_quantity} in stock"
        elif self.stock_status:
            return self.stock_status
        return "In Stock"

# ============================================================================
# DATA MANAGEMENT MODELS
# ============================================================================

class RawScrapedData(models.Model):
    """Store original scraped data for debugging and reprocessing"""
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    
    # Source information
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, related_name='raw_data')
    source_url = models.URLField(max_length=1000)
    scraper_type = models.CharField(max_length=50, db_index=True)  # selenium, apify, etc.
    
    # Raw data
    raw_json = models.JSONField()
    raw_html = models.TextField(blank=True)
    
    # Processing status
    processed = models.BooleanField(default=False, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    product = models.ForeignKey(CoreProduct, on_delete=models.SET_NULL, null=True, blank=True, related_name='raw_data')
    
    # Error tracking
    processing_errors = models.JSONField(default=list, blank=True)
    retry_count = models.IntegerField(default=0)
    
    # Metadata
    scraped_at = models.DateTimeField(auto_now_add=True, db_index=True)
    file_size = models.IntegerField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['platform', 'processed', 'scraped_at']),
            models.Index(fields=['scraper_type', 'processed']),
            models.Index(fields=['source_url']),
        ]
        ordering = ['-scraped_at']
    
    def __str__(self):
        return f"Raw data from {self.platform.display_name} - {self.scraped_at}"

class PriceHistory(models.Model):
    """Track price changes over time"""
    product = models.ForeignKey(CoreProduct, on_delete=models.CASCADE, related_name='price_history')
    
    price = models.DecimalField(max_digits=12, decimal_places=2)
    original_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='PKR')
    
    # Source of price change
    change_source = models.CharField(
        max_length=20,
        choices=[
            ('scraping', 'Scraping'),
            ('manual', 'Manual Update'),
            ('api', 'API Update'),
        ],
        default='scraping'
    )
    
    # Price change metadata
    price_change = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_change_percentage = models.FloatField(null=True, blank=True)
    
    recorded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['product', 'recorded_at']),
            models.Index(fields=['recorded_at']),
            models.Index(fields=['price']),
        ]
        ordering = ['-recorded_at']
    
    def __str__(self):
        return f"{self.product.name} - ₨{self.price} on {self.recorded_at.date()}"

class ProductAuditLog(models.Model):
    """Track all changes to products for debugging and analytics"""
    product = models.ForeignKey(CoreProduct, on_delete=models.CASCADE, related_name='audit_logs')
    
    # Change information
    action = models.CharField(
        max_length=20,
        choices=[
            ('created', 'Created'),
            ('updated', 'Updated'),
            ('deleted', 'Deleted'),
            ('scraped', 'Scraped'),
        ],
        db_index=True
    )
    
    # Changed fields
    changed_fields = models.JSONField(default=list, blank=True)
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    
    # Source of change
    change_source = models.CharField(max_length=100, blank=True)  # scraper name, user, api
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Metadata
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['product', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.action} - {self.product.name} at {self.timestamp}"

# ============================================================================
# USER INTERACTION MODELS
# ============================================================================

class Wishlist(models.Model):
    """User wishlist with enhanced functionality"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(CoreProduct, on_delete=models.CASCADE, related_name='wishlist_entries')
    
    # Wishlist metadata
    added_at = models.DateTimeField(auto_now_add=True, db_index=True)
    notes = models.TextField(blank=True)
    priority = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(5)])
    
    # Notifications
    notify_price_drop = models.BooleanField(default=True)
    notify_back_in_stock = models.BooleanField(default=True)
    price_threshold = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'product']
        indexes = [
            models.Index(fields=['user', 'added_at']),
            models.Index(fields=['product', 'added_at']),
            models.Index(fields=['priority', 'added_at']),
        ]
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name}"

class ProductReview(models.Model):
    """Product reviews and ratings"""
    product = models.ForeignKey(CoreProduct, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    
    # Review content
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        db_index=True
    )
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField(blank=True)
    
    # Review metadata
    is_verified_purchase = models.BooleanField(default=False, db_index=True)
    helpful_votes = models.IntegerField(default=0, db_index=True)
    
    # Status
    is_approved = models.BooleanField(default=True, db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['product', 'user']
        indexes = [
            models.Index(fields=['product', 'is_approved', 'created_at']),
            models.Index(fields=['rating', 'is_approved']),
            models.Index(fields=['helpful_votes']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.rating}⭐ - {self.product.name} by {self.user.username}"

# ============================================================================
# OPTIMIZED QUERY EXAMPLES
# ============================================================================

class ProductQuerySet(models.QuerySet):
    """Custom QuerySet with optimized methods"""
    
    def active(self):
        """Get only active products"""
        return self.filter(is_active=True)
    
    def featured(self):
        """Get featured products"""
        return self.filter(is_featured=True, is_active=True)
    
    def by_platform(self, platform_type):
        """Filter by platform type with optimized query"""
        return self.filter(platform_type=platform_type, is_active=True)
    
    def by_category(self, category_id):
        """Filter by category with related data"""
        return self.filter(category_id=category_id, is_active=True).select_related('brand', 'category', 'seller')
    
    def by_brand(self, brand_id):
        """Filter by brand with optimized query"""
        return self.filter(brand_id=brand_id, is_active=True).select_related('brand', 'category')
    
    def price_range(self, min_price, max_price):
        """Filter by price range"""
        return self.filter(price__range=(min_price, max_price), price__isnull=False)
    
    def with_engagement(self):
        """Get Instagram products with engagement data"""
        return self.filter(platform_type='instagram').select_related('instagram_data')
    
    def with_stock_info(self):
        """Get e-commerce products with stock information"""
        return self.filter(platform_type='ecommerce').select_related('ecommerce_data')
    
    def search(self, query):
        """Full-text search (requires PostgreSQL)"""
        from django.contrib.postgres.search import SearchQuery, SearchRank
        search_query = SearchQuery(query)
        return self.filter(search_vector=search_query).annotate(
            rank=SearchRank('search_vector', search_query)
        ).order_by('-rank')

class ProductManager(models.Manager):
    """Custom manager with optimized methods"""
    
    def get_queryset(self):
        return ProductQuerySet(self.model, using=self._db)
    
    def active(self):
        return self.get_queryset().active()
    
    def featured(self):
        return self.get_queryset().featured()
    
    def by_platform(self, platform_type):
        return self.get_queryset().by_platform(platform_type)

# Add custom manager to CoreProduct
CoreProduct.add_to_class('objects', ProductManager())

# ============================================================================
# EXAMPLE USAGE AND OPTIMIZED QUERIES
# ============================================================================

"""
OPTIMIZED QUERY EXAMPLES:

# 1. Get Instagram products with engagement (1 query instead of N+1)
instagram_products = CoreProduct.objects.by_platform('instagram').select_related(
    'instagram_data', 'seller', 'brand', 'category'
)

# 2. Get e-commerce products with stock info (1 query instead of N+1)
ecommerce_products = CoreProduct.objects.by_platform('ecommerce').select_related(
    'ecommerce_data', 'seller__platform', 'brand', 'category'
)

# 3. Filter by category with optimized joins
electronics = CoreProduct.objects.by_category(electronics_category_id)

# 4. Price range search with brand and category
expensive_phones = CoreProduct.objects.filter(
    category__main_category='Electronics',
    category__subcategory='Phones',
    price__range=(50000, 200000)
).select_related('brand', 'category', 'seller')

# 5. Featured products for homepage (cached query)
featured_products = CoreProduct.objects.featured().select_related(
    'brand', 'category'
)[:10]

# 6. Full-text search (PostgreSQL)
search_results = CoreProduct.objects.search('Samsung Galaxy phone')

# 7. Get products with price history
products_with_history = CoreProduct.objects.prefetch_related('price_history')

# 8. Analytics query - products by platform and category
analytics_data = CoreProduct.objects.values(
    'platform_type', 'category__main_category'
).annotate(
    count=models.Count('id'),
    avg_price=models.Avg('price')
)

CACHING EXAMPLES:

from django.core.cache import cache

# Cache popular categories (1 hour)
def get_popular_categories():
    cache_key = 'popular_categories'
    categories = cache.get(cache_key)
    if not categories:
        categories = ProductCategory.objects.filter(
            is_featured=True, is_active=True
        ).order_by('-product_count')[:10]
        cache.set(cache_key, categories, 3600)  # 1 hour
    return categories

# Cache top brands (30 minutes)
def get_top_brands():
    cache_key = 'top_brands'
    brands = cache.get(cache_key)
    if not brands:
        brands = Brand.objects.filter(
            is_verified=True
        ).annotate(
            product_count=models.Count('products')
        ).order_by('-product_count')[:20]
        cache.set(cache_key, brands, 1800)  # 30 minutes
    return brands
"""

# ============================================================================
# SIGNALS FOR AUTOMATIC WISHLIST COUNT UPDATES
# ============================================================================

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=Wishlist)
def update_wishlist_count_on_add(sender, instance, created, **kwargs):
    """Update product wishlist_count when wishlist item is added"""
    if created:
        product = instance.product
        wishlist_count = Wishlist.objects.filter(product=product).count()
        CoreProduct.objects.filter(pk=product.pk).update(wishlist_count=wishlist_count)

@receiver(post_delete, sender=Wishlist)
def update_wishlist_count_on_remove(sender, instance, **kwargs):
    """Update product wishlist_count when wishlist item is removed"""
    product = instance.product
    wishlist_count = Wishlist.objects.filter(product=product).count()
    CoreProduct.objects.filter(pk=product.pk).update(wishlist_count=wishlist_count)