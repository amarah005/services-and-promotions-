#!/usr/bin/env python3
"""
Test script for AI Search functionality
Run this to verify backend AI search is working correctly
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'buyvaulthub.settings')
django.setup()

from django.test import RequestFactory
from products.views import ProductViewSet
from rest_framework.test import APIRequestFactory
import json

def test_ai_search(query):
    """Test AI search endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing AI Search for: '{query}'")
    print(f"{'='*60}\n")
    
    # Create request factory
    factory = APIRequestFactory()
    
    # Create request
    request = factory.get('/api/v1/products/ai_search/', {'q': query, 'limit': 20})
    
    # Create viewset instance
    viewset = ProductViewSet()
    viewset.request = request
    viewset.format_kwarg = None
    
    try:
        # Call ai_search method
        response = viewset.ai_search(request)
        
        # Get response data
        if hasattr(response, 'data'):
            data = response.data
        else:
            data = json.loads(response.content.decode())
        
        print(f"✅ Response Status: {response.status_code}")
        print(f"\n📊 Response Data:")
        print(f"   Query: {data.get('query', 'N/A')}")
        print(f"   Total Found: {data.get('total_found', 0)}")
        print(f"   Returned: {data.get('returned', 0)}")
        
        results = data.get('results', [])
        
        if results:
            print(f"\n🎯 Top 5 Results:")
            for i, result in enumerate(results[:5], 1):
                name = result.get('name', 'N/A')[:60]
                similarity = result.get('similarity_score', 0)
                price = result.get('price', 'N/A')
                print(f"   {i}. {name}")
                print(f"      Similarity: {similarity:.4f} | Price: {price}")
        else:
            print(f"\n❌ No results found!")
            print(f"   This might indicate:")
            print(f"   - No products with embeddings in database")
            print(f"   - Query didn't match any products")
            print(f"   - Embeddings not generated yet")
        
        return response
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    # Test queries
    test_queries = [
        "gift ideas for tech lovers",
        "samsung phone",
        "laptop",
        "electronics",
        "smartphone"
    ]
    
    print("🧪 AI Search Backend Test")
    print("=" * 60)
    
    for query in test_queries:
        test_ai_search(query)
        print("\n")
    
    print("=" * 60)
    print("✅ Test Complete!")

