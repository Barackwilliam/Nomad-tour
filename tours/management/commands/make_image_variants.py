from django.core.management.base import BaseCommand

from tours import cache as content_cache
from tours.images import make_variants
from tours.models import Category, Page, SiteSettings, Tour, TourDay, TourImage


class Command(BaseCommand):
    help = "Create the small responsive copies (480/960 px) for every stored photo. Safe to re-run."

    def handle(self, *args, **opts):
        n = 0
        for model in (SiteSettings, Category, Tour, TourDay, TourImage, Page):
            for obj in model.objects.all():
                widths = {}
                for field in obj.IMAGE_FIELDS:
                    ff = getattr(obj, field)
                    widths[field] = make_variants(ff) if ff else []
                    n += bool(ff)
                model.objects.filter(pk=obj.pk).update(image_widths=widths)
        content_cache.bump()
        self.stdout.write(self.style.SUCCESS(f"Variants checked for {n} photos."))
