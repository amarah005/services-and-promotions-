from rest_framework import serializers
from .models import Recommendation

class RecommendationSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)
    product_image = serializers.URLField(source='product.main_image_url', read_only=True)
    
    class Meta:
        model = Recommendation
        fields = [
            'id', 'user', 'product', 'product_name', 'product_price', 
            'product_image', 'score', 'reason', 'created_at'
        ]
        read_only_fields = ['created_at']
