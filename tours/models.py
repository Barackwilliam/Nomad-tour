import datetime

from django.core.cache import cache
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from .images import OptimisedImagesMixin, upload_to


def lines(text):
    """Split a textarea into clean non-empty lines (used for lists like 'Included')."""
    return [ln.strip(" -•\t") for ln in (text or "").splitlines() if ln.strip(" -•\t")]


def paragraphs(text):
    return [p.strip() for p in (text or "").replace("\r\n", "\n").split("\n\n") if p.strip()]


class SEOFields(models.Model):
    meta_title = models.CharField(
        "SEO title", max_length=70, blank=True, help_text="Shown in Google results. Leave blank to use the name."
    )
    meta_description = models.CharField(
        "SEO description", max_length=170, blank=True, help_text="1-2 sentences shown under the title in Google."
    )

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# Site-wide settings (one row only)
# ---------------------------------------------------------------------------
class SiteSettings(OptimisedImagesMixin, models.Model):
    IMAGE_FIELDS = ("logo", "hero_image", "hero_image_2", "hero_image_3", "about_image", "cta_image")
    CACHE_KEY = "site-settings"
    image_widths = models.JSONField(default=dict, blank=True, editable=False)

    company_name = models.CharField(max_length=120, default="Nomad Explorer Tours")
    tagline = models.CharField(max_length=200, default="Authentic African Safaris. Unforgettable Kilimanjaro Adventures.")
    logo = models.ImageField(upload_to=upload_to("brand"), blank=True, help_text="Leave empty to use the built-in logo.")

    # Contacts
    phone = models.CharField(max_length=40, default="+255 768 611 840")
    phone_2 = models.CharField("Second phone", max_length=40, blank=True, default="+255 689 598 786")
    whatsapp = models.CharField(
        max_length=40, default="255768611840", help_text="Number in international format without + or spaces."
    )
    email = models.EmailField(default="info@nomadexplorertours.com")
    address = models.CharField(max_length=200, default="P.O Box 1118, Soweto, Moshi, Kilimanjaro, Tanzania")
    map_embed_url = models.URLField(
        blank=True,
        max_length=600,
        help_text='Google Maps > Share > Embed a map > copy only the src="..." link.',
    )

    # Social media
    facebook = models.URLField(blank=True, default="https://www.facebook.com/nomadexplorertours")
    instagram = models.URLField(blank=True)
    tiktok = models.URLField(blank=True)
    youtube = models.URLField(blank=True)
    x_twitter = models.URLField("X (Twitter)", blank=True)
    tripadvisor = models.URLField(
        blank=True,
        max_length=300,
        default="https://www.tripadvisor.com/Attraction_Review-g317084-d19139287-Reviews-Nomad_Explorer_Tours-Moshi_Kilimanjaro_Region.html",
    )
    payment_link = models.URLField(
        "Online payment link", blank=True, default="https://payments.pesapal.com/nomadexplorertours"
    )

    # Home page
    hero_title = models.CharField(max_length=120, default="Discover Tanzania with Nomad Explorer Tours")
    hero_subtitle = models.CharField(
        max_length=250,
        default="Maasai-owned safari and Kilimanjaro specialists based in Moshi & Arusha. "
        "Private, tailor-made trips with local guides.",
    )
    hero_image = models.ImageField(upload_to=upload_to("brand"), blank=True)
    hero_image_2 = models.ImageField("Hero slideshow photo 2", upload_to=upload_to("brand"), blank=True)
    hero_image_3 = models.ImageField("Hero slideshow photo 3", upload_to=upload_to("brand"), blank=True)
    intro_title = models.CharField(max_length=150, default="Let us be your guide to Kilimanjaro and Tanzania")
    intro_text = models.TextField(blank=True)
    about_title = models.CharField(max_length=150, default="Discover Tanzania with Nomad Explorer Tours")
    about_text = models.TextField(blank=True, help_text="Main About Us text. Separate paragraphs with an empty line.")
    about_image = models.ImageField(upload_to=upload_to("brand"), blank=True)
    who_we_are = models.TextField("Who we are", blank=True, help_text="Separate paragraphs with an empty line.")
    mission = models.TextField("Our mission", blank=True)
    vision = models.TextField("Our vision", blank=True)
    values = models.TextField(
        "Our values",
        blank=True,
        help_text="One value per line, written as 'Name: description', e.g. 'Authenticity: Sharing the real Tanzania...'",
    )
    about_closing_title = models.CharField(max_length=150, blank=True, default="Experience Tanzania with a Local Company")
    about_closing_text = models.TextField(blank=True)
    slogan = models.CharField(max_length=120, blank=True, default="Travel Local. Explore More. Experience Tanzania.")
    cta_image = models.ImageField("Footer call-to-action image", upload_to=upload_to("brand"), blank=True)
    founded_year = models.PositiveIntegerField(default=2019)
    stat_travellers = models.CharField("Happy travellers", max_length=20, default="5,000+")
    stat_summits = models.CharField("Successful summits", max_length=20, default="1,200+")
    stat_rating = models.CharField(
        "Review rating", max_length=20, blank=True, default="",
        help_text="Your TripAdvisor rating, e.g. 5.0. Leave empty to hide it.",
    )

    departures_year = models.PositiveIntegerField(
        "Group departures year",
        default=2027,
        help_text="The group joining page only lists departures in this year.",
    )

    # SEO
    meta_title = models.CharField(
        "SEO title (home page)",
        max_length=70,
        blank=True,
        default="Nomad Explorer Tours | Tanzania Safaris & Kilimanjaro Climbs",
    )
    meta_description = models.CharField(
        "SEO description (home page)",
        max_length=170,
        blank=True,
        default="Maasai-owned tour operator in Moshi & Arusha. Private Tanzania safaris, Kilimanjaro climbs, "
        "Zanzibar holidays and group joining tours at fair local prices.",
    )
    google_analytics_id = models.CharField("Google Analytics ID", max_length=30, blank=True, help_text="e.g. G-XXXXXXX")
    google_site_verification = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return "Site settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete(self.CACHE_KEY)

    @classmethod
    def get(cls):
        from .cache import version  # the key changes whenever any content is saved

        key = f"{cls.CACHE_KEY}:v{version()}"
        obj = cache.get(key)
        if obj is None:
            obj, _ = cls.objects.get_or_create(pk=1)
            cache.set(key, obj, 600)
        return obj

    @property
    def years_experience(self):
        return max(1, datetime.date.today().year - self.founded_year)

    @property
    def whatsapp_url(self):
        return f"https://wa.me/{self.whatsapp}"

    @property
    def phone_link(self):
        return "".join(ch for ch in self.phone if ch.isdigit() or ch == "+")

    @property
    def phone_2_link(self):
        return "".join(ch for ch in self.phone_2 if ch.isdigit() or ch == "+")

    @property
    def about_paragraphs(self):
        return paragraphs(self.about_text)

    @property
    def intro_paragraphs(self):
        return paragraphs(self.intro_text)

    @property
    def hero_slides(self):
        return [im for im in (self.hero_image, self.hero_image_2, self.hero_image_3) if im]

    @property
    def who_we_are_paragraphs(self):
        return paragraphs(self.who_we_are)

    @property
    def closing_paragraphs(self):
        return paragraphs(self.about_closing_text)

    @property
    def values_list(self):
        """[(name, description)] from lines like 'Authenticity: Sharing the real Tanzania'."""
        out = []
        for line in lines(self.values):
            name, sep, text = line.partition(":")
            out.append((name.strip(), text.strip()) if sep else ("", line))
        return out

    @property
    def social_links(self):
        items = [
            ("facebook", "Facebook", self.facebook),
            ("instagram", "Instagram", self.instagram),
            ("tiktok", "TikTok", self.tiktok),
            ("youtube", "YouTube", self.youtube),
            ("x", "X", self.x_twitter),
            ("tripadvisor", "TripAdvisor", self.tripadvisor),
        ]
        return [(key, label, url) for key, label, url in items if url]


