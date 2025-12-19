#!/usr/bin/env python3
"""
Generate AI embeddings for products
Run: python manage.py generate_embeddings
"""

from django.core.management.base import BaseCommand
from products.models import CoreProduct
from django.db.models import Q
import numpy as np
import pickle
from sentence_transformers import SentenceTransformer
import time
from tqdm import tqdm


class Command(BaseCommand):
    help = 'Generate AI embeddings for product search'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of products to process at once (default 100)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate embeddings even if they already exist'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of products to process (for testing)'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        force = options['force']
        limit = options['limit']

        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('🧠 GENERATING AI EMBEDDINGS FOR PRODUCTS'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write('')

        # Load model
        self.stdout.write(self.style.WARNING('📦 Loading AI model...'))
        try:
            model = SentenceTransformer('all-MiniLM-L6-v2')
            self.stdout.write(self.style.SUCCESS('✅ Model loaded: all-MiniLM-L6-v2'))
            self.stdout.write('')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to load model: {e}'))
            return

        # Get products to process
        self.stdout.write(self.style.WARNING('📊 Fetching products...'))
        
        queryset = CoreProduct.objects.filter(is_active=True).exclude(
            Q(name='') | Q(name__isnull=True)
        )
        
        if not force:
            queryset = queryset.filter(search_embedding__isnull=True)
        
        if limit:
            queryset = queryset[:limit]
        
        total_products = queryset.count()
        
        if total_products == 0:
            self.stdout.write(self.style.WARNING('✅ All products already have embeddings!'))
            self.stdout.write(self.style.SUCCESS('   Use --force to regenerate'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'✅ Found {total_products} products to process'))
        self.stdout.write('')

        # Process in batches
        self.stdout.write(self.style.WARNING(f'🔄 Processing in batches of {batch_size}...'))
        self.stdout.write('')
        
        start_time = time.time()
        
        products = list(queryset.select_related('brand', 'category'))
        
        # Create progress bar
        with tqdm(total=len(products), desc="Generating embeddings", unit="product") as pbar:
            for i in range(0, len(products), batch_size):
                batch = products[i:i + batch_size]
                
                # Generate texts for embedding
                texts = []
                for product in batch:
                    text = f"{product.name}"
                    if product.brand:
                        text += f" {product.brand.display_name}"
                    if product.category:
                        text += f" {product.category.name}"
                    if product.description:
                        text += f" {product.description[:200]}"
                    texts.append(text)
                
                # Generate embeddings
                embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
                
                # Save to database
                for product, embedding in zip(batch, embeddings):
                    # Store as pickled numpy array
                    product.search_embedding = pickle.dumps(embedding)
                    product.save(update_fields=['search_embedding'])
                
                # Update progress bar
                pbar.update(len(batch))
                
                # Update speed in progress bar
                elapsed = time.time() - start_time
                speed = (i + len(batch)) / elapsed if elapsed > 0 else 0
                pbar.set_postfix({'speed': f'{speed:.1f} prod/s'})
        
        elapsed = time.time() - start_time
        processed = len(products)
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('✅ EMBEDDINGS GENERATED SUCCESSFULLY'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(f'Total products: {processed}')
        self.stdout.write(f'Time taken: {elapsed:.2f} seconds')
        self.stdout.write(f'Average speed: {processed/elapsed:.1f} products/second')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('💡 Next: Test AI search with:'))
        self.stdout.write('   python manage.py test_ai_search --query="your search"')
        self.stdout.write('')

