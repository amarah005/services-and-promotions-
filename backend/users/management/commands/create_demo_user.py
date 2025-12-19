from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

class Command(BaseCommand):
    help = 'Create a demo user for testing authentication'

    def handle(self, *args, **options):
        # Create demo user
        username = 'admin'
        email = 'admin@buyvaulthub.com'
        password = 'admin123'
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'User "{username}" already exists')
            )
            user = User.objects.get(username=username)
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name='Admin',
                last_name='User'
            )
            self.stdout.write(
                self.style.SUCCESS(f'Created user "{username}"')
            )
        
        # Create or get token
        token, created = Token.objects.get_or_create(user=user)
        
        self.stdout.write(
            self.style.SUCCESS(f'Demo user credentials:')
        )
        self.stdout.write(f'Username: {username}')
        self.stdout.write(f'Password: {password}')
        self.stdout.write(f'Token: {token.key}')
        self.stdout.write(
            self.style.SUCCESS('Demo user is ready for testing!')
        )
