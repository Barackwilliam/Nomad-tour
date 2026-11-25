import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Create the admin user from DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD if it does not exist. "
        "Useful on hosting without a terminal (e.g. Render free plan)."
    )

    def handle(self, *args, **opts):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        if not username or not password:
            self.stdout.write("DJANGO_SUPERUSER_USERNAME/PASSWORD not set; skipping.")
            return
        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"Admin '{username}' already exists.")
            return
        User.objects.create_superuser(
            username=username, email=os.environ.get("DJANGO_SUPERUSER_EMAIL", ""), password=password
        )
        self.stdout.write(self.style.SUCCESS(f"Admin '{username}' created."))
