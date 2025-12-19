from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import render
from django.utils import timezone
from django.db import models
from django.db.models import Case, When, IntegerField, F
from django.http import HttpResponse, Http404
from django.views.decorators.cache import cache_page
import requests
import urllib.parse
from .models import CoreProduct, ProductCategory, Wishlist
from .serializers import ProductSerializer, CategorySerializer, WishlistSerializer
import logging
import os
import time
import pickle
import numpy as np
import threading
from django.conf import settings
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from .utils.search_utils import expand_query_synonyms, parse_query_filters, build_token_groups

logger = logging.getLogger(__name__)

# ============================================================================
# AI MODEL SINGLETON (Module-level for proper caching)
# ============================================================================

# Global AI model instance (shared across all requests)
_ai_model_singleton = None
_ai_model_lock = threading.Lock()

def get_ai_model():
    """
    Get or load the AI model singleton (thread-safe, module-level)
    This ensures the model is loaded once and reused across all requests
    """
    global _ai_model_singleton, _ai_model_lock
    
    if _ai_model_singleton is not None:
        return _ai_model_singleton
    
    # Import here to avoid issues if not installed
    try:
        from sentence_transformers import SentenceTransformer
        import torch
        
        if _ai_model_lock is None:
            import threading
            _ai_model_lock = threading.Lock()
        
        # Double-check locking pattern for thread safety
        if _ai_model_singleton is None:
            with _ai_model_lock:
                if _ai_model_singleton is None:
                    logger.info('🤖 Loading AI search model (first time, this may take 20-30 seconds)...')
                    start_time = time.time()
                    
                    try:
                        device = 'cuda' if torch.cuda.is_available() else 'cpu'
                        _ai_model_singleton = SentenceTransformer('all-MiniLM-L6-v2', device=device)
                        load_time = time.time() - start_time
                        logger.info(f'✅ AI model loaded successfully on {device} in {load_time:.2f}s')
                    except Exception as e:
                        logger.error(f'❌ Failed to load AI model: {str(e)}')
                        raise
        
        return _ai_model_singleton
        
    except ImportError:
        logger.error('sentence-transformers not installed')
        return None
    except Exception as e:
        logger.error(f'Error loading AI model: {str(e)}')
        return None

