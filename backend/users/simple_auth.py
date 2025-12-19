"""
Simple authentication views that completely bypass CSRF
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
import json

@csrf_exempt
@require_http_methods(["POST"])
def simple_login(request):
    """Simple login endpoint that completely bypasses CSRF"""
    try:
        # Parse JSON data
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return JsonResponse(
                {'error': 'Username and password are required'}, 
                status=400
            )
        
        user = authenticate(username=username, password=password)
        
        if user:
            token, created = Token.objects.get_or_create(user=user)
            return JsonResponse({
                'token': token.key,
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            })
        else:
            return JsonResponse(
                {'error': 'Invalid credentials'}, 
                status=401
            )
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse(
            {'error': f'Login failed: {str(e)}'}, 
            status=500
        )

@csrf_exempt
@require_http_methods(["POST"])
def simple_register(request):
    """Simple registration endpoint that completely bypasses CSRF"""
    try:
        from django.contrib.auth.models import User
        
        # Parse JSON data
        data = json.loads(request.body)
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        
        if not username or not email or not password:
            return JsonResponse(
                {'error': 'Username, email, and password are required'}, 
                status=400
            )
        
        if User.objects.filter(username=username).exists():
            return JsonResponse(
                {'error': 'Username already exists'}, 
                status=400
            )
        
        if User.objects.filter(email=email).exists():
            return JsonResponse(
                {'error': 'Email already exists'}, 
                status=400
            )
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        token = Token.objects.create(user=user)
        
        return JsonResponse({
            'token': token.key,
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse(
            {'error': f'Registration failed: {str(e)}'}, 
            status=500
        )
