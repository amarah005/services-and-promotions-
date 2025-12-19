import csv
import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from products.models import CoreProduct


class Command(BaseCommand):
    help = 'Export all electronics products to CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-path',
            type=str,
            help='Path where to save the CSV file (optional)',
            default=None
        )
        parser.add_argument(
            '--category',
            type=str,
            help='Filter by main category (default: Electronics)',
            default='Electronics'
        )
        parser.add_argument(
            '--subcategory',
            type=str,
            help='Filter by subcategory (optional)',
            default=None
        )

    def handle(self, *args, **options):
        category = options['category']
        subcategory = options['subcategory']
        output_path = options['output_path']

        # Build filename
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        if subcategory:
            filename = f"{category.lower()}_{subcategory.lower().replace(' ', '_')}_products_{timestamp}.csv"
        else:
            filename = f"{category.lower()}_products_{timestamp}.csv"

        # Use provided path or default to current directory
        if output_path:
            csv_file_path = os.path.join(output_path, filename)
        else:
            csv_file_path = filename

        # Filter products
        queryset = CoreProduct.objects.filter(is_active=True)
        
        if category:
            queryset = queryset.filter(category__main_category__icontains=category)
        
        if subcategory:
            queryset = queryset.filter(category__subcategory__icontains=subcategory)

        # Order by latest first
        queryset = queryset.order_by('-created_at')

        total_products = queryset.count()
        
        if total_products == 0:
            self.stdout.write(
                self.style.WARNING(f'No products found for category: {category}' + 
                                 (f', subcategory: {subcategory}' if subcategory else ''))
            )
            return

        self.stdout.write(f'📊 Exporting {total_products} products...')
        self.stdout.write(f'📁 Category: {category}')
        if subcategory:
            self.stdout.write(f'📂 Subcategory: {subcategory}')

        # CSV headers (based on actual model fields)
        headers = [
            'id',
            'name',
            'description',
            'price',
            'original_price',
            'currency',
            'main_image_url',
            'product_url',
            'platform_type',
            'platform_name',
            'platform_product_id',
            'brand_name',
            'main_category',
            'subcategory',
            'category_name',
            'sku',
            'model_number',
            'in_stock',
            'stock_quantity',
            'stock_status',
            'average_rating',
            'review_count',
            'shipping_cost',
            'warranty_period',
            'created_at',
            'last_scraped',
            'is_active'
        ]

        try:
            with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)

                exported_count = 0
                for product in queryset:
                    try:
                        # Get platform info and URL
                        platform_name = 'Unknown'
                        platform_product_id = ''
                        product_url = ''
                        
                        if product.platform_type == 'ecommerce' and hasattr(product, 'ecommerce_data'):
                            ecommerce_data = product.ecommerce_data
                            if ecommerce_data.platform:
                                platform_name = ecommerce_data.platform.display_name
                            platform_product_id = ecommerce_data.platform_product_id or ''
                            product_url = ecommerce_data.platform_url or ''
                        elif product.platform_type == 'instagram' and hasattr(product, 'instagram_data'):
                            platform_name = 'Instagram'
                            product_url = product.instagram_data.post_url or ''

                        # Get brand name
                        brand_name = ''
                        if product.brand:
                            brand_name = product.brand.display_name
                        else:
                            # Extract from product name as fallback
                            common_brands = [
                                'Samsung', 'LG', 'Sony', 'Apple', 'Huawei', 'Xiaomi', 'Oppo', 'Vivo', 
                                'OnePlus', 'Realme', 'Tecno', 'Infinix', 'Haier', 'Dawlance', 'Orient',
                                'AUX', 'Gree', 'TCL', 'Changhong', 'HP', 'Dell', 'Lenovo', 'Asus',
                                'Acer', 'MSI', 'Canon', 'Nikon', 'JBL', 'Beats', 'Bose', 'Anker'
                            ]
                            if product.name:
                                name_lower = product.name.lower()
                                for brand in common_brands:
                                    if brand.lower() in name_lower:
                                        brand_name = brand
                                        break

                        # Get category info
                        main_category = product.category.main_category if product.category else ''
                        subcategory_name = product.category.subcategory if product.category else ''
                        category_name = product.category.name if product.category else ''

                        # Get ecommerce-specific data
                        in_stock = ''
                        stock_quantity = ''
                        stock_status = ''
                        average_rating = ''
                        review_count = ''
                        shipping_cost = ''
                        warranty_period = ''
                        
                        if product.platform_type == 'ecommerce' and hasattr(product, 'ecommerce_data'):
                            ecommerce_data = product.ecommerce_data
                            in_stock = ecommerce_data.in_stock if ecommerce_data.in_stock is not None else ''
                            stock_quantity = ecommerce_data.stock_quantity or ''
                            stock_status = ecommerce_data.stock_status or ''
                            average_rating = float(ecommerce_data.average_rating) if ecommerce_data.average_rating else ''
                            review_count = ecommerce_data.review_count or 0
                            shipping_cost = float(ecommerce_data.shipping_cost) if ecommerce_data.shipping_cost else ''
                            warranty_period = ecommerce_data.warranty_period or ''

                        row = [
                            product.id,
                            product.name or '',
                            product.description or '',
                            float(product.price) if product.price else '',
                            float(product.original_price) if product.original_price else '',
                            product.currency or 'PKR',
                            product.main_image_url or '',
                            product_url,
                            product.platform_type or '',
                            platform_name,
                            platform_product_id,
                            brand_name,
                            main_category,
                            subcategory_name,
                            category_name,
                            product.sku or '',
                            product.model_number or '',
                            in_stock,
                            stock_quantity,
                            stock_status,
                            average_rating,
                            review_count,
                            shipping_cost,
                            warranty_period,
                            product.created_at.isoformat() if product.created_at else '',
                            product.last_scraped.isoformat() if product.last_scraped else '',
                            product.is_active
                        ]
                        
                        writer.writerow(row)
                        exported_count += 1

                        # Progress indicator
                        if exported_count % 100 == 0:
                            self.stdout.write(f'📝 Exported {exported_count}/{total_products} products...')

                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f'⚠️  Error exporting product {product.id}: {str(e)}')
                        )
                        continue

            self.stdout.write(
                self.style.SUCCESS(f'✅ Successfully exported {exported_count} products to: {csv_file_path}')
            )
            
            # Show file info
            file_size = os.path.getsize(csv_file_path)
            file_size_mb = file_size / (1024 * 1024)
            self.stdout.write(f'📦 File size: {file_size_mb:.2f} MB')
            
            # Show category breakdown
            self.stdout.write('\n📈 Category Breakdown:')
            category_counts = {}
            for product in queryset:
                subcat = product.category.subcategory if product.category and product.category.subcategory else 'Unknown'
                category_counts[subcat] = category_counts.get(subcat, 0) + 1
            
            for subcat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
                self.stdout.write(f'   {subcat}: {count} products')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error creating CSV file: {str(e)}')
            )
            return
