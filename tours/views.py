import datetime
import logging
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.db.models import F, Min, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from . import mailer, seo
from .cache import cached
from .seasons import SEASONS
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
    mailer.send_async(
        f"New enquiry: {enquiry.subject} — {enquiry.full_name}",
        "\n".join(lines),
        [to],
        reply_to=enquiry.email,  # pressing "Reply" answers the customer directly
    )
    if settings.SEND_CUSTOMER_CONFIRMATION and mailer.backend_name() != "none":
        first = enquiry.full_name.split(" ")[0]
        body = [
            f"Dear {first},",
            "",
            f"Thank you for contacting {site.company_name}. We have received your enquiry about "
            f"{enquiry.subject} and our team will reply within 24 hours with availability and a free quote.",
            "",
            f"Travel date: {enquiry.travel_date or 'flexible'}",
            f"Travellers: {enquiry.adults} adults, {enquiry.children} children",
            "",
            f"Need a faster answer? Chat with us on WhatsApp: {site.whatsapp_url}",
            f"Phone: {site.phone}",
            "",
            "Asante sana,",
            site.company_name,
            settings.SITE_URL,
        ]
        mailer.send_async(
            f"We received your enquiry – {site.company_name}", "\n".join(body), [enquiry.email], reply_to=to
        )


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
    site = SiteSettings.get()

    def load():
        featured = list(
            Tour.objects.published().filter(is_featured=True).select_related("category").order_by("order")[:12]
        )
        if len(featured) < 6:
            featured = list(Tour.objects.published().select_related("category")[:12])
        return {
            "featured": featured,
            "featured_categories": sorted({t.category for t in featured}, key=lambda c: c.order),
            "categories": list(
                Category.objects.filter(is_active=True).annotate(min_price=Min("tours__price_from"))
            ),
            "testimonials": list(Testimonial.objects.filter(is_published=True)[:9]),
            "faqs": list(FAQ.objects.filter(show_on_home=True)[:8]),
            "departures": list(
                GroupDeparture.objects.upcoming()
                .filter(start_date__lte=site.departures_end)
                .select_related("tour", "tour__category")[:6]
            ),
            "guides": list(Page.objects.filter(is_published=True, kind="guide").order_by("-created_at")[:3]),
        }

    context = dict(cached("home", load))
    context.update(
        {
            "months": _upcoming_months(),
            "seasons": SEASONS,
            "ld_org": seo.organization(site),
            "ld_faq": seo.faq_page(context["faqs"]),
        }
    )
    return render(request, "tours/home.html", context)


def _upcoming_months(count=18):
    d = datetime.date.today().replace(day=1)
    out = []
    for _ in range(count):
        out.append(d)
        d = (d + datetime.timedelta(days=32)).replace(day=1)
    return out


def _filter_tours(request, qs):
    active = {}
    q = request.GET.get("q", "").strip()[:80]
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
        qs = qs.order_by(F("price_from").asc(nulls_last=True))
    elif sort == "days":
        qs = qs.order_by("duration_days")
    return qs, active


def _query_key(request, *names):
    return "&".join(f"{n}={request.GET.get(n, '')}" for n in names)


def tour_list(request):
    def load():
        qs = Tour.objects.published().select_related("category")
        category = None
        if request.GET.get("category"):
            category = Category.objects.filter(slug=request.GET["category"], is_active=True).first()
            if category:
                qs = qs.filter(category=category)
        qs, active = _filter_tours(request, qs)
        return {
            "tours": list(qs),
            "active": active,
            "category_filter": category,
            "categories": list(Category.objects.filter(is_active=True)),
        }

    if request.GET.get("q"):
        data = load()  # free-text searches are not worth caching
    else:
        data = cached("tours?" + _query_key(request, "category", "days", "style", "level", "sort"), load)
    context = dict(data)
    context.update(
        {
            "duration_filters": [(k, label) for k, label, _ in DURATION_FILTERS],
            "levels": [c for c in Tour.LEVEL_CHOICES if c[0]],
        }
    )
    return render(request, "tours/tour_list.html", context)