# ---------------------------------------------------------------------------
# Tours
# ---------------------------------------------------------------------------
class Category(OptimisedImagesMixin, SEOFields):
    IMAGE_FIELDS = ("image",)
    image_widths = models.JSONField(default=dict, blank=True, editable=False)

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, help_text="Part of the web address, e.g. kilimanjaro-climbing")
    menu_label = models.CharField(max_length=40, blank=True, help_text="Short name for the top menu.")
    tagline = models.CharField(max_length=160, blank=True)
    intro = models.TextField(blank=True, help_text="Text shown at the top of the category page.")
    image = models.ImageField(upload_to=upload_to("categories"), blank=True)
    order = models.PositiveIntegerField(default=0)
    show_in_menu = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("category", args=[self.slug])

    @property
    def label(self):
        return self.menu_label or self.name

    @property
    def intro_paragraphs(self):
        return paragraphs(self.intro)


class TourQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True, category__is_active=True)


class Tour(OptimisedImagesMixin, SEOFields):
    IMAGE_FIELDS = ("image",)
    image_widths = models.JSONField(default=dict, blank=True, editable=False)

    STYLE_PRIVATE = "private"
    STYLE_GROUP = "group"
    STYLE_CHOICES = [(STYLE_PRIVATE, "Private tour"), (STYLE_GROUP, "Group joining")]
    LEVEL_CHOICES = [
        ("", "—"),
        ("camping", "Camping"),
        ("budget", "Budget"),
        ("mid-range", "Mid-range lodges"),
        ("luxury", "Luxury"),
    ]

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="tours")
    title = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    summary = models.CharField(max_length=300, blank=True, help_text="One or two lines shown on tour cards.")
    image = models.ImageField("Main photo", upload_to=upload_to("tours"), blank=True)

    duration_days = models.PositiveIntegerField(default=1, help_text="Use 1 for day trips.")
    duration_label = models.CharField(
        max_length=40, blank=True, help_text="Optional, e.g. '7 Days / 6 Nights' or 'Half day'. Auto if empty."
    )
    style = models.CharField("Tour style", max_length=20, choices=STYLE_CHOICES, default=STYLE_PRIVATE)
    level = models.CharField("Accommodation level", max_length=20, choices=LEVEL_CHOICES, blank=True)
    tour_type = models.CharField(max_length=80, blank=True, help_text="e.g. Game drive, Hiking, Beach & culture")
    group_size = models.CharField(max_length=60, blank=True, default="1 to 12 people")
    destinations = models.CharField(max_length=250, blank=True, help_text="Parks / places visited.")
    start_point = models.CharField(max_length=120, blank=True, default="Kilimanjaro Airport / Moshi / Arusha")
    end_point = models.CharField(max_length=120, blank=True, default="Kilimanjaro Airport / Moshi / Arusha")

    overview = models.TextField(blank=True, help_text="Separate paragraphs with an empty line.")
    highlights = models.TextField(blank=True, help_text="One highlight per line.")
    included = models.TextField("What's included", blank=True, help_text="One item per line.")
    excluded = models.TextField("Not included", blank=True, help_text="One item per line.")

    price_from = models.DecimalField(
        "Price from (USD)",
        max_digits=9,
        decimal_places=0,
        null=True,
        blank=True,
        help_text="Leave empty to show 'Price on request'.",
    )
    price_old = models.DecimalField(
        "Old price (USD)", max_digits=9, decimal_places=0, null=True, blank=True, help_text="Optional, shown crossed out."
    )
    price_note = models.CharField(max_length=80, blank=True, default="per person")

    is_featured = models.BooleanField("Show on home page", default=False)
    is_published = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    legacy_path = models.CharField(
        max_length=200,
        blank=True,
        db_index=True,
        help_text="Old website address (e.g. 7days-kilimanjaro-climb-machame-route.php) redirected here for SEO.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TourQuerySet.as_manager()

    class Meta:
        ordering = ["category__order", "order", "duration_days", "title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:160]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("tour", args=[self.category.slug, self.slug])

    @property
    def duration_text(self):
        if self.duration_label:
            return self.duration_label
        if self.duration_days <= 1:
            return "Day trip"
        nights = self.duration_days - 1
        return f"{self.duration_days} Days / {nights} Night{'s' if nights != 1 else ''}"

    @property
    def short_duration(self):
        return "Day trip" if self.duration_days <= 1 else f"{self.duration_days} days"

    @property
    def is_group(self):
        return self.style == self.STYLE_GROUP

    @property
    def overview_paragraphs(self):
        return paragraphs(self.overview)

    @property
    def highlight_list(self):
        return lines(self.highlights)

    @property
    def included_list(self):
        return lines(self.included)

    @property
    def excluded_list(self):
        return lines(self.excluded)

    @property
    def seo_title(self):
        return self.meta_title or f"{self.title} | {self.duration_text}"

    @property
    def seo_description(self):
        if self.meta_description:
            return self.meta_description
        text = self.summary or (self.overview_paragraphs[0] if self.overview_paragraphs else self.title)
        return (text[:157].rsplit(" ", 1)[0] + "...") if len(text) > 160 else text


class TourDay(OptimisedImagesMixin, models.Model):
    IMAGE_FIELDS = ("image",)
    image_widths = models.JSONField(default=dict, blank=True, editable=False)
    IMAGE_MAX_WIDTH = 1200

    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name="days")
    day_number = models.PositiveIntegerField("Day", default=1)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    accommodation = models.CharField(max_length=200, blank=True)
    meals = models.CharField(max_length=120, blank=True)
    elevation = models.CharField(max_length=120, blank=True)
    distance = models.CharField(max_length=80, blank=True)
    hiking_time = models.CharField(max_length=80, blank=True)
    habitat = models.CharField(max_length=80, blank=True)
    activity = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to=upload_to("days"), blank=True)

    class Meta:
        ordering = ["day_number", "id"]
        verbose_name = "itinerary day"

    def __str__(self):
        return f"Day {self.day_number}: {self.title}"

    @property
    def paragraphs(self):
        return paragraphs(self.description)

    @property
    def facts(self):
        pairs = [
            ("Accommodation", self.accommodation),
            ("Meals", self.meals),
            ("Elevation", self.elevation),
            ("Distance", self.distance),
            ("Hiking time", self.hiking_time),
            ("Habitat", self.habitat),
            ("Activities", self.activity),
        ]
        return [(k, v) for k, v in pairs if v]


