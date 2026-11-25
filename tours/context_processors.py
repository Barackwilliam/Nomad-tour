import datetime

from django.conf import settings

from .cache import cached
from .models import Category, Page, SiteSettings


def _menu():
    data = []
    for cat in Category.objects.filter(is_active=True, show_in_menu=True).order_by("order"):
        published = cat.tours.filter(is_published=True)
        tours = list(
            published.order_by("order", "duration_days", "title").only(
                "title", "slug", "duration_days", "duration_label", "category_id"
            )[:10]
        )
        data.append({"category": cat, "tours": tours, "more": published.count() > 10})
    return data


def site(request):
    return {
        "site": SiteSettings.get(),
        "menu": cached("menu", _menu),
        # Active categories not shown in the top menu (e.g. Kilimanjaro & Safari combos) are linked
        # from the first dropdowns instead, so the menu stays on one line.
        "menu_extra": cached(
            "menu-extra", lambda: list(Category.objects.filter(is_active=True, show_in_menu=False).order_by("order"))
        ),
        "footer_pages": cached(
            "footer-pages",
            lambda: list(Page.objects.filter(is_published=True, show_in_footer=True).order_by("order")[:8]),
        ),
        "SITE_URL": settings.SITE_URL,
        "current_year": datetime.date.today().year,
        "canonical_url": settings.SITE_URL + request.path,
    }