def category_detail(request, slug):
    def load():
        category = Category.objects.filter(slug=slug, is_active=True).first()
        if category is None:
            return None
        qs = category.tours.filter(is_published=True).select_related("category")
        qs, active = _filter_tours(request, qs)
        levels_present = set(category.tours.filter(is_published=True).values_list("level", flat=True))
        return {
            "category": category,
            "tours": list(qs),
            "active": active,
            "levels": [c for c in Tour.LEVEL_CHOICES if c[0] and c[0] in levels_present],
            "faqs": list(FAQ.objects.filter(group=_faq_group(category))[:6]),
        }

    data = cached(f"cat:{slug}?" + _query_key(request, "days", "style", "level", "sort"), load)
    if data is None:
        raise Http404
    category = data["category"]
    context = dict(data)
    context.update(
        {
            "duration_filters": [(k, label) for k, label, _ in DURATION_FILTERS],
            "ld_list": seo.item_list(data["tours"]),
            "ld_faq": seo.faq_page(data["faqs"]),
            "ld_crumbs": seo.breadcrumbs([(category.name, category.get_absolute_url())]),
        }
    )
    return render(request, "tours/category.html", context)


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
    def load():
        tour = (
            Tour.objects.select_related("category")
            .prefetch_related("days", "prices", "gallery")
            .filter(slug=slug, is_published=True)
            .first()
        )
        if tour is None:
            return None
        related = Tour.objects.published().filter(category=tour.category).exclude(pk=tour.pk).select_related("category")
        return {
            "tour": tour,
            "related": sorted(related, key=lambda t: abs(t.duration_days - tour.duration_days))[:3],
            "departures": list(
                tour.departures.upcoming().filter(start_date__lte=SiteSettings.get().departures_end)[:12]
            ),
        }

    data = cached(f"tour:{slug}", load)
    if data is None:
        raise Http404
    tour = data["tour"]
    if tour.category.slug != category_slug:
        return redirect(tour.get_absolute_url(), permanent=True)
    # A group departure chosen on the departures page (?departure=ID) or in the booking form.
    departure = None
    dep_id = request.POST.get("departure_id") or request.GET.get("departure")
    if dep_id and str(dep_id).isdigit():
        departure = next((d for d in data["departures"] if d.pk == int(dep_id)), None)
    if departure and departure.is_full:
        departure = None
    form, response = handle_enquiry(request, "departure" if departure else "tour", tour=tour, departure=departure)
    if response:
        return response
    site = SiteSettings.get()
    context = dict(data)
    wa_text = f"Hello {site.company_name}, I am interested in the {tour.title}"
    if departure:
        wa_text += f" group departure on {departure.start_date:%d %B %Y}"
    context.update(
        {
            "form": form,
            "departure": departure,
            "wa_text": wa_text + ". Is it available?",
            "ld_tour": seo.tour(tour, site),
            "ld_crumbs": seo.breadcrumbs(
                [(tour.category.name, tour.category.get_absolute_url()), (tour.title, tour.get_absolute_url())]
            ),
        }
    )
    return render(request, "tours/tour_detail.html", context)


DEPARTURE_GROUPS = [
    ("kilimanjaro", "Kilimanjaro & mountain climbs", "Climb"),
    ("safari", "Group joining safaris", "Safari"),
    ("other", "Other group trips", "Trip"),
]


def departures(request):
    site = SiteSettings.get()
    end = site.departures_end
    kind = request.GET.get("type")
    kind = kind if kind in dict((k, 1) for k, _l, _s in DEPARTURE_GROUPS) else ""
    month = request.GET.get("month", "")
    month = month if len(month) == 7 and month[:4].isdigit() and month[5:].isdigit() else ""  # "2027-03"

    def load():
        upcoming = GroupDeparture.objects.upcoming().filter(start_date__lte=end).select_related("tour", "tour__category")
        all_dates = list(upcoming.values_list("start_date", flat=True))
        qs = upcoming
        if kind:
            qs = qs.filter(kind=kind)
        if month:
            qs = qs.filter(start_date__year=int(month[:4]), start_date__month=int(month[5:]))
        items = list(qs)
        groups = []
        for key, label, short in DEPARTURE_GROUPS:
            rows = [d for d in items if d.kind == key]
            if rows:
                groups.append({"key": key, "label": label, "short": short, "rows": rows,
                               "first": rows[0].start_date, "last": rows[-1].start_date})
        months = sorted({d.replace(day=1) for d in all_dates})
        return {
            "groups": groups,
            "departures": items,
            "total": len(all_dates),
            "period_start": min(all_dates) if all_dates else None,
            "months": [(m.strftime("%Y-%m"), m) for m in months],
            "group_tours": list(Tour.objects.published().filter(style="group").select_related("category")[:6]),
        }

    departure = None
    if request.method == "POST":
        departure = GroupDeparture.objects.filter(pk=request.POST.get("departure_id"), is_published=True).first()
        if departure is None:
            messages.error(request, "Please choose a departure date.")
    form, response = handle_enquiry(request, "departure", departure=departure)
    if response:
        return response

    data = cached(f"departures:{end}:{kind}:{month}", load)
    context = dict(data)
    context.update(
        {
            "year": site.departures_year,
            "period_end": end,
            "kind": kind,
            "month": month,
            "form": form,
            "open_departure": departure,
            "deposit_percent": 30,
            "ld_events": seo.departures(data["departures"][:40], site),
            "hero_text": (
                f"Scheduled safari and mountain departures "
                f"{'from ' + data['period_start'].strftime('%B %Y') + ' ' if data['period_start'] else ''}"
                f"until December {site.departures_year}. Travel with others, pay less, keep private-tour quality."
            ),
        }
    )
    return render(request, "tours/departures.html", context)


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
            "categories": cached("categories", lambda: list(Category.objects.filter(is_active=True))),
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