class TourPrice(models.Model):
    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name="prices")
    label = models.CharField(max_length=80, help_text="e.g. Solo traveller, 2-3 people, 4+ people")
    price = models.DecimalField("Price per person (USD)", max_digits=9, decimal_places=0)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "price option"

    def __str__(self):
        return f"{self.label}: ${self.price}"


class TourImage(OptimisedImagesMixin, models.Model):
    IMAGE_FIELDS = ("image",)
    image_widths = models.JSONField(default=dict, blank=True, editable=False)

    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name="gallery")
    image = models.ImageField(upload_to=upload_to("gallery"))
    caption = models.CharField(max_length=150, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "gallery photo"

    def __str__(self):
        return self.caption or f"Photo {self.pk}"


# ---------------------------------------------------------------------------
# Group joining departures
# ---------------------------------------------------------------------------
class DepartureQuerySet(models.QuerySet):
    def upcoming(self):
        return self.filter(is_published=True, start_date__gte=datetime.date.today())


class GroupDeparture(models.Model):
    KIND_CHOICES = [("kilimanjaro", "Kilimanjaro climb"), ("safari", "Safari"), ("other", "Other")]
    STATUS_CHOICES = [
        ("open", "Open for booking"),
        ("guaranteed", "Guaranteed departure"),
        ("few", "Few spaces left"),
        ("full", "Fully booked"),
    ]

    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default="kilimanjaro")
    tour = models.ForeignKey(
        Tour,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="departures",
        help_text="The package this group follows (links to its itinerary).",
    )
    title = models.CharField(max_length=150, blank=True, help_text="Leave empty to use the tour name.")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Filled automatically from the tour length if empty.")
    price = models.DecimalField("Price per person (USD)", max_digits=9, decimal_places=0)
    deposit_percent = models.PositiveIntegerField(default=30)
    total_spaces = models.PositiveIntegerField(default=12)
    booked_spaces = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    note = models.CharField(max_length=200, blank=True, help_text="e.g. Full moon summit, Calving season")
    is_published = models.BooleanField(default=True)

    objects = DepartureQuerySet.as_manager()

    class Meta:
        ordering = ["start_date", "kind"]
        verbose_name = "group departure"

    def __str__(self):
        return f"{self.name} — {self.start_date:%d %b %Y}"

    def save(self, *args, **kwargs):
        if not self.end_date and self.tour_id:
            self.end_date = self.start_date + datetime.timedelta(days=max(self.tour.duration_days - 1, 0))
        super().save(*args, **kwargs)

    @property
    def name(self):
        return self.title or (self.tour.title if self.tour else "Group departure")

    @property
    def spaces_left(self):
        return max(self.total_spaces - self.booked_spaces, 0)

    @property
    def is_full(self):
        return self.status == "full" or self.spaces_left == 0

    @property
    def display_status(self):
        if self.is_full:
            return "full", "Fully booked"
        if self.status == "guaranteed":
            return "guaranteed", "Guaranteed"
        if self.status == "few" or self.spaces_left <= 3:
            return "few", f"Only {self.spaces_left} left"
        return "open", f"{self.spaces_left} spaces left"

    @property
    def deposit(self):
        return round(self.price * self.deposit_percent / 100)

    @property
    def days(self):
        if self.end_date:
            return (self.end_date - self.start_date).days + 1
        return self.tour.duration_days if self.tour else None


