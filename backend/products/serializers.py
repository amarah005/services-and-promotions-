from rest_framework import serializers
from .models import CoreProduct, ProductCategory, Wishlist

class CategorySerializer(serializers.ModelSerializer):
    parent = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductCategory
        fields = ['id', 'name', 'main_category', 'subcategory', 'parent', 'description', 'created_at']
    
    def get_parent(self, obj):
        """Return parent as an object with id and name"""
        if obj.parent:
            return {
                'id': obj.parent.id,
                'name': obj.parent.name
            }
        return None

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    brand_name = serializers.SerializerMethodField()
    platform = serializers.SerializerMethodField()  # Map platform_type to platform for compatibility
    platform_url = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    instagram_username = serializers.SerializerMethodField()
    instagram_post_id = serializers.SerializerMethodField()
    instagram_caption = serializers.SerializerMethodField()
    instagram_likes = serializers.SerializerMethodField()
    instagram_comments = serializers.SerializerMethodField()
    contact_info = serializers.SerializerMethodField()
    availability = serializers.SerializerMethodField()
    is_scraped = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CoreProduct
        fields = [
            'id', 'name', 'description', 'price', 'original_price',
            'category', 'category_name', 'platform', 'platform_url',
            'sku', 'brand', 'brand_name', 'model_number', 'main_image_url',
            'image_url',
            'instagram_username', 'instagram_post_id', 'instagram_caption',
            'instagram_likes', 'instagram_comments', 'contact_info',
            'availability', 'average_rating', 'review_count',
            'availability_status', 'availability_check_message', 'last_availability_check',
            'created_at', 'updated_at', 'last_scraped', 'is_scraped'
        ]
        read_only_fields = ['created_at', 'updated_at', 'last_scraped']
    
    def get_brand_name(self, obj):
        """Return brand name for frontend display"""
        if obj.brand:
            return obj.brand.display_name
        
        # Fallback: Extract brand from product name
        if obj.name:
            # Common electronics brands to look for
            common_brands = [
                'Samsung', 'LG', 'Sony', 'Apple', 'Huawei', 'Xiaomi', 'Oppo', 'Vivo', 
                'OnePlus', 'Realme', 'Tecno', 'Infinix', 'Haier', 'Dawlance', 'Orient',
                'AUX', 'Gree', 'TCL', 'Changhong', 'HP', 'Dell', 'Lenovo', 'Asus',
                'Acer', 'MSI', 'Canon', 'Nikon', 'JBL', 'Beats', 'Bose', 'Anker'
            ]
            
            name_lower = obj.name.lower()
            for brand in common_brands:
                if brand.lower() in name_lower:
                    return brand
        
        return None  # Don't show 'Unknown', just empty
    
    def get_platform(self, obj):
        """Get actual platform display name for frontend"""
        if obj.platform_type == 'ecommerce' and hasattr(obj, 'ecommerce_data') and obj.ecommerce_data.platform:
            return obj.ecommerce_data.platform.display_name
        elif obj.platform_type == 'instagram' and hasattr(obj, 'instagram_data'):
            return 'Instagram'
        return obj.platform_type or 'Unknown'
    
    def get_platform_url(self, obj):
        """Get platform URL from platform-specific data"""
        if obj.platform_type == 'instagram' and hasattr(obj, 'instagram_data'):
            return obj.instagram_data.post_url
        elif obj.platform_type == 'ecommerce' and hasattr(obj, 'ecommerce_data'):
            return obj.ecommerce_data.platform_url
        return ''

    def get_image_url(self, obj):
        """Expose a stable image_url alias for frontend compatibility"""
        return getattr(obj, 'main_image_url', '') or ''
    
    def get_instagram_username(self, obj):
        """Get Instagram username from platform-specific data"""
        if obj.platform_type == 'instagram' and hasattr(obj, 'instagram_data'):
            return obj.seller.username
        return ''
    
    def get_instagram_post_id(self, obj):
        """Get Instagram post ID from platform-specific data"""
        if obj.platform_type == 'instagram' and hasattr(obj, 'instagram_data'):
            return obj.instagram_data.post_id
        return ''
    
    def get_instagram_caption(self, obj):
        """Get Instagram caption from platform-specific data"""
        if obj.platform_type == 'instagram' and hasattr(obj, 'instagram_data'):
            return obj.instagram_data.caption
        return ''
    
    def get_instagram_likes(self, obj):
        """Get Instagram likes from platform-specific data"""
        if obj.platform_type == 'instagram' and hasattr(obj, 'instagram_data'):
            return obj.instagram_data.likes_count
        return 0
    
    def get_instagram_comments(self, obj):
        """Get Instagram comments from platform-specific data"""
        if obj.platform_type == 'instagram' and hasattr(obj, 'instagram_data'):
            return obj.instagram_data.comments_count
        return 0
    
    def get_contact_info(self, obj):
        """Get contact info from platform-specific data"""
        if obj.platform_type == 'instagram' and hasattr(obj, 'instagram_data'):
            return obj.instagram_data.contact_info
        return ''
    
    def get_availability(self, obj):
        """Get availability from platform-specific data"""
        if obj.platform_type == 'ecommerce' and hasattr(obj, 'ecommerce_data'):
            return obj.ecommerce_data.in_stock
        return True
    
    def get_average_rating(self, obj):
        """Get average rating from ecommerce data"""
        if obj.platform_type == 'ecommerce' and hasattr(obj, 'ecommerce_data'):
            return obj.ecommerce_data.average_rating
        return None
    
    def get_review_count(self, obj):
        """Get review count from ecommerce data"""
        if obj.platform_type == 'ecommerce' and hasattr(obj, 'ecommerce_data'):
            return obj.ecommerce_data.review_count
        return 0
    
    def get_is_scraped(self, obj):
        """Check if product is scraped (has platform-specific data)"""
        return hasattr(obj, 'instagram_data') or hasattr(obj, 'ecommerce_data')

class WishlistSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Wishlist
        fields = ['id', 'product', 'product_id', 'added_at']
        read_only_fields = ['added_at']
