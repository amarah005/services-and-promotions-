from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render
from django.db.models import Count, Avg, Q
from .models import (
    Platform, Brand, Seller, ProductCategory, CoreProduct,
    InstagramProduct, EcommerceProduct, RawScrapedData,
    PriceHistory, ProductAuditLog, Wishlist, ProductReview
)

@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'platform_type', 'is_active', 'scraping_enabled', 'product_count']
    list_filter = ['platform_type', 'is_active', 'scraping_enabled']
    search_fields = ['name', 'display_name']
    readonly_fields = ['created_at', 'updated_at']
    
    def product_count(self, obj):
        count = CoreProduct.objects.filter(
            Q(ecommerce_data__platform=obj) | Q(platform_type='instagram', seller__platform=obj)
        ).count()
        return format_html('<span style="color: green;">{}</span>', count)
    product_count.short_description = 'Products Count'

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'is_verified', 'product_count', 'created_at']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['name', 'display_name']
    readonly_fields = ['created_at', 'updated_at']
    
    def product_count(self, obj):
        count = CoreProduct.objects.filter(brand=obj).count()
        return format_html('<span style="color: blue;">{}</span>', count)
    product_count.short_description = 'Products Count'

@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ['username', 'platform', 'business_type', 'verified', 'is_active']
    list_filter = ['platform', 'business_type', 'verified', 'is_active']
    search_fields = ['username', 'display_name']

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'main_category', 'subcategory', 'is_active']
    list_filter = ['main_category', 'is_active']
    search_fields = ['name', 'main_category', 'subcategory']

@admin.register(CoreProduct)
class CoreProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'platform_type', 'brand', 'category', 'is_active', 'created_at']
    list_filter = ['platform_type', 'brand', 'category', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'brand__name', 'category__name']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'last_scraped']
    list_per_page = 25
    
    # Bulk actions
    actions = ['mark_as_active', 'mark_as_inactive', 'export_products']
    
    def mark_as_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} products marked as active.')
    mark_as_active.short_description = "Mark selected products as active"
    
    def mark_as_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} products marked as inactive.')
    mark_as_inactive.short_description = "Mark selected products as inactive"
    
    def export_products(self, request, queryset):
        # This would export selected products to CSV/Excel
        self.message_user(request, f'Exporting {queryset.count()} products...')
    export_products.short_description = "Export selected products"

@admin.register(InstagramProduct)
class InstagramProductAdmin(admin.ModelAdmin):
    list_display = ['product', 'post_id', 'likes_count', 'comments_count']
    search_fields = ['product__name', 'post_id']

@admin.register(EcommerceProduct)
class EcommerceProductAdmin(admin.ModelAdmin):
    list_display = ['product', 'platform', 'in_stock', 'stock_quantity']
    list_filter = ['platform', 'in_stock']
    search_fields = ['product__name', 'platform__name']

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__username', 'product__name']
    ordering = ['-added_at']

@admin.register(RawScrapedData)
class RawScrapedDataAdmin(admin.ModelAdmin):
    list_display = ['id', 'platform', 'scraper_type', 'processed', 'processed_at']
    list_filter = ['platform', 'scraper_type', 'processed', 'processed_at']
    search_fields = ['platform__name', 'source_url']
    readonly_fields = ['uuid', 'processed_at']
    ordering = ['-processed_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('platform')

@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'price', 'currency', 'recorded_at', 'change_source']
    list_filter = ['currency', 'change_source', 'recorded_at']
    search_fields = ['product__name']
    readonly_fields = ['recorded_at']
    ordering = ['-recorded_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')

@admin.register(ProductAuditLog)
class ProductAuditLogAdmin(admin.ModelAdmin):
    list_display = ['product', 'action', 'change_source', 'timestamp', 'user']
    list_filter = ['action', 'change_source', 'timestamp']
    search_fields = ['product__name', 'user__username', 'change_source']
    readonly_fields = ['timestamp']
    ordering = ['-timestamp']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'user')

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'is_verified_purchase', 'created_at']
    list_filter = ['rating', 'is_verified_purchase', 'created_at']
    search_fields = ['product__name', 'user__username', 'title', 'content']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'user')


# Custom Admin Site Configuration
admin.site.site_header = "BuyVaultHub Admin Panel"
admin.site.site_title = "BuyVaultHub Admin"
admin.site.index_title = "Product Aggregator Management"