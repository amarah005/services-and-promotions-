#!/usr/bin/env python3
"""
Compare all three search methods side-by-side
Tests: Regular Search vs AI Search vs Hybrid Search
"""

from django.core.management.base import BaseCommand
from products.models import CoreProduct
from django.db.models import Q
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from products.utils.search_utils import expand_query_synonyms
import numpy as np
import pickle
from sentence_transformers import SentenceTransformer
import time


class Command(BaseCommand):
    help = 'Compare Regular, AI, and Hybrid search methods'

    def add_arguments(self, parser):
        parser.add_argument(
            '--query',
            type=str,
            default='samsung phone',
            help='Search query to test'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=5,
            help='Number of results to show per method'
        )

    def handle(self, *args, **options):
        query = options['query']
        limit = options['limit']

        self.stdout.write(self.style.SUCCESS('=' * 100))
        self.stdout.write(self.style.SUCCESS('🔍 SEARCH METHODS COMPARISON'))
        self.stdout.write(self.style.SUCCESS('=' * 100))
        self.stdout.write(f'\nQuery: "{query}"')
        self.stdout.write(f'Showing top {limit} results from each method\n')

        # Load AI model once
        self.stdout.write('Loading AI model...')
        model = SentenceTransformer('all-MiniLM-L6-v2')
        self.stdout.write('✅ Model loaded\n')

        # ========================================================================
        # METHOD 1: Regular PostgreSQL Full-Text Search
        # ========================================================================
        self.stdout.write(self.style.WARNING('=' * 100))
        self.stdout.write(self.style.WARNING('METHOD 1: Regular PostgreSQL Full-Text Search (Current)'))
        self.stdout.write(self.style.WARNING('=' * 100))
        
        start = time.time()
        try:
            expanded = expand_query_synonyms(query)
            search_query = SearchQuery(' '.join(expanded), search_type='plain')
            vector = (
                SearchVector('name', weight='A') +
                SearchVector('brand__name', weight='B') +
                SearchVector('category__name', weight='B') +
                SearchVector('description', weight='C')
            )
            
            regular_results = CoreProduct.objects.filter(
                is_active=True
            ).annotate(
                rank=SearchRank(vector, search_query)
            ).filter(
                rank__gt=0
            ).select_related('brand', 'category').order_by('-rank')[:limit]
            
            regular_time = (time.time() - start) * 1000
            
            self.stdout.write(f'\n⏱️  Search time: {regular_time:.1f}ms')
            self.stdout.write(f'📊 Results found: {regular_results.count()}\n')
            
            for i, product in enumerate(regular_results, 1):
                brand = product.brand.display_name if product.brand else "No Brand"
                category = product.category.name if product.category else "No Category"
                price = f"₨{product.price:,.0f}" if product.price else "N/A"
                
                self.stdout.write(f'{i}. {product.name[:70]}')
                self.stdout.write(f'   Brand: {brand} | Category: {category} | Price: {price}')
                self.stdout.write(f'   FTS Rank: {product.rank:.4f}\n')
                
        except Exception as e:
            regular_time = 0
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}\n'))

        # ========================================================================
        # METHOD 2: AI Semantic Search
        # ========================================================================
        self.stdout.write(self.style.WARNING('=' * 100))
        self.stdout.write(self.style.WARNING('METHOD 2: AI Semantic Search'))
        self.stdout.write(self.style.WARNING('=' * 100))
        
        start = time.time()
        try:
            query_embedding = model.encode(query, convert_to_numpy=True)
            
            products = CoreProduct.objects.filter(
                is_active=True,
                search_embedding__isnull=False
            ).select_related('brand', 'category')
            
            # Optimized vectorized approach
            product_list = list(products)
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
                
                results = [
                    {'product': product, 'similarity': float(sim)}
                    for product, sim in zip(valid_products, similarities)
                ]
                results.sort(key=lambda x: x['similarity'], reverse=True)
            else:
                results = []
            
            ai_results = results[:limit]
            
            ai_time = (time.time() - start) * 1000
            
            self.stdout.write(f'\n⏱️  Search time: {ai_time:.1f}ms')
            self.stdout.write(f'📊 Results found: {len(results)}\n')
            
            for i, result in enumerate(ai_results, 1):
                product = result['product']
                brand = product.brand.display_name if product.brand else "No Brand"
                category = product.category.name if product.category else "No Category"
                price = f"₨{product.price:,.0f}" if product.price else "N/A"
                
                self.stdout.write(f'{i}. {product.name[:70]}')
                self.stdout.write(f'   Brand: {brand} | Category: {category} | Price: {price}')
                self.stdout.write(f'   Similarity: {result["similarity"]:.4f} ({result["similarity"]*100:.1f}%)\n')
                
        except Exception as e:
            ai_time = 0
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}\n'))

        # ========================================================================
        # METHOD 3: Hybrid Search (AI + PostgreSQL)
        # ========================================================================
        self.stdout.write(self.style.WARNING('=' * 100))
        self.stdout.write(self.style.WARNING('METHOD 3: Hybrid Search (60% AI + 40% PostgreSQL)'))
        self.stdout.write(self.style.WARNING('=' * 100))
        
        start = time.time()
        try:
            # AI part (optimized vectorized)
            query_embedding = model.encode(query, convert_to_numpy=True)
            products_with_embeddings = list(CoreProduct.objects.filter(
                is_active=True,
                search_embedding__isnull=False
            ).select_related('brand', 'category')[:1000])
            
            embeddings_matrix = []
            valid_products = []
            
            for product in products_with_embeddings:
                try:
                    embedding = pickle.loads(product.search_embedding)
                    embeddings_matrix.append(embedding)
                    valid_products.append(product)
                except:
                    continue
            
            ai_results_dict = {}
            if embeddings_matrix:
                embeddings_array = np.array(embeddings_matrix)
                embeddings_norm = embeddings_array / np.linalg.norm(embeddings_array, axis=1, keepdims=True)
                query_norm = query_embedding / np.linalg.norm(query_embedding)
                similarities = np.dot(embeddings_norm, query_norm)
                
                for product, sim in zip(valid_products, similarities):
                    ai_results_dict[product.id] = {
                        'product': product,
                        'ai_score': float(sim)
                    }
            
            # FTS part
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
            ).select_related('brand', 'category').order_by('-rank')[:limit * 2]
            
            # Merge with scoring
            merged = {}
            
            if ai_results_dict:
                max_ai = max(r['ai_score'] for r in ai_results_dict.values())
                for pid, result in ai_results_dict.items():
                    normalized_ai = result['ai_score'] / max_ai if max_ai > 0 else 0
                    merged[pid] = {
                        'product': result['product'],
                        'ai_score': normalized_ai,
                        'fts_score': 0,
                        'combined': normalized_ai * 0.6
                    }
            
            if fts_products:
                max_fts = max(float(p.rank) for p in fts_products)
                for product in fts_products:
                    normalized_fts = float(product.rank) / max_fts if max_fts > 0 else 0
                    if product.id in merged:
                        merged[product.id]['fts_score'] = normalized_fts
                        merged[product.id]['combined'] += normalized_fts * 0.4
                    else:
                        merged[product.id] = {
                            'product': product,
                            'ai_score': 0,
                            'fts_score': normalized_fts,
                            'combined': normalized_fts * 0.4
                        }
            
            hybrid_results = sorted(merged.values(), key=lambda x: x['combined'], reverse=True)[:limit]
            
            hybrid_time = (time.time() - start) * 1000
            
            self.stdout.write(f'\n⏱️  Search time: {hybrid_time:.1f}ms')
            self.stdout.write(f'📊 Results found: {len(merged)}\n')
            
            for i, result in enumerate(hybrid_results, 1):
                product = result['product']
                brand = product.brand.display_name if product.brand else "No Brand"
                category = product.category.name if product.category else "No Category"
                price = f"₨{product.price:,.0f}" if product.price else "N/A"
                
                self.stdout.write(f'{i}. {product.name[:70]}')
                self.stdout.write(f'   Brand: {brand} | Category: {category} | Price: {price}')
                self.stdout.write(f'   Combined: {result["combined"]:.4f} (AI: {result["ai_score"]:.2f}, FTS: {result["fts_score"]:.2f})\n')
                
        except Exception as e:
            hybrid_time = 0
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}\n'))

        # ========================================================================
        # PERFORMANCE SUMMARY
        # ========================================================================
        self.stdout.write(self.style.SUCCESS('=' * 100))
        self.stdout.write(self.style.SUCCESS('📊 PERFORMANCE SUMMARY'))
        self.stdout.write(self.style.SUCCESS('=' * 100))
        self.stdout.write('')
        self.stdout.write(f'Regular Search (PostgreSQL FTS):  {regular_time:.1f}ms')
        self.stdout.write(f'AI Semantic Search:                {ai_time:.1f}ms')
        self.stdout.write(f'Hybrid Search (Both Combined):     {hybrid_time:.1f}ms')
        self.stdout.write('')
        
        if regular_time and ai_time and hybrid_time:
            fastest = min(regular_time, ai_time, hybrid_time)
            if fastest == regular_time:
                winner = "Regular Search"
            elif fastest == ai_time:
                winner = "AI Search"
            else:
                winner = "Hybrid Search"
            
            self.stdout.write(self.style.SUCCESS(f'🏆 Fastest: {winner} ({fastest:.1f}ms)'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 100))
        self.stdout.write(self.style.SUCCESS('💡 RECOMMENDATIONS'))
        self.stdout.write(self.style.SUCCESS('=' * 100))
        self.stdout.write('')
        self.stdout.write('• Use Regular Search for: Exact keyword matches, category filtering')
        self.stdout.write('• Use AI Search for: Typos, semantic meaning, similar products')
        self.stdout.write('• Use Hybrid Search for: Best overall results (combines both strengths)')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('🧪 Try more test queries:'))
        self.stdout.write('   python manage.py compare_search_methods --query="cheap laptop"')
        self.stdout.write('   python manage.py compare_search_methods --query="ac for bedroom"')
        self.stdout.write('   python manage.py compare_search_methods --query="samung phone" # typo test')
        self.stdout.write('')

