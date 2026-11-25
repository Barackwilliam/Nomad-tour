from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Category, Tour


@receiver([post_save, post_delete], sender=Category)
@receiver([post_save, post_delete], sender=Tour)
def clear_menu_cache(sender, **kwargs):
    cache.delete("site-menu")
