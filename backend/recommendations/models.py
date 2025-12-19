from django.db import models
from django.contrib.auth.models import User

class Recommendation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    product = models.ForeignKey('products.CoreProduct', on_delete=models.CASCADE, related_name='recommendations')
    score = models.FloatField(default=0.0)  # AI recommendation score
    reason = models.TextField(blank=True)  # Why this product was recommended
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'product']
        ordering = ['-score', '-created_at']
