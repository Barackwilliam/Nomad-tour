"""Structured data (schema.org JSON-LD) for Google rich results."""
from django.conf import settings
from django.templatetags.static import static


def absolute(url):
    if not url:
        return ""
    return url if url.startswith("http") else settings.SITE_URL + url


def image_url(field, fallback="tours/img/hero.webp"):
    try:
        if field:
            return absolute(field.url)
    except ValueError:
        pass
    return absolute(static(fallback))


def organization(site):
    same_as = [url for _key, _label, url in site.social_links]
    return {
        "@context": "https://schema.org",
        "@type": "TravelAgency",
        "@id": settings.SITE_URL + "/#organization",
        "name": site.company_name,
        "description": site.meta_description,
        "url": settings.SITE_URL + "/",
        "logo": image_url(site.logo, "tours/img/logo.png"),
        "image": image_url(site.hero_image),
        "telephone": site.phone,
        "email": site.email,
        "foundingDate": str(site.founded_year),
        "priceRange": "$$",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": site.address,
            "addressLocality": "Moshi",
            "addressRegion": "Kilimanjaro",
            "addressCountry": "TZ",
        },
        "areaServed": "Tanzania",
        "sameAs": same_as,
    }


def breadcrumbs(items):
    """items: list of (name, url)."""
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": name, "item": absolute(url)}
            for i, (name, url) in enumerate([("Home", "/")] + list(items), start=1)
        ],
    }


def tour(t, site):
    data = {
        "@context": "https://schema.org",
        "@type": "TouristTrip",
        "name": t.title,
        "description": t.seo_description,
        "url": absolute(t.get_absolute_url()),
        "image": image_url(t.image),
        "touristType": t.tour_type or t.category.name,
        "provider": {"@type": "TravelAgency", "name": site.company_name, "url": settings.SITE_URL + "/"},
    }
    days = list(t.days.all())
    if days:
        data["itinerary"] = {
            "@type": "ItemList",
            "numberOfItems": len(days),
            "itemListElement": [
                {"@type": "ListItem", "position": i, "name": d.title} for i, d in enumerate(days, start=1)
            ],
        }
    if t.price_from:
        data["offers"] = {
            "@type": "Offer",
            "price": str(t.price_from),
            "priceCurrency": "USD",
            "availability": "https://schema.org/InStock",
            "url": absolute(t.get_absolute_url()),
            "seller": {"@type": "TravelAgency", "name": site.company_name},
        }
    return data


def item_list(tours):
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "url": absolute(t.get_absolute_url()), "name": t.title}
            for i, t in enumerate(tours, start=1)
        ],
    }


def faq_page(faqs):
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f.question, "acceptedAnswer": {"@type": "Answer", "text": f.answer}}
            for f in faqs
        ],
    }


def departures(items, site):
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i,
                "item": {
                    "@type": "Event",
                    "name": f"{d.name} – group departure",
                    "startDate": d.start_date.isoformat(),
                    "endDate": (d.end_date or d.start_date).isoformat(),
                    "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
                    "eventStatus": "https://schema.org/EventScheduled",
                    "location": {"@type": "Place", "name": "Moshi, Tanzania",
                                 "address": {"@type": "PostalAddress", "addressCountry": "TZ", "addressLocality": "Moshi"}},
                    "organizer": {"@type": "Organization", "name": site.company_name, "url": settings.SITE_URL + "/"},
                    "offers": {
                        "@type": "Offer",
                        "price": str(d.price),
                        "priceCurrency": "USD",
                        "availability": "https://schema.org/SoldOut" if d.is_full else "https://schema.org/InStock",
                        "url": absolute(d.get_absolute_url()),
                    },
                },
            }
            for i, d in enumerate(items, start=1)
        ],
    }
