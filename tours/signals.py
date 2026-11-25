from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from . import cache as content_cache
from .models import FAQ, Category, GroupDeparture, Page, SiteSettings, Testimonial, Tour, TourDay, TourImage, TourPrice

CONTENT_MODELS = (Category, Tour, TourDay, TourPrice, TourImage, GroupDeparture, FAQ, Page, Testimonial, SiteSettings)


@receiver([post_save, post_delete])
def refresh_content(sender, **kwargs):
    """Any change in the dashboard makes the website show fresh content right away."""
    if sender in CONTENT_MODELS:
        content_cache.bump()
        cache.delete(SiteSettings.CACHE_KEY)
