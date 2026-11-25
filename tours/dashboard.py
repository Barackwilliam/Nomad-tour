import datetime

from django.urls import reverse
from django.utils.html import format_html

from .models import Enquiry, GroupDeparture, Tour


def dashboard_callback(request, context):
    today = datetime.date.today()
    month_start = today.replace(day=1)
    new_enquiries = Enquiry.objects.filter(status="new")
    upcoming = GroupDeparture.objects.upcoming().select_related("tour")[:8]

    context.update(
        {
            "kpis": [
                {
                    "title": "New enquiries",
                    "value": new_enquiries.count(),
                    "note": "waiting for a reply",
                    "href": reverse("admin:tours_enquiry_changelist") + "?status__exact=new",
                    "icon": "mark_email_unread",
                },
                {
                    "title": "Enquiries this month",
                    "value": Enquiry.objects.filter(created_at__date__gte=month_start).count(),
                    "note": today.strftime("%B %Y"),
                    "href": reverse("admin:tours_enquiry_changelist"),
                    "icon": "inbox",
                },
                {
                    "title": "Bookings",
                    "value": Enquiry.objects.filter(status="booked").count(),
                    "note": "marked booked / paid",
                    "href": reverse("admin:tours_enquiry_changelist") + "?status__exact=booked",
                    "icon": "verified",
                },
                {
                    "title": "Published tours",
                    "value": Tour.objects.published().count(),
                    "note": f"{Tour.objects.filter(is_featured=True).count()} on the home page",
                    "href": reverse("admin:tours_tour_changelist"),
                    "icon": "travel_explore",
                },
            ],
            "latest_enquiries": {
                "headers": ["Date", "Name", "Request", "Travel date", "Status"],
                "rows": [
                    [
                        e.created_at.strftime("%d %b %H:%M"),
                        format_html('<a class="text-primary-600 font-semibold" href="{}">{}</a>',
                                    reverse("admin:tours_enquiry_change", args=[e.pk]), e.full_name),
                        e.subject,
                        e.travel_date.strftime("%d %b %Y") if e.travel_date else "—",
                        e.get_status_display(),
                    ]
                    for e in Enquiry.objects.select_related("tour", "departure")[:8]
                ],
            },
            "upcoming_departures": {
                "headers": ["Date", "Departure", "Booked", "Price"],
                "rows": [
                    [
                        d.start_date.strftime("%d %b %Y"),
                        format_html('<a class="text-primary-600" href="{}">{}</a>',
                                    reverse("admin:tours_groupdeparture_change", args=[d.pk]), d.name),
                        f"{d.booked_spaces}/{d.total_spaces}",
                        f"${d.price:,.0f}",
                    ]
                    for d in upcoming
                ],
            },
            "quick_links": [
                ("Add a new tour", reverse("admin:tours_tour_add"), "add_circle"),
                ("Add group departure", reverse("admin:tours_groupdeparture_add"), "group_add"),
                ("Edit contacts & home page", reverse("admin:tours_sitesettings_changelist"), "settings"),
                ("Add a review", reverse("admin:tours_testimonial_add"), "reviews"),
            ],
        }
    )
    return context
