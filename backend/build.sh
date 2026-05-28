#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --no-input

# Create superuser + profile if none exists
python manage.py shell -c "
from django.contrib.auth import get_user_model
from core.models import Tenant, UserProfile

User = get_user_model()

# Create a default tenant
tenant, _ = Tenant.objects.get_or_create(
    slug='default',
    defaults={'name': 'Default Organization'}
)
print(f'Tenant ready: {tenant.name}')

# Create admin user
if not User.objects.filter(username='admin').exists():
    user = User.objects.create_superuser('admin', 'admin@example.com', 'Admin@1234')
    print('Superuser created: admin / Admin@1234')
else:
    user = User.objects.get(username='admin')
    print('Superuser already exists, skipping.')

# Create profile for admin
if not UserProfile.objects.filter(user=user).exists():
    UserProfile.objects.create(user=user, tenant=tenant, role='ADMIN')
    print('UserProfile created for admin.')
else:
    print('UserProfile already exists, skipping.')
"
