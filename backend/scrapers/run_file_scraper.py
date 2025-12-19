#!/usr/bin/env python3
"""
File-based scraper runner
Automatically discovers and scrapes all categories from JSON config
"""

import sys
import os
import json
import time

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from unified_scraper import UnifiedScraper

def main():
    print("🚀 BuyVaultHub File-Based Scraper")
    print("=" * 50)
    
    # Get platform from command line or default to almumtaz
    platform = sys.argv[1] if len(sys.argv) > 1 else 'almumtaz'
    
    print(f"📋 Platform: {platform}")
    
    # Check if config file exists
    config_path = os.path.join('configs', f'{platform}.json')
    if not os.path.exists(config_path):
        print(f"❌ Config file not found: {config_path}")
        return 1
    
    # Load config to show categories
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Show discovered categories
    categories = []
    category_paths = config.get('category_paths', {})
    for category_name in category_paths.keys():
        if category_name != 'default':
            categories.append(category_name)
    
    print(f"🔍 Auto-discovered categories: {len(categories)}")
    for i, cat in enumerate(categories, 1):
        print(f"   {i}. {cat}")
    
    # Get max pages from command line or default to 2
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    
    print(f"📄 Max pages per category: {max_pages}")
    print(f"🤖 Headless mode: True")
    print()
    
    # Create and run scraper
    scraper = UnifiedScraper(headless=True)
    
    try:
        print("🕷️  Starting file-based scraping...")
        start_time = time.time()
        
        # Scrape all categories automatically (categories=None means auto-discover)
        products = scraper.scrape_products(
            platform_name=platform,
            categories=None,  # Auto-discover from config
            max_pages=max_pages
        )
        
        # Export to CSV
        csv_file = scraper.export_to_csv()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n✅ File-based scraping completed!")
        print(f"⏱️  Duration: {duration:.1f} seconds")
        print(f"📊 Total products found: {len(products)}")
        print(f"💾 Exported to: {csv_file}")
        
        # Show category breakdown
        category_counts = {}
        for product in products:
            subcat = product.get('subcategory', 'Unknown')
            category_counts[subcat] = category_counts.get(subcat, 0) + 1
        
        print(f"\n📈 Category Breakdown:")
        for subcat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {subcat}: {count} products")
        
        # Ask if user wants to import to database
        print(f"\n📥 Import to database? (y/n): ", end='')
        import_input = input().strip().lower()
        if import_input == 'y':
            print("📥 Importing to database...")
            import subprocess
            # Change to parent directory (backend) to run Django commands
            backend_dir = os.path.dirname(os.path.dirname(__file__))
            result = subprocess.run([
                sys.executable, 'manage.py', 'import_products_csv', 
                '--csv-path', csv_file
            ], cwd=backend_dir)
            
            if result.returncode == 0:
                print("✅ Database import completed!")
            else:
                print("❌ Database import failed!")
        
    except Exception as e:
        print(f"❌ Scraping failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