class ProductViewSet(viewsets.ModelViewSet):
    queryset = CoreProduct.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    ordering_fields = ['created_at', 'price', 'name', 'view_count', 'wishlist_count']
    # No default ordering - let get_queryset handle it
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single product and check its availability on source platform
        Reactive checking: only check when user visits the product
        """
        instance = self.get_object()
        
        # Check product availability on source platform (non-blocking)
        try:
            from products.utils.availability_checker import check_product_availability
            
            # Check availability (will skip if recently checked)
            availability_result = check_product_availability(
                product=instance,
                force=False,  # Don't force, respect last check time
                update_db=True  # Update database with results
            )
            
            logger.info(f"Product {instance.id} availability check: {availability_result['status']}")
            
        except Exception as e:
            # Don't fail the request if availability check fails
            logger.error(f"Error checking product {instance.id} availability: {str(e)}")
        
        # Return product data (serializer will include availability status)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def get_queryset(self):
        """Override to add filtering support and deduplication"""
        queryset = CoreProduct.objects.filter(is_active=True)
        
        # Platform filtering
        platform = self.request.query_params.get('platform')
        if platform:
            # Filter by seller/platform display name (unified approach)
            queryset = queryset.filter(seller__display_name__icontains=platform)
        
        # Main category filtering - case-insensitive
        main_category = self.request.query_params.get('main_category')
        if main_category:
            # Use iexact for case-insensitive exact match
            queryset = queryset.filter(category__main_category__iexact=main_category)
        
        # Subcategory filtering - case-insensitive exact match
        subcategory = self.request.query_params.get('subcategory')
        if subcategory:
            queryset = queryset.filter(category__subcategory__iexact=subcategory)
        
        # Category name filtering (supports multiple categories)
        categories = self.request.query_params.getlist('category')
        if categories:
            # Filter by any of the provided categories
            from django.db.models import Q
            category_filter = Q()
            for category in categories:
                # Special handling for main categories like "Toys & Games"
                if category == 'Toys & Games':
                    # Include all products from Toys & Games subcategories
                    category_filter |= Q(category__parent__name='Toys & Games')
                else:
                    # Regular category filtering
                    category_filter |= Q(category__name__icontains=category)
            queryset = queryset.filter(category_filter)
        
        # Price range filtering
        min_price = self.request.query_params.get('min_price')
        if min_price:
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except ValueError:
                pass
        
        max_price = self.request.query_params.get('max_price')
        if max_price:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except ValueError:
                pass
        
        # Brand filtering
        brand = self.request.query_params.get('brand')
        if brand:
            queryset = queryset.filter(brand__display_name__iexact=brand)
        
        # Search filtering (weighted, with synonyms and safe fallback)
        search = self.request.query_params.get('search')
        if search:
            # Build AND-of-ORs filter: all tokens must appear (with synonyms), in any field
            token_groups = build_token_groups(search)
            group_clauses = []
            for group in token_groups:
                or_clause = models.Q()
                for token in group:
                    token_clause = (
                        models.Q(name__icontains=token) |
                        models.Q(description__icontains=token) |
                        models.Q(brand__name__icontains=token)
                    )
                    # Avoid category-name matches for very short tokens like 'ac'
                    if len(token) >= 3:
                        token_clause |= models.Q(category__name__icontains=token)
                    or_clause |= token_clause
                group_clauses.append(or_clause)
            fallback_q = models.Q()
            for gc in group_clauses:
                fallback_q &= gc
            try:
                expanded = expand_query_synonyms(search)
                search_query = SearchQuery(' '.join(expanded), search_type='plain')
                vector = (
                    SearchVector('name', weight='A') +
                    SearchVector('brand__name', weight='B') +
                    SearchVector('category__name', weight='B') +
                    SearchVector('description', weight='C')
                )
                queryset = queryset.annotate(rank=SearchRank(vector, search_query))\
                                   .filter(models.Q(search_vector=search_query) | fallback_q)\
                                   .order_by('-rank', '-created_at')
            except Exception:
                queryset = queryset.filter(fallback_q)
        
        # Deduplication: For products with same name+seller, prefer the one with:
        # 1. Has ecommerce_data.platform_url (most complete)
        # 2. Has main_image_url (has image)
        # 3. Most recent created_at
        queryset = queryset.annotate(
            has_url=Case(
                When(ecommerce_data__platform_url__isnull=False, ecommerce_data__platform_url__gt='', then=1),
                default=0,
                output_field=IntegerField()
            ),
            has_image=Case(
                When(main_image_url__isnull=False, main_image_url__gt='', then=1),
                default=0,
                output_field=IntegerField()
            )
        )
        
        # Apply user-requested ordering if provided, otherwise use deduplication ordering
        ordering_param = self.request.query_params.get('ordering')
        if ordering_param:
            # User wants specific ordering - skip deduplication to allow proper ordering
            # Just use the requested ordering without distinct
            queryset = queryset.order_by(ordering_param)
        else:
            # No user ordering - apply deduplication with quality sorting
            # PostgreSQL DISTINCT ON requires first ORDER BY fields to match DISTINCT ON fields
            queryset = queryset.order_by(
                'seller_id', 'name',  # Must match DISTINCT ON fields first
                '-has_url',           # Then prefer products with URLs
            '-has_image',         # Then prefer products with images
            '-created_at'         # Finally prefer newest
        ).distinct('seller_id', 'name')  # Take only the first (best) from each group
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Rich search endpoint with weighted FTS and synonym expansion"""
        from django.db.models.functions import Coalesce
        
        q = request.query_params.get('q', '').strip()
        limit = int(request.query_params.get('limit', 20))
        if not q:
            return Response([])
        expanded = expand_query_synonyms(q)
        token_groups = build_token_groups(q)
        fallback_q = models.Q()
        for group in token_groups:
            or_clause = models.Q()
            for token in group:
                token_clause = (
                    models.Q(name__icontains=token) |
                    models.Q(description__icontains=token) |
                    models.Q(brand__name__icontains=token)
                )
                if len(token) >= 3:
                    token_clause |= models.Q(category__name__icontains=token)
                or_clause |= token_clause
            fallback_q &= or_clause
        try:
            search_query = SearchQuery(' '.join(expanded), search_type='plain')
            vector = (
                SearchVector('name', weight='A') +
                SearchVector('brand__name', weight='B') +
                SearchVector('category__name', weight='B') +
                SearchVector('description', weight='C')
            )
            # Annotate with trending score and prioritize high-engagement products
            products = CoreProduct.objects.filter(is_active=True)\
                .annotate(
                    rank=SearchRank(vector, search_query),
                    trending_score=Coalesce(F('view_count'), 0) + (Coalesce(F('wishlist_count'), 0) * 3)
                )\
                .filter(models.Q(search_vector=search_query) | fallback_q)\
                .annotate(
                    # Boost products with trending_score > 50
                    is_trending=Case(
                        When(trending_score__gt=50, then=1),
                        default=0,
                        output_field=IntegerField()
                    )
                )\
                .order_by('-is_trending', '-rank', '-trending_score', '-created_at')[:limit]
        except Exception:
            # Fallback: still apply trending score even without FTS
            products = CoreProduct.objects.filter(is_active=True)\
                .annotate(
                    trending_score=Coalesce(F('view_count'), 0) + (Coalesce(F('wishlist_count'), 0) * 3)
                )\
                .filter(fallback_q)\
                .annotate(
                    is_trending=Case(
                        When(trending_score__gt=50, then=1),
                        default=0,
                        output_field=IntegerField()
                    )
                )\
                .order_by('-is_trending', '-trending_score', '-created_at')[:limit]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search_suggestions(self, request):
        """Get search suggestions with product images for real-time search"""
        from django.db.models.functions import Coalesce
        
        query = request.query_params.get('q', '').strip()
        limit = int(request.query_params.get('limit', 10))
        
        if len(query) < 2:
            return Response({'suggestions': []})
        
        # Search in multiple fields for better suggestions
        # Prioritize trending products (trending_score > 50)
        products = CoreProduct.objects.select_related(
            'category'
        ).filter(
            models.Q(name__icontains=query) |
            models.Q(description__icontains=query) |
            models.Q(category__name__icontains=query) |
            models.Q(instagram_data__caption__icontains=query)
        ).annotate(
            trending_score=Coalesce(F('view_count'), 0) + (Coalesce(F('wishlist_count'), 0) * 3)
        ).annotate(
            is_trending=Case(
                When(trending_score__gt=50, then=1),
                default=0,
                output_field=IntegerField()
            )
        ).distinct().order_by('-is_trending', '-trending_score', '-last_scraped', '-created_at')[:limit]
        
        # Format suggestions with essential data
        suggestions = []
        for product in products:
            suggestion = {
                'id': product.id,
                'name': product.name,
                'price': float(product.price) if product.price else 0,
                'image_url': getattr(product, 'main_image_url', ''),
                'category_name': product.category.name if product.category else 'General',
                'platform': ('Instagram' if product.platform_type == 'instagram' else (getattr(getattr(product, 'ecommerce_data', None), 'platform', None).display_name if getattr(getattr(product, 'ecommerce_data', None), 'platform', None) else product.platform_type)),
                'platform_url': (getattr(getattr(product, 'instagram_data', None), 'post_url', '') if product.platform_type == 'instagram' else getattr(getattr(product, 'ecommerce_data', None), 'platform_url', '')),
                'contact_info': (getattr(getattr(product, 'instagram_data', None), 'contact_info', '') if product.platform_type == 'instagram' else ''),
                'description': product.description[:100] + '...' if product.description and len(product.description) > 100 else product.description
            }
            suggestions.append(suggestion)
        
        return Response({'suggestions': suggestions})
    
    @action(detail=False, methods=['get'])
    def ai_search(self, request):
        """AI-powered semantic search using sentence transformers"""
        query = request.query_params.get('q', '').strip()
        limit = int(request.query_params.get('limit', 20))
        
        if not query:
            return Response({'error': 'Query parameter "q" is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get the module-level singleton model (thread-safe, cached)
            model = get_ai_model()
            
            if model is None:
                return Response({
                    'error': 'AI search not available - sentence-transformers not installed or model failed to load'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            # Generate query embedding
            logger.info(f'🤖 Generating embedding for query: "{query}"')
            query_start_time = time.time()
            query_embedding = model.encode(query, convert_to_numpy=True, show_progress_bar=False)
            encode_time = time.time() - query_start_time
            logger.info(f'✅ Query embedding generated in {encode_time:.3f}s')
            
            total_start_time = time.time()
            
            # Get products with embeddings (optimized batch processing)
            logger.info('📦 Fetching products with embeddings...')
            products = CoreProduct.objects.filter(
                is_active=True,
                search_embedding__isnull=False
            ).select_related('brand', 'category', 'seller').only(
                'id', 'name', 'description', 'price', 'original_price', 'main_image_url',
                'search_embedding', 'brand', 'category', 'seller', 'platform_type',
                'created_at', 'updated_at'
            )
            
            # Batch process embeddings for speed
            logger.info('🔍 Processing product embeddings...')
            product_list = list(products)
            embeddings_matrix = []
            valid_products = []
            
            for product in product_list:
                try:
                    embedding = pickle.loads(product.search_embedding)
                    embeddings_matrix.append(embedding)
                    valid_products.append(product)
                except Exception as e:
                    logger.debug(f'Failed to load embedding for product {product.id}: {str(e)}')
                    continue
            
            logger.info(f'✅ Loaded {len(valid_products)} product embeddings')
            
            # Vectorized similarity calculation (MUCH faster!)
            if embeddings_matrix:
                logger.info('🔢 Calculating similarities...')
                start_time = time.time()
                
                embeddings_array = np.array(embeddings_matrix)
                # Normalize embeddings
                embeddings_norm = embeddings_array / np.linalg.norm(embeddings_array, axis=1, keepdims=True)
                query_norm = query_embedding / np.linalg.norm(query_embedding)
                
                # Calculate all similarities at once (vectorized)
                similarities = np.dot(embeddings_norm, query_norm)
                
                similarity_time = time.time() - start_time
                logger.info(f'✅ Similarities calculated in {similarity_time:.3f}s')
                
                # Create results
                results = [
                    {'product': product, 'similarity': float(sim)}
                    for product, sim in zip(valid_products, similarities)
                ]
                
                # Sort by similarity (descending)
                results.sort(key=lambda x: x['similarity'], reverse=True)
                logger.info(f'📊 Top similarity score: {results[0]["similarity"]:.4f}' if results else 'No results')
            else:
                results = []
                logger.warning('⚠️ No valid embeddings found')
            
            # Get top results
            top_results = results[:limit]
            
            # Serialize
            logger.info(f'📝 Serializing {len(top_results)} results...')
            serialized_results = []
            for result in top_results:
                product_data = ProductSerializer(result['product']).data
                product_data['similarity_score'] = result['similarity']
                serialized_results.append(product_data)
            
            total_time = time.time() - total_start_time
            logger.info(f'✅ AI search completed: {len(serialized_results)} results in {total_time:.2f}s')
            
            return Response({
                'query': query,
                'results': serialized_results,
                'total_found': len(results),
                'returned': len(serialized_results)
            })
            
        except Exception as e:
            logger.error(f'❌ AI search error: {str(e)}', exc_info=True)
            import traceback
            error_details = traceback.format_exc()
            logger.error(f'Stack trace: {error_details}')
            return Response({
                'error': f'AI search failed: {str(e)}',
                'details': error_details if settings.DEBUG else None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def hybrid_search(self, request):
        """Hybrid search combining AI semantic search + PostgreSQL full-text search"""
        query = request.query_params.get('q', '').strip()
        limit = int(request.query_params.get('limit', 20))
        
        if not query:
            return Response({'error': 'Query parameter "q" is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # === PART 1: AI Semantic Search (Optimized) ===
            ai_results = []
            try:
                # Use the same module-level singleton model
                model = get_ai_model()
                
                if model is None:
                    logger.warning('AI model not available for hybrid search')
                    raise Exception('AI model not loaded')
                
                query_embedding = model.encode(query, convert_to_numpy=True, show_progress_bar=False)
                
                products_with_embeddings = CoreProduct.objects.filter(
                    is_active=True,
                    search_embedding__isnull=False
                ).select_related('brand', 'category', 'seller').only(
                    'id', 'name', 'description', 'price', 'original_price', 'main_image_url',
                    'search_embedding', 'brand', 'category', 'seller', 'platform_type',
                    'created_at', 'updated_at'
                )[:1000]  # Limit for performance
                
                # Batch vectorized processing
                product_list = list(products_with_embeddings)
                embeddings_matrix = []
                valid_products = []
                
                for product in product_list:
                    try:
                        embedding = pickle.loads(product.search_embedding)
                        embeddings_matrix.append(embedding)
                        valid_products.append(product)
                    except:
                        continue
                
                if embeddings_matrix:
                    embeddings_array = np.array(embeddings_matrix)
                    embeddings_norm = embeddings_array / np.linalg.norm(embeddings_array, axis=1, keepdims=True)
                    query_norm = query_embedding / np.linalg.norm(query_embedding)
                    similarities = np.dot(embeddings_norm, query_norm)
                    
                    ai_results = [
                        {'product': product, 'ai_score': float(sim)}
                        for product, sim in zip(valid_products, similarities)
                    ]
                    
                    # Sort and get top results
                    ai_results.sort(key=lambda x: x['ai_score'], reverse=True)
                    ai_results = ai_results[:limit * 2]
                
            except Exception as e:
                logger.warning(f'AI search failed in hybrid mode: {e}')
            
            # === PART 2: PostgreSQL Full-Text Search ===
            fts_results = []
            try:
                expanded = expand_query_synonyms(query)
                search_query = SearchQuery(' '.join(expanded), search_type='plain')
                vector = (
                    SearchVector('name', weight='A') +
                    SearchVector('brand__name', weight='B') +
                    SearchVector('category__name', weight='B') +
                    SearchVector('description', weight='C')
                )
                
                fts_products = CoreProduct.objects.filter(
                    is_active=True
                ).annotate(
                    rank=SearchRank(vector, search_query)
                ).filter(
                    rank__gt=0
                ).select_related('brand', 'category', 'seller').order_by('-rank')[:limit * 2]
                
                for product in fts_products:
                    fts_results.append({
                        'product': product,
                        'fts_score': float(product.rank)
                    })
                    
            except Exception as e:
                logger.warning(f'FTS search failed in hybrid mode: {e}')
            
            # === PART 3: Merge & Score ===
            # Combine results with weighted scoring: 60% AI, 40% FTS
            merged = {}
            
            # Normalize and add AI scores
            if ai_results:
                max_ai = max(r['ai_score'] for r in ai_results)
                for result in ai_results:
                    product_id = result['product'].id
                    normalized_ai = result['ai_score'] / max_ai if max_ai > 0 else 0
                    merged[product_id] = {
                        'product': result['product'],
                        'ai_score': normalized_ai,
                        'fts_score': 0,
                        'combined_score': normalized_ai * 0.6
                    }
            
            # Normalize and add FTS scores
            if fts_results:
                max_fts = max(r['fts_score'] for r in fts_results)
                for result in fts_results:
                    product_id = result['product'].id
                    normalized_fts = result['fts_score'] / max_fts if max_fts > 0 else 0
                    
                    if product_id in merged:
                        merged[product_id]['fts_score'] = normalized_fts
                        merged[product_id]['combined_score'] += normalized_fts * 0.4
                    else:
                        merged[product_id] = {
                            'product': result['product'],
                            'ai_score': 0,
                            'fts_score': normalized_fts,
                            'combined_score': normalized_fts * 0.4
                        }
            
            # Sort by combined score
            final_results = sorted(merged.values(), key=lambda x: x['combined_score'], reverse=True)[:limit]
            
            # Serialize
            serialized_results = []
            for result in final_results:
                product_data = ProductSerializer(result['product']).data
                product_data['ai_score'] = result['ai_score']
                product_data['fts_score'] = result['fts_score']
                product_data['combined_score'] = result['combined_score']
                serialized_results.append(product_data)
            
            return Response({
                'query': query,
                'results': serialized_results,
                'total_found': len(merged),
                'returned': len(serialized_results),
                'search_type': 'hybrid',
                'weights': {'ai': 0.6, 'fts': 0.4}
            })
            
        except Exception as e:
            logger.error(f'Hybrid search error: {str(e)}')
            return Response({
                'error': f'Hybrid search failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def platforms(self, request):
        """Get platforms (all or filtered by category)"""
        category = request.query_params.get('category', '')
        subcategory = request.query_params.get('subcategory', '')
        
        # If category or subcategory parameters are provided, return filtered platforms
        if category or subcategory:
            return self.platforms_by_category(request)
        
        # Otherwise, return all platforms
        # Get platform display names from ecommerce products and Instagram
        ecommerce_platforms = CoreProduct.objects.filter(
            platform_type='ecommerce'
        ).select_related('seller__platform').values_list(
            'seller__platform__display_name', flat=True
        ).distinct()
        
        # Add Instagram for Instagram products
        has_instagram = CoreProduct.objects.filter(platform_type='instagram').exists()
        
        # Combine all platforms
        platforms_set = set()
        for platform in ecommerce_platforms:
            if platform and platform.strip():
                platforms_set.add(platform.strip())
        
        if has_instagram:
            platforms_set.add('Instagram')
        
        platforms_list = sorted(list(platforms_set))
        return Response({'platforms': platforms_list})
    
    @action(detail=False, methods=['get'])
    def platforms_by_category(self, request):
        """Get platforms filtered by category with smart focusing"""
        category = request.query_params.get('category', '')
        subcategory = request.query_params.get('subcategory', '')
        
        # Define specialist platforms for each category based on analysis
        specialists = {
            'Electronics': {
                'all': ['Jalal Electronics', 'New Tokyo Electronics', 'Al Fatah Electronics', 
                       'Al Mumtaz Electronics', 'ShopHive', 'Telemart', 'Friends Home'],
                'Smartphones & Mobiles': ['Jalal Electronics', 'New Tokyo Electronics', 'Al Mumtaz Electronics', 'ShopHive', 'Telemart'],
                'Audio & Accessories': ['Al Fatah Electronics', 'ShopHive', 'Telemart'],
                'Entertainment': ['Jalal Electronics', 'Al Fatah Electronics', 'ShopHive', 'Telemart'],
                'Home Appliances (Large)': ['Al Fatah Electronics', 'Al Mumtaz Electronics', 'Friends Home', 'Jalal Electronics', 'New Tokyo Electronics', 'ShopHive', 'Telemart'],
                'Kitchen Appliances (Small)': ['Al Fatah Electronics', 'Friends Home', 'Jalal Electronics', 'New Tokyo Electronics', 'ShopHive', 'Telemart'],
                'Cooling & Heating': ['Al Fatah Electronics', 'Al Mumtaz Electronics', 'Friends Home', 'Jalal Electronics', 'New Tokyo Electronics', 'ShopHive', 'Telemart'],
                'Laptops & Computers': ['Jalal Electronics', 'New Tokyo Electronics', 'ShopHive', 'Telemart'],
                'Mobile Accessories': ['Al Fatah Electronics', 'Jalal Electronics', 'New Tokyo Electronics', 'ShopHive', 'Telemart']
            },
            'Home & Living': {
                'all': ['Furniture Hub', 'Interwood', 'Wood Action', 'AenZay Homes', 'All In One Store', 
                       'Plant.Pk', 'Plants.com.pk', 'Baghbani.pk', 'etree.pk'],
                'Furniture': ['Furniture Hub', 'Interwood', 'Wood Action', 'AenZay Homes'],
                'Home Decor': ['AenZay Homes', 'Baghbani.pk', 'Wood Action'],
                'Kitchen & Dining': ['All In One Store', 'AenZay Homes', 'Al Fatah Electronics', 'Friends Home', 'Furniture Hub', 'Jalal Electronics', 'New Tokyo Electronics', 'ShopHive', 'Telemart', 'Wood Action'],
                'Gardening & Outdoor': ['Plant.Pk', 'Plants.com.pk', 'Baghbani.pk', 'etree.pk', 'AenZay Homes', 'Al Fatah Electronics', 'Al Mumtaz Electronics', 'Friends Home', 'Furniture Hub', 'Interwood', 'New Tokyo Electronics', 'ShopHive', 'Telemart', 'Wood Action']
            },
            'Sports & Fitness': {
                'all': ['Apollo Sports', 'Ali Sports', 'Sports Plus'],
                'Gym Equipment': ['Apollo Sports', 'Ali Sports', 'Sports Plus'],
                'Sports Gear': ['Apollo Sports', 'Ali Sports', 'Sports Plus'],
                'Sportswear': ['Apollo Sports', 'Ali Sports', 'Sports Plus'],
                'Outdoor & Adventure': ['Apollo Sports', 'Ali Sports', 'Sports Plus']
            },
            'Beauty & Personal Care': {
                'all': ['Missrose Beauty', 'Bigbasket Beauty', 'Shoppingbag Beauty', 'Vincecare Beauty', 
                       'Homeshopping Beauty', 'Thebodyshop Beauty', 'Saeedghani Beauty', 'Darimooch Beauty', 
                       'Hemaniherbals Beauty', 'Scentsnstories Beauty', 'Rozzana Beauty', 'Symbios Beauty'],
                'Makeup': ['Missrose Beauty', 'Bigbasket Beauty', 'Shoppingbag Beauty'],
                'Skincare': ['Vincecare Beauty', 'Homeshopping Beauty', 'Thebodyshop Beauty'],
                'Haircare': ['Saeedghani Beauty', 'Darimooch Beauty', 'Hemaniherbals Beauty'],
                'Fragrances': ['Scentsnstories Beauty', 'Rozzana Beauty', 'Symbios Beauty']
            },
            'Clothing & Fashion': {
                'all': ['Heerpret Fashion', 'Mohagni Fashion', 'Panacheapparels Fashion', 'Furorjeans Fashion', 
                       'Hub Fashion', 'Chasevalue Fashion', 'Peachrepublic Fashion', 'Sclothers Fashion', 
                       'Studiobytcs Fashion', 'Julke Fashion', 'Akgalleria Fashion', 'Lamosaik Fashion', 
                       'Mizajstore Fashion', 'Kayseria Fashion', 'Generation Fashion', 'Bagallery Fashion', 
                       'Shopbrumano Fashion', 'Xessories Fashion', 'Shopmanto Fashion', 'Jeem Fashion', 
                       'Laam Fashion', 'Shomiofficial Fashion'],
                "Men's Wear": ['Heerpret Fashion', 'Mohagni Fashion', 'Panacheapparels Fashion', 'Furorjeans Fashion', 'Hub Fashion', 'Chasevalue Fashion'],
                "Women's Wear": ['Peachrepublic Fashion', 'Sclothers Fashion', 'Studiobytcs Fashion', 'Julke Fashion', 'Akgalleria Fashion', 'Lamosaik Fashion'],
                "Kids Wear": ['Mizajstore Fashion', 'Kayseria Fashion', 'Generation Fashion', 'Bagallery Fashion'],
                "Shoes & Accessories": ['Shopbrumano Fashion', 'Xessories Fashion', 'Shopmanto Fashion', 'Jeem Fashion', 'Laam Fashion', 'Shomiofficial Fashion']
            }
        }
        
        # Get relevant platform list based on request
        if subcategory and category in specialists and subcategory in specialists[category]:
            # Get subcategory-specific platforms
            relevant_platforms = specialists[category][subcategory]
            filter_kwargs = {'category__name': subcategory}
        elif category in specialists:
            # Get category-wide platforms
            relevant_platforms = specialists[category]['all']
            filter_kwargs = {'category__main_category': category}
        else:
            # If a category is provided but not in curated list, still filter by it
            # to avoid returning unrelated platforms from other categories.
            relevant_platforms = []
            if category:
                filter_kwargs = {'category__main_category': category}
            else:
                # No filtering - will fall back to all platforms later
                filter_kwargs = {}
        
        # Get platforms that actually have products matching the filter
        if filter_kwargs:
            actual_platforms = CoreProduct.objects.filter(
                platform_type='ecommerce',
                **filter_kwargs
            ).select_related('seller__platform').values_list(
                'seller__platform__display_name', flat=True
            ).distinct()

            # Strict mode: only show platforms that actually have products in this specific category/subcategory
            platform_list = sorted(list(set([p for p in actual_platforms if p])))
            
            # Additional filtering: exclude platforms that are primarily from other categories
            if category == 'Books & Stationery':
                # Only show book/stationery focused platforms
                book_platforms = ['Caravanbookhouse', 'Vanguardbooks', 'Bookemporium.pk', 'Chasevalue.pk', 
                                'Sangemeel', 'Stationers', 'Thepaperworm', 'Paramountbooks', 'Katib.pk']
                platform_list = [p for p in platform_list if any(bp.lower() in p.lower() for bp in book_platforms)]
            elif category == 'Electronics':
                # Only show electronics focused platforms
                electronics_platforms = ['ShopHive', 'Friends Home', 'Jalal Electronics', 'Al Fatah Electronics', 
                                      'Al Mumtaz Electronics', 'Telemart', 'New Tokyo Electronics']
                platform_list = [p for p in platform_list if any(ep.lower() in p.lower() for ep in electronics_platforms)]
        else:
            # No filtering - return all platforms
            all_platforms = CoreProduct.objects.filter(
                platform_type='ecommerce'
            ).select_related('seller__platform').values_list(
                'seller__platform__display_name', flat=True
            ).distinct()
            platform_list = sorted(list(set([p for p in all_platforms if p])))
        
        # Add Instagram if there are Instagram products in this category
        if filter_kwargs:
            has_instagram = CoreProduct.objects.filter(
                platform_type='instagram',
                **filter_kwargs
            ).exists()
            
            if has_instagram:
                platform_list.append('Instagram')
        
        platforms_list = sorted(list(set(platform_list)))
        return Response({'platforms': platforms_list})
    
    @action(detail=False, methods=['get'])
    def category_mappings(self, request):
        """Get dynamic category mappings from database"""
        from products.models import ProductCategory
        
        # Get all main categories from ProductCategory table
        main_categories = ProductCategory.objects.filter(
            main_category__isnull=False
        ).values_list('main_category', flat=True).distinct()
        
        mappings = {}
        for main_cat in main_categories:
            if main_cat:  # Skip None values
                # Get subcategories for this main category from ProductCategory table
                subcategories = ProductCategory.objects.filter(
                    main_category=main_cat
                ).values_list('name', flat=True).distinct()
                
                # Only include subcategories that have products
                subcategories_with_products = []
                for subcat in subcategories:
                    if (subcat and 
                        CoreProduct.objects.filter(
                            is_active=True,
                            category__name=subcat
                        ).exists()):
                        subcategories_with_products.append(subcat)
                
                if subcategories_with_products:
                    mappings[main_cat] = subcategories_with_products
        
        return Response({
            'mappings': mappings,
            'main_categories': list(mappings.keys())
        })
    
    @action(detail=False, methods=['get'])
    def filter_options(self, request):
        """Get all available filter options (categories, subcategories, etc.)"""
        # Get optional category filter for context-specific options
        main_category = request.query_params.get('main_category', '')
        subcategory = request.query_params.get('subcategory', '')
        
        # Get main categories - use set to ensure uniqueness
        main_categories_raw = CoreProduct.objects.values_list('category__main_category', flat=True).distinct()
        main_categories = list(set([cat for cat in main_categories_raw if cat]))
        
        # Get subcategories - use set to ensure uniqueness
        subcategories_raw = CoreProduct.objects.values_list('category__subcategory', flat=True).distinct()
        subcategories = list(set([subcat for subcat in subcategories_raw if subcat]))
        
        # Get platforms - use seller field (unified approach)
        platforms_raw = CoreProduct.objects.filter(
            is_active=True,
            seller__isnull=False
        ).select_related('seller').values_list(
            'seller__display_name', flat=True
        ).distinct()
        
        # Clean and deduplicate platform names
        platforms_set = set()
        for platform in platforms_raw:
            if platform and platform.strip():
                platforms_set.add(platform.strip())
        
        platforms = sorted(list(platforms_set))
        
        # Get price range
        price_range = CoreProduct.objects.aggregate(
            min_price=models.Min('price'),
            max_price=models.Max('price')
        )
        
        # Get brands - filter by category if provided
        brand_queryset = CoreProduct.objects.filter(
            is_active=True,
            brand__isnull=False
        )
        
        # Filter by category if provided
        if subcategory:
            brand_queryset = brand_queryset.filter(category__name__iexact=subcategory)
        elif main_category:
            brand_queryset = brand_queryset.filter(category__main_category__iexact=main_category)
        
        # Get brands with product count for sorting
        brands_with_count = brand_queryset.select_related('brand').values(
            'brand__display_name'
        ).annotate(
            product_count=models.Count('id')
        ).order_by('-product_count')
        
        # If no category filter, limit to top 100 popular brands
        if not main_category and not subcategory:
            brands_with_count = brands_with_count[:100]
        
        # Extract brand names
        brands = [b['brand__display_name'] for b in brands_with_count if b['brand__display_name']]
        
        return Response({
            'main_categories': sorted(main_categories),  # Sort for consistent order
            'subcategories': sorted(subcategories),      # Sort for consistent order
            'platforms': platforms,                      # Already sorted
            'brands': brands,                            # Sorted brand list
            'price_range': {
                'min': float(price_range['min_price']) if price_range['min_price'] else 0,
                'max': float(price_range['max_price']) if price_range['max_price'] else 0
            }
        })
    
    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def track_view(self, request, pk=None):
        """Track product view - increments view count"""
        try:
            product = self.get_object()
            # Use F() expression to avoid race conditions
            CoreProduct.objects.filter(pk=product.pk).update(
                view_count=F('view_count') + 1
            )
            return Response({'status': 'view tracked', 'product_id': product.id})
        except Exception as e:
            logger.error(f"Error tracking view for product {pk}: {str(e)}")
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def trending(self, request):
        """Get trending products based on view counts + wishlist counts"""
        from django.db.models import Q
        from django.db.models.functions import Coalesce
        from decimal import Decimal
        
        try:
            # Calculate trending score: views + (wishlists * 3)
            # Wishlists weighted higher as they show stronger purchase intent
            products = CoreProduct.objects.filter(
                is_active=True,
                main_image_url__isnull=False
            ).exclude(
                Q(main_image_url='') | 
                Q(main_image_url='null') | 
                Q(main_image_url='undefined') |
                # Exclude placeholder images
                Q(main_image_url__startswith='data:image/gif;base64,R0lGODlhAQABAAAA') |
                Q(main_image_url__contains='placeholder.com') |
                Q(main_image_url__contains='via.placeholder') |
                # Exclude price outliers (NULL prices are OK - they show "Visit for Price")
                Q(price__gt=Decimal('100000000')) |  # Exclude prices above 100 million (likely scraping errors)
                Q(price__lt=Decimal('50'))  # Exclude prices below 50 (likely errors, except NULL)
            ).annotate(
                # Use Coalesce to handle NULL values (treat as 0)
                trending_score=(
                    Coalesce(F('view_count'), 0) + 
                    (Coalesce(F('wishlist_count'), 0) * 3)
                )
            ).filter(
                trending_score__gt=0  # Only products with some activity
            ).select_related(
                'brand', 'category', 'seller'
            ).order_by('-trending_score')[:12]
            
            # Fallback to newest products if no trending data yet (with same quality filters)
            if products.count() < 3:
                products = CoreProduct.objects.filter(
                    is_active=True,
                    main_image_url__isnull=False
                ).exclude(
                    Q(main_image_url='') | 
                    Q(main_image_url='null') | 
                    Q(main_image_url='undefined') |
                    # Exclude placeholder images
                    Q(main_image_url__startswith='data:image/gif;base64,R0lGODlhAQABAAAA') |
                    Q(main_image_url__contains='placeholder.com') |
                    Q(main_image_url__contains='via.placeholder') |
                    # Exclude price outliers
                    Q(price__gt=Decimal('100000000')) |
                    Q(price__lt=Decimal('50'))
                ).select_related(
                    'brand', 'category', 'seller'
                ).order_by('-created_at')[:12]
            
            serializer = self.get_serializer(products, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error fetching trending products: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for categories - read-only"""
    queryset = ProductCategory.objects.all()
    serializer_class = CategorySerializer

class WishlistViewSet(viewsets.ModelViewSet):
    """ViewSet for user wishlist"""
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def add_product(self, request):
        """Add a product to wishlist"""
        product_id = request.data.get('product_id')
        if not product_id:
            return Response({'error': 'product_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            product = CoreProduct.objects.get(id=product_id)
        except CoreProduct.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        
        wishlist_item, created = Wishlist.objects.get_or_create(
            user=request.user,
            product=product
        )
        
        if created:
            serializer = self.get_serializer(wishlist_item)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response({'message': 'Product already in wishlist'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['delete'])
    def remove_product(self, request):
        """Remove a product from wishlist"""
        product_id = request.data.get('product_id')
        if not product_id:
            return Response({'error': 'product_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            wishlist_item = Wishlist.objects.get(user=request.user, product_id=product_id)
            wishlist_item.delete()
            return Response({'message': 'Product removed from wishlist'}, status=status.HTTP_200_OK)
        except Wishlist.DoesNotExist:
            return Response({'error': 'Product not in wishlist'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_scraped_products(request):
    """
    Get products that were scraped from Instagram
    """
    try:
        # Get scraped products with deduplication
        scraped_products = CoreProduct.objects.filter(is_active=True)
        
        # Apply filters
        category = request.query_params.get('category')
        if category:
            scraped_products = scraped_products.filter(category__name__icontains=category)
        
        platform = request.query_params.get('platform')
        if platform:
            # Filter by Instagram platform
            if platform.lower() == 'instagram':
                scraped_products = scraped_products.filter(platform_type='instagram')
            else:
                # Filter by ecommerce platform display name
                scraped_products = scraped_products.filter(
                    platform_type='ecommerce',
                    ecommerce_data__platform__display_name__icontains=platform
                )
        
        # Search functionality
        search = request.query_params.get('search')
        if search:
            scraped_products = scraped_products.filter(
                models.Q(name__icontains=search) |
                models.Q(description__icontains=search) |
                models.Q(instagram_data__caption__icontains=search)
            )
        
        # Deduplication: For products with same name+seller, prefer the one with:
        # 1. Has ecommerce_data.platform_url (most complete)
        # 2. Has main_image_url (has image)
        # 3. Most recent created_at
        scraped_products = scraped_products.annotate(
            has_url=Case(
                When(ecommerce_data__platform_url__isnull=False, ecommerce_data__platform_url__gt='', then=1),
                default=0,
                output_field=IntegerField()
            ),
            has_image=Case(
                When(main_image_url__isnull=False, main_image_url__gt='', then=1),
                default=0,
                output_field=IntegerField()
            )
        ).order_by(
            'seller_id', 'name',  # Group by seller+name
            '-has_url',           # Prefer products with URLs
            '-has_image',         # Then prefer products with images
            '-created_at'         # Finally prefer newest
        ).distinct('seller_id', 'name')  # Take only the first (best) from each group
        
        # Pagination
        page_size = int(request.query_params.get('page_size', 20))
        page = int(request.query_params.get('page', 1))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        products_page = scraped_products[start:end]
        
        serializer = ProductSerializer(products_page, many=True)
        
        return Response({
            'success': True,
            'products': serializer.data,
            'total_count': scraped_products.count(),
            'page': page,
            'page_size': page_size,
            'has_next': end < scraped_products.count()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in get_scraped_products view: {str(e)}")
        return Response({
            'success': False,
            'message': f'Failed to fetch products: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def scraping_status(request):
    """
    Get scraping status and statistics
    """
    try:
        total_products = CoreProduct.objects.count()
        scraped_products = CoreProduct.objects.filter(is_active=True).count()
        dummy_products = CoreProduct.objects.filter(is_active=False).count()
        
        # Get latest scraping info
        latest_scraped = CoreProduct.objects.filter(is_active=True).order_by('-last_scraped').first()
        
        return Response({
            'success': True,
            'statistics': {
                'total_products': total_products,
                'scraped_products': scraped_products,
                'dummy_products': dummy_products,
                'scraping_percentage': round((scraped_products / total_products * 100) if total_products > 0 else 0, 2)
            },
            'latest_scraping': {
                'last_scraped_product': latest_scraped.name if latest_scraped else None,
                'last_scraped_time': latest_scraped.last_scraped if latest_scraped else None
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in scraping_status view: {str(e)}")
        return Response({
            'success': False,
            'message': f'Failed to get status: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@cache_page(60 * 60 * 24)  # Cache for 24 hours
def proxy_image(request, image_url):
    """
    Proxy endpoint to serve remote images from approved hosts to bypass CORS.
    Allowed hosts: Instagram CDN, ShopHive media, Telemart CloudFront.
    """
    try:
        # Decode the URL (it might be URL-encoded)
        decoded_url = urllib.parse.unquote(image_url)
        logger.info(f"Proxy request for URL: {decoded_url}")
        
        # Validate host against whitelist
        from urllib.parse import urlparse
        parsed = urlparse(decoded_url)
        host = parsed.netloc.lower()
        allowed_hosts = (
            'cdninstagram.com',            # Instagram CDN
            'scontent.cdninstagram.com',   # Alternate Instagram CDN
            'www.shophive.com',            # ShopHive site media
            'shophive.com',
            'd1iv6qgcmtzm6l.cloudfront.net',  # Telemart CloudFront
            'cdn.shopify.com',              # Shopify CDN (e.g., FriendsHome)
            'friendshome.pk',               # Friends Home main domain
            'www.friendshome.pk',
            'newtokyo.pk',                  # New Tokyo
            'www.newtokyo.pk',
            'www.almumtaz.com.pk',          # Al Mumtaz
            'almumtaz.com.pk',
            'woodaction.com',               # Wood Action
            'www.woodaction.com',
            'alfatah.pk',                   # Al Fatah uploads
            'alfatah.com.pk',               # Al Fatah alt domain
            'www.alfatah.com.pk',
            'furniturehub.pk',              # FurnitureHub
            'www.furniturehub.pk',
            'i0.wp.com',                    # WordPress CDN used by some vendors
            'interwood.pk',                 # Interwood
            'www.interwood.pk',
            'allinonestore.pk',             # All In One Store
            'www.allinonestore.pk',
            'plant.pk',                     # Plant.Pk
            'www.plant.pk',
            'plants.com.pk',                # Plants.com.pk
            'www.plants.com.pk',
            'baghbani.pk',                  # Baghbani.pk
            'www.baghbani.pk',
            'etree.pk',                     # etree.pk
            'www.etree.pk',
            'apollosports.pk',              # Apollo Sports
            'www.apollosports.pk',
            'alisports.pk',                 # Ali Sports
            'www.alisports.pk',
            'sportsplus.pk',                # Sports Plus
            'www.sportsplus.pk',
            'theirongear.com',              # IRONGEAR Fitness
            'www.theirongear.com',
            'speedsports.pk',               # SPL - Speed (Pvt.) Ltd.
            'www.speedsports.pk',
            'fitnessdepot.pk',              # Fitness Depot
            'www.fitnessdepot.pk',
            'advancefitness.pk',            # Advance Fitness
            'www.advancefitness.pk',
            'lifefitnesspk.com',             # Life Fitness PK
            'www.lifefitnesspk.com',
            'altimateoutdoors.pk',            # Altimate Outdoors
            'www.altimateoutdoors.pk',
            'shimshaladventureshop.com',      # Shimshal Adventure Shop
            'www.shimshaladventureshop.com',
            'higher.com.pk',                  # Higher Adventure
            'www.higher.com.pk',
            'dominance.pk',                   # Dominance.pk
            'www.dominance.pk',
            'missrose.com.pk',                # Miss Rose Beauty
            'www.missrose.com.pk',
            'bigbasket.pk',                  # Big Basket Beauty
            'www.bigbasket.pk',
            'shoppingbag.pk',                # Shopping Bag Beauty
            'www.shoppingbag.pk',
            'vincecare.com',                 # Vince Care Beauty
            'www.vincecare.com',
            'homeshopping.pk',               # Home Shopping Beauty
            'www.homeshopping.pk',
            'thebodyshop.pk',                # The Body Shop Beauty
            'www.thebodyshop.pk',
            'saeedghani.pk',                 # Saeed Ghani Beauty
            'www.saeedghani.pk',
            'darimooch.com',                 # Darimooch Beauty
            'www.darimooch.com',
            'hemaniherbals.com',            # Hemani Herbals Beauty
            'www.hemaniherbals.com',
            'scentsnstories.pk',            # Scents & Stories Beauty
            'www.scentsnstories.pk',
            'rozzana.pk',                   # Rozzana Beauty
            'www.rozzana.pk',
            'symbios.pk',                   # Symbios Beauty
            'www.symbios.pk',
            'heerpret.com',                  # Heerpret Fashion
            'www.heerpret.com',
            'mohagni.com',                   # Mohagni Fashion
            'www.mohagni.com',
            'panacheapparels.com',           # Panache Apparels Fashion
            'www.panacheapparels.com',
            'furorjeans.com',                # Furor Jeans Fashion
            'www.furorjeans.com',
            'hub.com.pk',                    # Hub Fashion
            'www.hub.com.pk',
            'chasevalue.pk',                 # Chase Value Fashion
            'www.chasevalue.pk',
            'peachrepublic.pk',              # Peach Republic Fashion
            'www.peachrepublic.pk',
            'sclothers.com',                 # SC Lothers Fashion
            'www.sclothers.com',
            'studiobytcs.com',               # Studio By TCS Fashion
            'www.studiobytcs.com',
            'julke.pk',                      # Julke Fashion
            'www.julke.pk',
            'akgalleria.com',                # AK Galleria Fashion
            'www.akgalleria.com',
            'lamosaik.com',                  # Lamo Saik Fashion
            'www.lamosaik.com',
            'mizajstore.com',                # Mizaj Store Fashion
            'www.mizajstore.com',
            'kayseria.com',                  # Kayseria Fashion
            'www.kayseria.com',
            'generation.com.pk',             # Generation Fashion
            'www.generation.com.pk',
            'bagallery.com',                 # Bagallery Fashion
            'www.bagallery.com',
            'shopbrumano.com',               # Shop Brumano Fashion
            'www.shopbrumano.com',
            'xessories.pk',                  # Xessories Fashion
            'www.xessories.pk',
            'shopmanto.com',                 # Shop Manto Fashion
            'www.shopmanto.com',
            'jeem.pk',                       # Jeem Fashion
            'www.jeem.pk',
            'laam.pk',                       # Laam Fashion
            'www.laam.pk',
            'shomiofficial.com'              # Shomi Official Fashion
            , 'stationers.pk'
            , 'www.stationers.pk'
            , 'paperclip.pk'
            , 'www.paperclip.pk'
            , 'thepaperworm.com'
            , 'www.thepaperworm.com'
            , 'bookemporium.pk'
            , 'www.bookemporium.pk'
            , 'vanguardbooks.com'
            , 'www.vanguardbooks.com'
            , 'paramountbooks.com.pk'
            , 'www.paramountbooks.com.pk'
            , 'caravanbookhouse.com'
            , 'www.caravanbookhouse.com'
            , 'sangemeel.com'
            , 'www.sangemeel.com'
            , 'sangemeel.shop'
            , 'www.sangemeel.shop'
            # Toys & Games domains
            , 'toyzone.pk'
            , 'www.toyzone.pk'
            , 'bachaaparty.com'
            , 'www.bachaaparty.com'
            , 'toynix.pk'
            , 'www.toynix.pk'
            , 'theentertainer.pk'
            , 'www.theentertainer.pk'
            , 'toyishland.com'
            , 'www.toyishland.com'
            , 'onetoystore.com'
            , 'www.onetoystore.com'
            , 'khanaan.pk'
            , 'www.khanaan.pk'
            , 'joystory.pk'
            , 'www.joystory.pk'
            , 'lahoretoys.com'
            , 'www.lahoretoys.com'
            , 'alfatah.pk'
            , 'www.alfatah.pk'
            , 'toygenix.com.pk'
            , 'www.toygenix.com.pk'
            , 'brudertoyshop.uk'
            , 'www.brudertoyshop.uk'
            # Automobiles & Accessories domains
            , 'sehgalmotors.pk'
            , 'www.sehgalmotors.pk'
            , 'vroom.pk'
            , 'www.vroom.pk'
            , 'autostore.pk'
            , 'www.autostore.pk'
            , 'autokings.pk'
            , 'www.autokings.pk'
            , 'cardekho.com.pk'
            , 'www.cardekho.com.pk'
            , 'pakwheels.com'
            , 'www.pakwheels.com'
            , 'cache1.pakwheels.com'  # PakWheels CDN cache servers
            , 'cache2.pakwheels.com'
            , 'cache3.pakwheels.com'
            , 'cache4.pakwheels.com'
            , 'scontent.flhe5-1.fna.fbcdn.net'  # Facebook CDN (for some products)
            , 'via.placeholder.com'  # Placeholder images
        )

        if not any(h in host for h in allowed_hosts):
            logger.warning(f"Blocked proxy for non-whitelisted host: {host}")
            raise Http404("Invalid image host")
        
        # Fetch the image from remote host with increased timeout
        response = requests.get(decoded_url, timeout=30, stream=True)
        response.raise_for_status()
        
        # Set appropriate headers
        http_response = HttpResponse(
            response.content,
            content_type=response.headers.get('content-type', 'image/jpeg')
        )
        
        # Add cache headers
        http_response['Cache-Control'] = 'public, max-age=86400'  # 24 hours
        http_response['Access-Control-Allow-Origin'] = '*'  # Allow CORS
        
        return http_response
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch image from {image_url}: {e}")
        raise Http404("Image not found")
    except Exception as e:
        logger.error(f"Error in proxy_image: {e}")
        raise Http404("Image not found")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def scrape_instagram(request):
    """
    Scrape Instagram posts using Apify or other services
    """
    try:
        usernames = request.data.get('usernames', [])
        max_posts = request.data.get('max_posts', 50)
        
        if not usernames:
            return Response({
                'success': False,
                'message': 'Usernames are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if Apify API token is configured
        apify_token = getattr(settings, 'APIFY_API_TOKEN', '')
        if not apify_token:
            return Response({
                'success': False,
                'message': 'Instagram scraping is not configured. Please set APIFY_API_TOKEN in environment variables.'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # For now, return a placeholder response
        # In a real implementation, this would call the Apify API or your Instagram scraper
        logger.info(f"Instagram scraping requested for usernames: {usernames}, max_posts: {max_posts}")
        
        return Response({
            'success': True,
            'message': f'Instagram scraping initiated for {len(usernames)} usernames',
            'usernames': usernames,
            'max_posts': max_posts,
            'note': 'This is a placeholder response. Implement actual Instagram scraping logic here.'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in scrape_instagram: {str(e)}")
        return Response({
            'success': False,
            'message': f'Instagram scraping failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def scrape_website(request):
    """
    Intelligent website scraping endpoint
    """
    try:
        website_url = request.data.get('website_url')
        platform_name = request.data.get('platform_name')
        categories = request.data.get('categories', [])
        max_pages = request.data.get('max_pages', 5)
        headless = request.data.get('headless', True)
        
        if not website_url or not platform_name or not categories:
            return Response({
                'success': False,
                'message': 'website_url, platform_name, and categories are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # This would integrate with the intelligent scraper
        logger.info(f"Intelligent scraping requested for {website_url} - {platform_name}")
        
        # For now, return a placeholder response
        return Response({
            'success': True,
            'message': f'Intelligent scraping initiated for {platform_name}',
            'website_url': website_url,
            'platform_name': platform_name,
            'categories': categories,
            'max_pages': max_pages,
            'headless': headless,
            'job_id': f'job_{int(time.time())}',
            'note': 'This is a placeholder response. Implement actual intelligent scraping logic here.'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in scrape_website: {str(e)}")
        return Response({
            'success': False,
            'message': f'Website scraping failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_scraping_jobs(request):
    """
    Get active scraping jobs
    """
    try:
        # This would return actual scraping jobs from database or queue
        jobs = [
            {
                'id': 'job_1',
                'type': 'instagram',
                'status': 'running',
                'progress': 45,
                'started_at': timezone.now().isoformat(),
                'platform': 'Instagram'
            }
        ]
        
        return Response({
            'success': True,
            'jobs': jobs
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in get_scraping_jobs: {str(e)}")
        return Response({
            'success': False,
            'message': f'Failed to get scraping jobs: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_scraping_history(request):
    """
    Get scraping history
    """
    try:
        # This would return actual scraping history from database
        history = [
            {
                'id': 1,
                'type': 'instagram',
                'platform': 'Instagram',
                'status': 'completed',
                'timestamp': timezone.now().isoformat(),
                'products_found': 25
            },
            {
                'id': 2,
                'type': 'intelligent',
                'platform': 'Example Store',
                'status': 'completed',
                'timestamp': timezone.now().isoformat(),
                'products_found': 150
            }
        ]
        
        return Response({
            'success': True,
            'history': history
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in get_scraping_history: {str(e)}")
        return Response({
            'success': False,
            'message': f'Failed to get scraping history: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
