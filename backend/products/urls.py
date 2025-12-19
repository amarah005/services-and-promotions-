from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'products', views.ProductViewSet)
router.register(r'categories', views.CategoryViewSet, basename='categories')
router.register(r'wishlist', views.WishlistViewSet, basename='wishlist')

urlpatterns = [
    # Image proxy endpoint (must come before router to avoid conflicts)
    path('products/proxy-image/<path:image_url>', views.proxy_image, name='proxy_image'),
    # Scraping endpoints
    path('scraped-products/', views.get_scraped_products, name='get_scraped_products'),
    path('scraping-status/', views.scraping_status, name='scraping_status'),
    path('scrape/instagram/', views.scrape_instagram, name='scrape_instagram'),
    path('scrape/website/', views.scrape_website, name='scrape_website'),
    path('scraping-jobs/', views.get_scraping_jobs, name='get_scraping_jobs'),
    path('scraping-history/', views.get_scraping_history, name='get_scraping_history'),
    # Router URLs (must come last)
    path('', include(router.urls)),
]
