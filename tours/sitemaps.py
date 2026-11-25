from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Category, Page, Tour


class StaticSitemap(Sitemap):
    changefreq = "weekly"

    def items(self):
        return ["home", "tour_list", "departures", "plan_trip", "about", "contact", "faq", "guides"]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return 1.0 if item == "home" else 0.7


class CategorySitemap(Sitemap):
    priority = 0.9
    changefreq = "weekly"

    def items(self):
        return Category.objects.filter(is_active=True)


class TourSitemap(Sitemap):
    priority = 0.8
    changefreq = "monthly"

    def items(self):
        return Tour.objects.published().select_related("category")

    def lastmod(self, obj):
        return obj.updated_at


class PageSitemap(Sitemap):
    priority = 0.5
    changefreq = "monthly"

    def items(self):
        return Page.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at


SITEMAPS = {"static": StaticSitemap, "categories": CategorySitemap, "tours": TourSitemap, "pages": PageSitemap}
