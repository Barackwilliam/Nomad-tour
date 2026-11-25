import datetime
import logging
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Min, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from . import seo
from .forms import EnquiryForm
from .models import FAQ, Category, GroupDeparture, Page, SiteSettings, Testimonial, Tour

log = logging.getLogger("tours")

DURATION_FILTERS = [
    ("1", "Day trips", Q(duration_days__lte=1)),
    ("2-4", "2 – 4 days", Q(duration_days__gte=2, duration_days__lte=4)),
    ("5-7", "5 – 7 days", Q(duration_days__gte=5, duration_days__lte=7)),
    ("8", "8+ days", Q(duration_days__gte=8)),
]


# ---------------------------------------------------------------------------
# Enquiry handling (shared by every form on the site)
# ---------------------------------------------------------------------------
def _notify(enquiry):
    site = SiteSettings.get()
    to = settings.ENQUIRY_NOTIFY_EMAIL or site.email
    if not to:
        return
    lines = [
        f"New website enquiry ({enquiry.get_source_display()})",
        "",
        f"Request:   {enquiry.subject}",
        f"Name:      {enquiry.full_name}",
        f"Email:     {enquiry.email}",
        f"Phone:     {enquiry.phone or '-'}",
        f"Country:   {enquiry.country or '-'}",
        f"Date:      {enquiry.travel_date or '-'}",
        f"People:    {enquiry.adults} adults, {enquiry.children} children",
        f"Budget:    {enquiry.budget or '-'}",
        f"Interests: {enquiry.interests or '-'}",
        "",
        enquiry.message or "",
        "",
        f"Open in dashboard: {settings.SITE_URL}{reverse('admin:tours_enquiry_change', args=[enquiry.pk])}",
    ]
    try:
        send_mail(
            f"New enquiry: {enquiry.subject} — {enquiry.full_name}",
            "\n".join(lines),
            settings.DEFAULT_FROM_EMAIL,
            [to],
            fail_silently=False,
        )
    except Exception:  # email problems must never lose the enquiry
        log.exception("Could not send enquiry notification email")


def handle_enquiry(request, source, tour=None, departure=None):
    """Return (form, response). response is a redirect when the enquiry was saved."""
    if request.method != "POST" or request.POST.get("form") != "enquiry":
        initial = {}
        if departure:
            initial["travel_date"] = departure.start_date
        return EnquiryForm(initial=initial), None

    form = EnquiryForm(request.POST)
    if form.is_spam():
        return form, redirect("thank_you")
    if form.is_valid():
        enquiry = form.save(commit=False)
        enquiry.source = source
        enquiry.tour = tour or (departure.tour if departure else None)
        enquiry.departure = departure
        if departure and not enquiry.travel_date:
            enquiry.travel_date = departure.start_date
        enquiry.save()
        _notify(enquiry)
        request.session["last_enquiry"] = {
            "name": enquiry.full_name.split(" ")[0],
            "subject": enquiry.subject,
            "date": enquiry.travel_date.strftime("%d %B %Y") if enquiry.travel_date else "",
            "people": enquiry.travellers,
        }
        return form, redirect("thank_you")
    messages.error(request, "Please check the form, some details are missing.")
    return form, None


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
def home(request):
    featured = list(Tour.objects.published().filter(is_featured=True).select_related("category").order_by("order")[:12])
    if len(featured) < 6:
        featured = list(Tour.objects.published().select_related("category")[:12])
    site = SiteSettings.get()
    departures = (
        GroupDeparture.objects.upcoming()
        .filter(start_date__year=site.departures_year)
        .select_related("tour", "tour__category")[:6]
    )
    categories = Category.objects.filter(is_active=True).annotate(min_price=Min("tours__price_from"))
    return render(
        request,
        "tours/home.html",
        {
            "featured": featured,
            "featured_categories": sorted({t.category for t in featured}, key=lambda c: c.order),
            "categories": categories,
            "testimonials": Testimonial.objects.filter(is_published=True)[:9],
            "faqs": FAQ.objects.filter(show_on_home=True)[:8],
            "departures": departures,
            "guides": Page.objects.filter(is_published=True, kind="guide").order_by("-created_at")[:3],
            "months": _upcoming_months(),
            "ld_org": seo.organization(site),
        },
    )


def _upcoming_months(count=18):
    d = datetime.date.today().replace(day=1)
    out = []
    for _ in range(count):
        out.append(d)
        d = (d + datetime.timedelta(days=32)).replace(day=1)
    return out


