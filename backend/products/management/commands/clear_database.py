"""
Django management command to safely clear all data from the database
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import User
from products.models import (
    CoreProduct, InstagramProduct, EcommerceProduct, Platform, Brand, Seller,
    ProductCategory, RawScrapedData, PriceHistory, ProductAuditLog, Wishlist, ProductReview
)
from recommendations.models import Recommendation


class Command(BaseCommand):
    help = 'Safely clear all data from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to delete all data',
        )
        parser.add_argument(
            '--keep-users',
            action='store_true',
            help='Keep user accounts and only clear product data',
        )
        parser.add_argument(
            '--keep-platforms',
            action='store_true',
            help='Keep platform configurations',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.ERROR(
                    '❌ This command will delete ALL data from the database!\n'
                    'Use --confirm flag to proceed.\n'
                    'Use --keep-users to preserve user accounts.\n'
                    'Use --keep-platforms to preserve platform configurations.'
                )
            )
            return

        self.stdout.write(self.style.WARNING('🗑️  Starting database cleanup...'))

        try:
            with transaction.atomic():
                # Clear product-related data
                self.clear_product_data()
                
                # Clear recommendations
                self.clear_recommendations()
                
                # Clear user data (if not keeping users)
                if not options['keep_users']:
                    self.clear_user_data()
                
                # Clear platform data (if not keeping platforms)
                if not options['keep_platforms']:
                    self.clear_platform_data()
                
                self.stdout.write(
                    self.style.SUCCESS('✅ Database cleanup completed successfully!')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error during cleanup: {str(e)}')
            )
            raise

    def clear_product_data(self):
        """Clear all product-related data"""
        self.stdout.write('🧹 Clearing product data...')
        
        # Clear in order to respect foreign key constraints
        models_to_clear = [
            (ProductReview, 'product reviews'),
            (Wishlist, 'wishlist items'),
            (ProductAuditLog, 'audit logs'),
            (PriceHistory, 'price history'),
            (RawScrapedData, 'raw scraped data'),
            (InstagramProduct, 'Instagram products'),
            (EcommerceProduct, 'e-commerce products'),
            (CoreProduct, 'core products'),
            (Seller, 'sellers'),
            (Brand, 'brands'),
            (ProductCategory, 'product categories'),
        ]
        
        for model, description in models_to_clear:
            count = model.objects.count()
            if count > 0:
                model.objects.all().delete()
                self.stdout.write(f'   ✅ Cleared {count} {description}')
            else:
                self.stdout.write(f'   ⏭️  No {description} to clear')

    def clear_recommendations(self):
        """Clear recommendation data"""
        self.stdout.write('🧹 Clearing recommendations...')
        
        count = Recommendation.objects.count()
        if count > 0:
            Recommendation.objects.all().delete()
            self.stdout.write(f'   ✅ Cleared {count} recommendations')
        else:
            self.stdout.write('   ⏭️  No recommendations to clear')

    def clear_user_data(self):
        """Clear user data (except superusers)"""
        self.stdout.write('🧹 Clearing user data...')
        
        # Keep superusers
        superusers = User.objects.filter(is_superuser=True)
        superuser_count = superusers.count()
        
        # Delete non-superuser accounts
        regular_users = User.objects.filter(is_superuser=False)
        regular_user_count = regular_users.count()
        
        if regular_user_count > 0:
            regular_users.delete()
            self.stdout.write(f'   ✅ Cleared {regular_user_count} regular user accounts')
        
        if superuser_count > 0:
            self.stdout.write(f'   🔒 Preserved {superuser_count} superuser accounts')
        
        if regular_user_count == 0 and superuser_count == 0:
            self.stdout.write('   ⏭️  No users to clear')

    def clear_platform_data(self):
        """Clear platform configurations"""
        self.stdout.write('🧹 Clearing platform data...')
        
        count = Platform.objects.count()
        if count > 0:
            Platform.objects.all().delete()
            self.stdout.write(f'   ✅ Cleared {count} platform configurations')
        else:
            self.stdout.write('   ⏭️  No platforms to clear')

    def get_database_stats(self):
        """Get current database statistics"""
        stats = {
            'CoreProduct': CoreProduct.objects.count(),
            'InstagramProduct': InstagramProduct.objects.count(),
            'EcommerceProduct': EcommerceProduct.objects.count(),
            'Platform': Platform.objects.count(),
            'Brand': Brand.objects.count(),
            'Seller': Seller.objects.count(),
            'ProductCategory': ProductCategory.objects.count(),
            'User': User.objects.count(),
            'Recommendation': Recommendation.objects.count(),
            'Wishlist': Wishlist.objects.count(),
            'ProductReview': ProductReview.objects.count(),
            'RawScrapedData': RawScrapedData.objects.count(),
            'PriceHistory': PriceHistory.objects.count(),
            'ProductAuditLog': ProductAuditLog.objects.count(),
        }
        return stats

    def show_database_stats(self):
        """Show current database statistics"""
        self.stdout.write('\n📊 Current Database Statistics:')
        self.stdout.write('=' * 50)
        
        stats = self.get_database_stats()
        for model_name, count in stats.items():
            if count > 0:
                self.stdout.write(f'{model_name:20} : {count:>6} records')
        
        total_records = sum(stats.values())
        self.stdout.write('=' * 50)
        self.stdout.write(f'{"TOTAL":20} : {total_records:>6} records')
        self.stdout.write('=' * 50)
