from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, re_path
from django.views.static import serve

from tours import views
from tours.sitemaps import SITEMAPS

handler404 = "tours.views.error_404"
handler500 = "tours.views.error_500"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("robots.txt", views.robots_txt),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    path("", views.home, name="home"),
    path("tours/", views.tour_list, name="tour_list"),
    path("group-departures/", views.departures, name="departures"),
    path("plan-your-trip/", views.plan_trip, name="plan_trip"),
    path("contact/", views.contact, name="contact"),
    path("about-us/", views.about, name="about"),
    path("faq/", views.faq, name="faq"),
    path("travel-guides/", views.guides, name="guides"),
    path("info/<slug:slug>/", views.page_detail, name="page"),
    path("thank-you/", views.thank_you, name="thank_you"),
    # Addresses from the old PHP website (e.g. /7days-kilimanjaro-climb-machame-route.php)
    re_path(r"^(?P<path>[\w-]+)\.php$", views.legacy_redirect),
]

if not settings.STORAGES["default"]["BACKEND"].endswith("SupabaseStorage"):
    # Local development without Supabase: serve uploaded files from media/.
    urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT})]

# Category and tour pages last, so they never shadow the fixed pages above.
urlpatterns += [
    path("<slug:slug>/", views.category_detail, name="category"),
    path("<slug:category_slug>/<slug:slug>/", views.tour_detail, name="tour"),
]