def _filter_tours(request, qs):
    active = {}
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(destinations__icontains=q))
        active["q"] = q
    days = request.GET.get("days")
    for key, _label, cond in DURATION_FILTERS:
        if days == key:
            qs = qs.filter(cond)
            active["days"] = key
    style = request.GET.get("style")
    if style in ("private", "group"):
        qs = qs.filter(style=style)
        active["style"] = style
    level = request.GET.get("level")
    if level in dict(Tour.LEVEL_CHOICES) and level:
        qs = qs.filter(level=level)
        active["level"] = level
    sort = request.GET.get("sort")
    if sort == "price":
        qs = qs.order_by("price_from")
    elif sort == "days":
        qs = qs.order_by("duration_days")
    return qs, active


def tour_list(request):
    qs = Tour.objects.published().select_related("category")
    cat = request.GET.get("category")
    category = None
    if cat:
        category = Category.objects.filter(slug=cat, is_active=True).first()
        if category:
            qs = qs.filter(category=category)
    qs, active = _filter_tours(request, qs)
    return render(
        request,
        "tours/tour_list.html",
        {
            "tours": qs,
            "active": active,
            "category_filter": category,
            "categories": Category.objects.filter(is_active=True),
            "duration_filters": [(k, label) for k, label, _ in DURATION_FILTERS],
            "levels": [c for c in Tour.LEVEL_CHOICES if c[0]],
        },
    )


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    qs = category.tours.filter(is_published=True).select_related("category")
    qs, active = _filter_tours(request, qs)
    levels_present = set(category.tours.filter(is_published=True).values_list("level", flat=True))
    faqs = list(FAQ.objects.filter(group=_faq_group(category))[:6])
    return render(
        request,
        "tours/category.html",
        {
            "category": category,
            "tours": qs,
            "active": active,
            "duration_filters": [(k, label) for k, label, _ in DURATION_FILTERS],
            "levels": [c for c in Tour.LEVEL_CHOICES if c[0] and c[0] in levels_present],
            "faqs": faqs,
            "ld_list": seo.item_list(qs),
            "ld_faq": seo.faq_page(faqs),
            "ld_crumbs": seo.breadcrumbs([(category.name, category.get_absolute_url())]),
        },
    )


def _faq_group(category):
    slug = category.slug
    if "kilimanjaro" in slug and "safari" not in slug:
        return "kilimanjaro"
    if "zanzibar" in slug:
        return "zanzibar"
    if "safari" in slug:
        return "safari"
    return "general"


def tour_detail(request, category_slug, slug):
    tour = get_object_or_404(
        Tour.objects.select_related("category").prefetch_related("days", "prices", "gallery"),
        slug=slug,
        is_published=True,
    )
    if tour.category.slug != category_slug:
        return redirect(tour.get_absolute_url(), permanent=True)
    form, response = handle_enquiry(request, "tour", tour=tour)
    if response:
        return response
    related = (
        Tour.objects.published().filter(category=tour.category).exclude(pk=tour.pk).select_related("category")
    )
    related = sorted(related, key=lambda t: abs(t.duration_days - tour.duration_days))[:3]
    departures = tour.departures.upcoming()[:6]
    site = SiteSettings.get()
    return render(
        request,
        "tours/tour_detail.html",
        {
            "tour": tour,
            "form": form,
            "related": related,
            "departures": departures,
            "wa_text": f"Hello {site.company_name}, I am interested in the {tour.title}. Is it available?",
            "ld_tour": seo.tour(tour, site),
            "ld_crumbs": seo.breadcrumbs(
                [(tour.category.name, tour.category.get_absolute_url()), (tour.title, tour.get_absolute_url())]
            ),
        },
    )


def departures(request):
    site = SiteSettings.get()
    year = site.departures_year
    qs = GroupDeparture.objects.upcoming().filter(start_date__year=year).select_related("tour", "tour__category")
    kind = request.GET.get("type")
    if kind in ("kilimanjaro", "safari", "other"):
        qs = qs.filter(kind=kind)
    month = request.GET.get("month")
    if month and month.isdigit() and 1 <= int(month) <= 12:
        qs = qs.filter(start_date__month=int(month))

    departure = None
    if request.method == "POST":
        departure = GroupDeparture.objects.filter(pk=request.POST.get("departure_id"), is_published=True).first()
        if departure is None:
            messages.error(request, "Please choose a departure date.")
    form, response = handle_enquiry(request, "departure", departure=departure)
    if response:
        return response

    all_upcoming = GroupDeparture.objects.upcoming().filter(start_date__year=year)
    months = sorted({d.month for d in all_upcoming.values_list("start_date", flat=True)})
    return render(
        request,
        "tours/departures.html",
        {
            "departures": qs,
            "year": year,
            "kind": kind or "",
            "month": int(month) if month and month.isdigit() else None,
            "months": [(m, datetime.date(year, m, 1)) for m in months],
            "form": form,
            "open_departure": departure,
            "group_tours": Tour.objects.published().filter(style="group").select_related("category")[:6],
            "year_str": str(year),
            "deposit_percent": 30,
            "ld_events": seo.departures(list(qs[:30]), site),
        },
    )