# ---------------------------------------------------------------------------
# Enquiries / bookings from the website
# ---------------------------------------------------------------------------
class Enquiry(models.Model):
    SOURCE_CHOICES = [
        ("tour", "Tour booking form"),
        ("departure", "Join group departure"),
        ("plan", "Plan my trip"),
        ("contact", "Contact page"),
    ]
    STATUS_CHOICES = [
        ("new", "New"),
        ("replied", "Replied"),
        ("booked", "Booked / paid"),
        ("closed", "Closed / lost"),
    ]

    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="contact")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    tour = models.ForeignKey(Tour, on_delete=models.SET_NULL, null=True, blank=True, related_name="enquiries")
    departure = models.ForeignKey(
        GroupDeparture, on_delete=models.SET_NULL, null=True, blank=True, related_name="enquiries"
    )
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField("Phone / WhatsApp", max_length=40, blank=True)
    country = models.CharField(max_length=80, blank=True)
    travel_date = models.DateField(null=True, blank=True)
    adults = models.PositiveIntegerField(default=2)
    children = models.PositiveIntegerField(default=0)
    budget = models.CharField(max_length=60, blank=True)
    interests = models.CharField(max_length=250, blank=True)
    message = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True, help_text="Private notes, not visible to the customer.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "enquiry"
        verbose_name_plural = "enquiries"

    def __str__(self):
        return f"{self.full_name} — {self.subject}"

    @property
    def subject(self):
        if self.departure:
            return f"Join group: {self.departure}"
        if self.tour:
            return self.tour.title
        return self.get_source_display()

    @property
    def travellers(self):
        return self.adults + self.children


# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------
class Testimonial(models.Model):
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=80, blank=True)
    trip = models.CharField(max_length=120, blank=True, help_text="e.g. 7 Days Machame Route")
    text = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5)
    source = models.CharField(max_length=40, blank=True, default="TripAdvisor")
    is_published = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "-id"]
        verbose_name = "review"

    def __str__(self):
        return f"{self.name} ({self.country})"

    @property
    def stars(self):
        return range(min(self.rating, 5))


class FAQ(models.Model):
    GROUP_CHOICES = [
        ("general", "General travel"),
        ("kilimanjaro", "Kilimanjaro"),
        ("safari", "Safari"),
        ("zanzibar", "Zanzibar"),
        ("booking", "Booking & payment"),
    ]
    group = models.CharField(max_length=20, choices=GROUP_CHOICES, default="general")
    question = models.CharField(max_length=250)
    answer = models.TextField()
    show_on_home = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["group", "order", "id"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question

    @property
    def answer_paragraphs(self):
        return paragraphs(self.answer)


class Page(OptimisedImagesMixin, SEOFields):
    """Simple content pages: terms, responsible travel, travel guides, etc."""

    IMAGE_FIELDS = ("image",)
    KIND_CHOICES = [("page", "Information page"), ("guide", "Travel guide / blog article")]
    image_widths = models.JSONField(default=dict, blank=True, editable=False)

    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default="page")
    title = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    intro = models.CharField(max_length=300, blank=True)
    body = models.TextField(
        help_text="Separate paragraphs with an empty line. Start a line with '## ' for a heading and '- ' for a bullet."
    )
    image = models.ImageField(upload_to=upload_to("pages"), blank=True)
    show_in_footer = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    legacy_path = models.CharField(max_length=200, blank=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("page", args=[self.slug])

    @property
    def seo_title(self):
        return self.meta_title or self.title

    @property
    def seo_description(self):
        return self.meta_description or self.intro or self.title
