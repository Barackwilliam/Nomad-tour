import datetime

from django.conf import settings
from django.core.cache import cache

from .models import Category, Page, SiteSettings


def _menu():
    data = cache.get("site-menu")
    if data is None:
        data = []
        for cat in Category.objects.filter(is_active=True, show_in_menu=True).order_by("order"):
            tours = list(
                cat.tours.filter(is_published=True).order_by("order", "duration_days", "title").only(
                    "title", "slug", "duration_days", "duration_label", "category_id"
                )[:10]
            )
            data.append({"category": cat, "tours": tours, "more": cat.tours.filter(is_published=True).count() > 10})
        cache.set("site-menu", data, 120)
    return data


def site(request):
    s = SiteSettings.get()
    return {
        "site": s,
        "menu": _menu(),
        # Active categories not shown in the top menu (e.g. Kilimanjaro & Safari combos) are linked
        # from the first dropdowns instead, so the menu stays on one line.
        "menu_extra": Category.objects.filter(is_active=True, show_in_menu=False).order_by("order"),
        "footer_pages": Page.objects.filter(is_published=True, show_in_footer=True).order_by("order")[:8],
        "SITE_URL": settings.SITE_URL,
        "current_year": datetime.date.today().year,
        "canonical_url": settings.SITE_URL + request.path,
    }
