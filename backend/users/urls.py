from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import simple_auth

router = DefaultRouter()
router.register(r'users', views.UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('rest_framework.urls')),
    path('auth/test/', views.test_view, name='test'),
    path('auth/simple-login/', simple_auth.simple_login, name='simple_login'),
    path('auth/simple-register/', simple_auth.simple_register, name='simple_register'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/register/', views.register_view, name='register'),
    path('auth/google/', views.google_login, name='google_login'),
]
