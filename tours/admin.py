from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.db.models import Count
from django.utils.html import format_html
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.decorators import display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import (
    FAQ,
    Category,
    Enquiry,
    GroupDeparture,
    Page,
    SiteSettings,
    Testimonial,
    Tour,
    TourDay,
    TourImage,
    TourPrice,
)

admin.site.site_header = "Nomad Explorer Tours"
admin.site.site_title = "Nomad Explorer Admin"
admin.site.index_title = "Dashboard"


def thumb(image, size=56):
    if not image:
        return "—"
    return format_html(
        '<img src="{}" style="width:{}px;height:{}px;object-fit:cover;border-radius:6px" alt="">',
        image.url,
        size,
        round(size * 0.7),
    )


# ---------------------------------------------------------------------------
# Users (re-registered with Unfold styling)
# ---------------------------------------------------------------------------
admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


# ---------------------------------------------------------------------------
# Site settings
# ---------------------------------------------------------------------------
@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
    fieldsets = (
        ("Company & contacts", {
            "classes": ["tab"],
            "fields": (
                "company_name", "tagline", "logo",
                ("phone", "phone_2"), ("whatsapp", "email"), "address", "map_embed_url", "payment_link",
            ),
        }),
        ("Social media", {
            "classes": ["tab"],
            "fields": ("facebook", "instagram", "tiktok", "youtube", "x_twitter", "tripadvisor"),
        }),
        ("Home page", {
            "classes": ["tab"],
            "fields": (
                "hero_title", "hero_subtitle", ("hero_image", "hero_image_2", "hero_image_3"), "intro_title", "intro_text",
                ("founded_year", "stat_travellers"), ("stat_summits", "stat_rating"), "cta_image",
            ),
        }),
        ("About us", {
            "classes": ["tab"],
            "fields": (
                "about_title", "about_text", "about_image", "who_we_are", ("mission", "vision"), "values",
                "about_closing_title", "about_closing_text", "slogan",
            ),
        }),
        ("Group departures", {"classes": ["tab"], "fields": ("departures_year",)}),
        ("SEO & analytics", {
            "classes": ["tab"],
            "fields": ("meta_title", "meta_description", "google_analytics_id", "google_site_verification"),
        }),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Go straight to the single settings form.
        from django.shortcuts import redirect

        obj = SiteSettings.get()
        return redirect("admin:tours_sitesettings_change", obj.pk)


# ---------------------------------------------------------------------------
# Tours
# ---------------------------------------------------------------------------
@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("preview", "name", "slug", "tour_count", "order", "show_in_menu", "is_active")
    list_display_links = ("preview", "name")
    list_editable = ("order", "show_in_menu", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        (None, {"fields": ("name", "slug", "menu_label", "tagline", "intro", "image", ("order", "show_in_menu", "is_active"))}),
        ("SEO", {"fields": ("meta_title", "meta_description")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_tours=Count("tours"))

    @display(description="Photo")
    def preview(self, obj):
        return thumb(obj.image)

    @display(description="Tours", ordering="_tours")
    def tour_count(self, obj):
        return obj._tours


class TourDayInline(StackedInline):
    model = TourDay
    extra = 0
    tab = True
    verbose_name_plural = "Itinerary (day by day)"
    fields = (
        ("day_number", "title"),
        "description",
        ("accommodation", "meals"),
        ("elevation", "distance", "hiking_time"),
        ("habitat", "activity"),
        "image",
    )


class TourPriceInline(TabularInline):
    model = TourPrice
    extra = 0
    tab = True
    verbose_name_plural = "Prices by group size"
    fields = ("label", "price", "order")


class TourImageInline(TabularInline):
    model = TourImage
    extra = 0
    tab = True
    verbose_name_plural = "Photo gallery"
    fields = ("preview", "image", "caption", "order")
    readonly_fields = ("preview",)

    @display(description="Preview")
    def preview(self, obj):
        return thumb(obj.image, 80)


@admin.register(Tour)
class TourAdmin(ModelAdmin):
    list_display = (
        "preview", "title", "category", "duration_days", "show_price", "style",
        "is_featured", "is_published", "order",
    )
    list_display_links = ("preview", "title")
    list_editable = ("is_featured", "is_published", "order")
    list_filter = ("category", "style", "level", "is_featured", "is_published")
    list_filter_submit = True
    search_fields = ("title", "summary", "destinations")
    prepopulated_fields = {"slug": ("title",)}
    inlines = (TourDayInline, TourPriceInline, TourImageInline)
    save_on_top = True
    warn_unsaved_form = True
    actions = ("make_published", "make_unpublished", "duplicate_tours")
    fieldsets = (
        ("Basics", {
            "classes": ["tab"],
            "fields": (
                "title", "slug", "category", "summary", "image",
                ("duration_days", "duration_label"), ("style", "level"), ("tour_type", "group_size"),
                "destinations", ("start_point", "end_point"),
            ),
        }),
        ("Description", {"classes": ["tab"], "fields": ("overview", "highlights", ("included", "excluded"))}),
        ("Price", {"classes": ["tab"], "fields": (("price_from", "price_old"), "price_note")}),
        ("Publishing & SEO", {
            "classes": ["tab"],
            "fields": (("is_published", "is_featured"), "order", "meta_title", "meta_description", "legacy_path"),
        }),
    )

    @display(description="Photo")
    def preview(self, obj):
        return thumb(obj.image)

    @display(description="From", ordering="price_from")
    def show_price(self, obj):
        return f"${obj.price_from:,.0f}" if obj.price_from else "On request"

    @admin.action(description="Publish selected tours")
    def make_published(self, request, queryset):
        queryset.update(is_published=True)

    @admin.action(description="Hide selected tours from the website")
    def make_unpublished(self, request, queryset):
        queryset.update(is_published=False)

    @admin.action(description="Duplicate selected tours (as hidden copies)")
    def duplicate_tours(self, request, queryset):
        for tour in queryset:
            days = list(tour.days.all())
            prices = list(tour.prices.all())
            tour.pk = None
            tour.id = None
            tour._state.adding = True
            tour.title = f"{tour.title} (copy)"
            base = f"{tour.slug}-copy"
            slug, n = base, 2
            while Tour.objects.filter(slug=slug).exists():
                slug, n = f"{base}-{n}", n + 1
            tour.slug = slug
            tour.is_published = False
            tour.is_featured = False
            tour.legacy_path = ""
            tour.save()
            for d in days:
                d.pk = None
                d.tour = tour
                d.save()
            for p in prices:
                p.pk = None
                p.tour = tour
                p.save()
        self.message_user(request, "Copies created. They are hidden until you publish them.")


# ---------------------------------------------------------------------------
# Group departures
# ---------------------------------------------------------------------------
@admin.register(GroupDeparture)
class GroupDepartureAdmin(ModelAdmin):
    list_display = (
        "start_date", "end_date", "name_display", "kind", "price", "spaces", "status_badge", "is_published",
    )
    list_editable = ("is_published",)
    list_filter = ("kind", "status", "is_published", ("start_date", admin.DateFieldListFilter))
    list_filter_submit = True
    date_hierarchy = "start_date"
    search_fields = ("title", "tour__title", "note")
    autocomplete_fields = ("tour",)
    actions = ("mark_full", "mark_open")
    fieldsets = (
        (None, {"fields": ("kind", "tour", "title", ("start_date", "end_date"), "note")}),
        ("Price & spaces", {"fields": (("price", "deposit_percent"), ("total_spaces", "booked_spaces"), "status", "is_published")}),
    )

    @display(description="Departure")
    def name_display(self, obj):
        return obj.name

    @display(description="Booked")
    def spaces(self, obj):
        return f"{obj.booked_spaces} / {obj.total_spaces}"

    @display(
        description="Status",
        label={"Available": "success", "Guaranteed": "info", "Few left": "warning", "Full": "danger"},
    )
    def status_badge(self, obj):
        key, _ = obj.display_status
        return {"open": "Available", "guaranteed": "Guaranteed", "few": "Few left", "full": "Full"}[key]

    @admin.action(description="Mark as fully booked")
    def mark_full(self, request, queryset):
        queryset.update(status="full")

    @admin.action(description="Mark as open")
    def mark_open(self, request, queryset):
        queryset.update(status="open")


# ---------------------------------------------------------------------------
# Enquiries
# ---------------------------------------------------------------------------
@admin.register(Enquiry)
class EnquiryAdmin(ModelAdmin):
    list_display = ("created_at", "full_name", "subject_display", "travel_date", "people", "whatsapp_link", "status_badge")
    list_filter = ("status", "source", ("created_at", admin.DateFieldListFilter))
    list_filter_submit = True
    search_fields = ("full_name", "email", "phone", "message", "tour__title")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "source", "tour", "departure", "contact_buttons")
    actions = ("mark_replied", "mark_booked")
    fieldsets = (
        ("Status", {"fields": ("status", "admin_notes", "contact_buttons")}),
        ("Customer", {"fields": (("full_name", "email"), ("phone", "country"))}),
        ("Trip", {"fields": ("source", "tour", "departure", "travel_date", ("adults", "children"), "budget", "interests", "message", "created_at")}),
    )

    def has_add_permission(self, request):
        return False

    @display(description="Request")
    def subject_display(self, obj):
        return obj.subject

    @display(description="People")
    def people(self, obj):
        return obj.travellers

    @display(
        description="Status",
        label={"New": "warning", "Replied": "info", "Booked / paid": "success", "Closed / lost": "danger"},
    )
    def status_badge(self, obj):
        return obj.get_status_display()

    @display(description="WhatsApp")
    def whatsapp_link(self, obj):
        number = "".join(ch for ch in obj.phone if ch.isdigit())
        if not number:
            return "—"
        return format_html('<a href="https://wa.me/{}" target="_blank" rel="noopener">Chat</a>', number)

    @display(description="Reply")
    def contact_buttons(self, obj):
        number = "".join(ch for ch in obj.phone if ch.isdigit())
        parts = [format_html('<a href="mailto:{}?subject=Your%20trip%20with%20Nomad%20Explorer%20Tours">Email {}</a>', obj.email, obj.email)]
        if number:
            parts.append(format_html('<a href="https://wa.me/{}" target="_blank" rel="noopener">WhatsApp {}</a>', number, obj.phone))
        return format_html(" &nbsp;|&nbsp; ".join(["{}"] * len(parts)), *parts)

    @admin.action(description="Mark as replied")
    def mark_replied(self, request, queryset):
        queryset.update(status="replied")

    @admin.action(description="Mark as booked / paid")
    def mark_booked(self, request, queryset):
        queryset.update(status="booked")


# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------
@admin.register(Testimonial)
class TestimonialAdmin(ModelAdmin):
    list_display = ("name", "country", "trip", "rating", "source", "is_published", "order")
    list_editable = ("is_published", "order")
    search_fields = ("name", "text", "trip")


@admin.register(FAQ)
class FAQAdmin(ModelAdmin):
    list_display = ("question", "group", "show_on_home", "order")
    list_editable = ("show_on_home", "order")
    list_filter = ("group", "show_on_home")
    search_fields = ("question", "answer")


@admin.register(Page)
class PageAdmin(ModelAdmin):
    list_display = ("title", "kind", "slug", "show_in_footer", "is_published", "order")
    list_editable = ("show_in_footer", "is_published", "order")
    list_filter = ("kind", "is_published")
    search_fields = ("title", "body")
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        (None, {"fields": ("kind", "title", "slug", "intro", "image", "body")}),
        ("Publishing & SEO", {"fields": (("is_published", "show_in_footer"), "order", "meta_title", "meta_description", "legacy_path")}),
    )

