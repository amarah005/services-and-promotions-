from django.contrib import admin
from .models import Recommendation

@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'score', 'created_at']
    list_filter = ['score', 'created_at']
    search_fields = ['user__username', 'product__name', 'reason']
    ordering = ['-score', '-created_at']