def plan_trip(request):
    form, response = handle_enquiry(request, "plan")
    if response:
        return response
    tour = None
    if request.GET.get("tour"):
        tour = Tour.objects.published().filter(slug=request.GET["tour"]).first()
        if tour and not form.is_bound:
            form.initial["message"] = f"I'm interested in: {tour.title}"
    if request.GET.get("month") and not form.is_bound:
        form.initial["message"] = (form.initial.get("message", "") + f"\nPreferred month: {request.GET['month']}").strip()
    if request.GET.get("trip") and not form.is_bound:
        form.initial["interests_list"] = [request.GET["trip"]]
    return render(request, "tours/plan_trip.html", {"form": form, "tour": tour})


def contact(request):
    form, response = handle_enquiry(request, "contact")
    if response:
        return response
    return render(request, "tours/contact.html", {"form": form})


def about(request):
    return render(
        request,
        "tours/about.html",
        {
            "testimonials": Testimonial.objects.filter(is_published=True)[:3],
            "categories": Category.objects.filter(is_active=True),
        },
    )


def faq(request):
    groups = []
    for key, label in FAQ.GROUP_CHOICES:
        items = list(FAQ.objects.filter(group=key))
        if items:
            groups.append((key, label, items))
    return render(request, "tours/faq.html", {"groups": groups, "ld_faq": seo.faq_page(FAQ.objects.all())})


def page_detail(request, slug):
    page = get_object_or_404(Page, slug=slug, is_published=True)
    more = Page.objects.filter(is_published=True, kind=page.kind).exclude(pk=page.pk)[:3]
    return render(request, "tours/page.html", {"page": page, "more": more})


def guides(request):
    pages = Page.objects.filter(is_published=True, kind="guide").order_by("-created_at")
    return render(request, "tours/guides.html", {"pages": pages})


def thank_you(request):
    info = request.session.get("last_enquiry") or {}
    site = SiteSettings.get()
    text = f"Hello {site.company_name}, I just sent an enquiry on your website"
    if info.get("subject"):
        text += f" about {info['subject']}"
    if info.get("date"):
        text += f" for {info['date']}"
    if info.get("people"):
        text += f" ({info['people']} people)"
    if info.get("name"):
        text += f". My name is {info['name']}."
    return render(
        request,
        "tours/thank_you.html",
        {"info": info, "wa_url": f"https://wa.me/{site.whatsapp}?text={quote(text)}"},
    )


def legacy_redirect(request, path):
    """301-redirect addresses from the old PHP website so Google keeps the rankings."""
    name = path + ".php"
    tour = Tour.objects.filter(legacy_path=name).select_related("category").first()
    if tour:
        return redirect(tour.get_absolute_url(), permanent=True)
    page = Page.objects.filter(legacy_path=name).first()
    if page:
        return redirect(page.get_absolute_url(), permanent=True)
    category = Category.objects.filter(slug=LEGACY_CATEGORIES.get(name, "-")).first()
    if category:
        return redirect(category.get_absolute_url(), permanent=True)
    fixed = LEGACY_FIXED.get(name)
    if fixed:
        return redirect(fixed, permanent=True)
    raise Http404


LEGACY_CATEGORIES = {
    "tanzania-camping-safari.php": "tanzania-safaris",
    "tanzania-lodge-safari.php": "tanzania-safaris",
    "mount-kilimanjaro.php": "kilimanjaro-climbing",
    "mount-meru-climbing.php": "mountain-trekking",
    "day-trips.php": "day-trips",
    "zanzibar-beach-holidays.php": "zanzibar-holidays",
}
LEGACY_FIXED = {
    "index.php": "/",
    "company-profile.php": "/about-us/",
    "contact-us.php": "/contact/",
    "plan-trip.php": "/plan-your-trip/",
    "join-group-safari-tanzania.php": "/group-departures/",
    "tanzania-travel-faqs.php": "/faq/",
    "tanzania-safari-faqs.php": "/faq/",
    "kilimanjaro-faqs.php": "/faq/",
}


@require_GET
@cache_control(max_age=86400)
def robots_txt(request):
    body = "\n".join(
        [
            "User-agent: *",
            "Disallow: /admin/",
            "Disallow: /thank-you/",
            "",
            f"Sitemap: {settings.SITE_URL}/sitemap.xml",
        ]
    )
    return HttpResponse(body + "\n", content_type="text/plain")


def error_404(request, exception=None):
    return render(request, "tours/404.html", status=404)


def error_500(request):
    return render(request, "tours/500.html", status=500)
