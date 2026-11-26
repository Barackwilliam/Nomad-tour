import datetime
import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.template.loader import get_template
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Category, Enquiry, GroupDeparture, SiteSettings, Tour

MEDIA = tempfile.mkdtemp()


@override_settings(
    MEDIA_ROOT=MEDIA,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    EMAIL_ASYNC=False,
    BREVO_API_KEY="",
    EMAIL_HOST="",
)
class SiteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_site", "--no-images", stdout=io.StringIO())
        settings = SiteSettings.get()
        settings.departures_year = datetime.date.today().year + 1
        settings.save()
        cls.tour = Tour.objects.get(slug="7-days-kilimanjaro-climb-machame-route")
        cls.departure = GroupDeparture.objects.create(
            kind="kilimanjaro",
            tour=cls.tour,
            start_date=datetime.date(settings.departures_year, 6, 5),
            price=1700,
        )

    def setUp(self):
        cache.clear()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def test_seed_is_idempotent(self):
        before = (Tour.objects.count(), GroupDeparture.objects.count())
        call_command("seed_site", "--no-images", stdout=io.StringIO())
        self.assertEqual(before, (Tour.objects.count(), GroupDeparture.objects.count()))
        self.assertGreaterEqual(Tour.objects.count(), 45)

    def test_every_template_compiles(self):
        import pathlib

        root = pathlib.Path(__file__).parent / "templates"
        for path in root.rglob("*.html"):
            get_template(str(path.relative_to(root)))

    def test_public_pages(self):
        cat = self.tour.category
        urls = [
            "/", "/tours/", "/tours/?category=day-trips&days=1&sort=price", "/tours/?q=serengeti",
            cat.get_absolute_url(), cat.get_absolute_url() + "?level=camping", self.tour.get_absolute_url(),
            "/group-departures/", "/group-departures/?type=safari&month=2027-07", "/group-departures/?month=bad", "/plan-your-trip/",
            "/plan-your-trip/?trip=Kilimanjaro+climb&month=June+2027&tour=" + self.tour.slug,
            "/contact/", "/about-us/", "/faq/", "/travel-guides/", "/info/booking-terms-and-conditions/",
            "/thank-you/", "/sitemap.xml", "/robots.txt",
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_every_tour_page_renders(self):
        for tour in Tour.objects.published().select_related("category"):
            with self.subTest(tour=tour.slug):
                res = self.client.get(tour.get_absolute_url())
                self.assertEqual(res.status_code, 200)
                self.assertContains(res, "application/ld+json")

    def test_about_page_sections(self):
        res = self.client.get("/about-us/")
        for text in ("Who we are", "Our mission", "Our vision", "Our values", "Authenticity", "Personalized Service",
                     "Travel Local. Explore More. Experience Tanzania."):
            self.assertContains(res, text)

    def test_404(self):
        self.assertEqual(self.client.get("/no-such-page/").status_code, 404)
        self.assertEqual(self.client.get("/kilimanjaro-climbing/no-such-tour/").status_code, 404)

    def test_wrong_category_redirects_to_canonical(self):
        res = self.client.get(f"/day-trips/{self.tour.slug}/")
        self.assertRedirects(res, self.tour.get_absolute_url(), status_code=301)

    def test_old_php_addresses_redirect(self):
        res = self.client.get("/7days-kilimanjaro-climb-machame-route.php")
        self.assertRedirects(res, self.tour.get_absolute_url(), status_code=301)
        self.assertRedirects(self.client.get("/company-profile.php"), "/about-us/", status_code=301, fetch_redirect_response=False)
        self.assertEqual(self.client.get("/unknown-page.php").status_code, 404)

    def test_tour_booking_creates_enquiry_and_email(self):
        res = self.client.post(
            self.tour.get_absolute_url(),
            {
                "form": "enquiry", "full_name": "Jane Doe", "email": "jane@example.com", "phone": "+44 7700 900000",
                "travel_date": (datetime.date.today() + datetime.timedelta(days=90)).isoformat(),
                "adults": 2, "children": 0, "message": "Hello",
            },
        )
        self.assertRedirects(res, reverse("thank_you"))
        enquiry = Enquiry.objects.get()
        self.assertEqual(enquiry.tour, self.tour)
        self.assertEqual(enquiry.source, "tour")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.tour.title, mail.outbox[0].subject)
        self.assertContains(self.client.get(reverse("thank_you")), "Jane")

    def _book(self):
        return self.client.post(
            self.tour.get_absolute_url(),
            {"form": "enquiry", "full_name": "Jane Doe", "email": "jane@example.com", "adults": 2},
        )

    def test_notification_reply_goes_to_customer_and_customer_gets_confirmation(self):
        with self.settings(EMAIL_HOST="mail.example.com"):
            self._book()
        self.assertEqual(len(mail.outbox), 2)
        notify, confirm = mail.outbox
        self.assertEqual(notify.reply_to, ["jane@example.com"])
        self.assertEqual(confirm.to, ["jane@example.com"])
        self.assertIn("We received your enquiry", confirm.subject)

    def test_brevo_api_is_used_when_key_is_set(self):
        from unittest import mock
        import json as _json

        calls = []

        class Res:
            status = 201
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def fake_urlopen(req, timeout=0):
            calls.append((req.full_url, req.headers, _json.loads(req.data)))
            return Res()

        with self.settings(BREVO_API_KEY="xkeysib-test"), mock.patch("urllib.request.urlopen", fake_urlopen):
            self._book()
        self.assertEqual(len(calls), 2)
        url, headers, payload = calls[0]
        self.assertEqual(url, "https://api.brevo.com/v3/smtp/email")
        self.assertEqual(headers["Api-key"], "xkeysib-test")
        self.assertEqual(payload["replyTo"]["email"], "jane@example.com")
        self.assertIn(self.tour.title, payload["subject"])
        self.assertEqual(len(mail.outbox), 0)

    def test_email_failure_never_loses_the_enquiry(self):
        from unittest import mock

        with self.settings(EMAIL_HOST="mail.example.com"), mock.patch(
            "django.core.mail.EmailMessage.send", side_effect=OSError("Network unreachable")
        ):
            res = self._book()
        self.assertRedirects(res, reverse("thank_you"))
        self.assertEqual(Enquiry.objects.count(), 1)

    def test_invalid_booking_shows_errors(self):
        res = self.client.post(self.tour.get_absolute_url(), {"form": "enquiry", "full_name": "", "email": "bad"})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "field__error")
        self.assertEqual(Enquiry.objects.count(), 0)

    def test_past_travel_date_rejected(self):
        res = self.client.post(
            "/contact/",
            {"form": "enquiry", "full_name": "A", "email": "a@example.com", "travel_date": "2001-01-01"},
        )
        self.assertContains(res, "future")
        self.assertEqual(Enquiry.objects.count(), 0)

    def test_spam_honeypot_is_ignored(self):
        res = self.client.post(
            "/contact/", {"form": "enquiry", "full_name": "Bot", "email": "bot@example.com", "website": "http://spam"}
        )
        self.assertRedirects(res, reverse("thank_you"))
        self.assertEqual(Enquiry.objects.count(), 0)

    def test_join_group_departure(self):
        res = self.client.post(
            "/group-departures/",
            {"form": "enquiry", "departure_id": self.departure.pk, "full_name": "Sam", "email": "sam@example.com", "adults": 1},
        )
        self.assertRedirects(res, reverse("thank_you"))
        enquiry = Enquiry.objects.get()
        self.assertEqual(enquiry.departure, self.departure)
        self.assertEqual(enquiry.tour, self.tour)
        self.assertEqual(enquiry.travel_date, self.departure.start_date)

    def test_departure_links_to_itinerary_with_date_selected(self):
        url = self.departure.get_absolute_url()
        self.assertEqual(url, f"{self.tour.get_absolute_url()}?departure={self.departure.pk}#book")
        self.assertContains(self.client.get("/group-departures/"), f"?departure={self.departure.pk}#book")
        res = self.client.get(f"{self.tour.get_absolute_url()}?departure={self.departure.pk}")
        self.assertContains(res, "Joining a group departure")
        self.assertContains(res, f'name="departure_id" value="{self.departure.pk}"')
        self.assertContains(res, self.departure.start_date.isoformat())  # travel date filled in
        # booking from the itinerary page is linked to that departure
        res = self.client.post(
            f"{self.tour.get_absolute_url()}?departure={self.departure.pk}",
            {"form": "enquiry", "departure_id": self.departure.pk, "full_name": "Ana", "email": "ana@example.com", "adults": 2},
        )
        self.assertRedirects(res, reverse("thank_you"))
        enquiry = Enquiry.objects.get()
        self.assertEqual((enquiry.source, enquiry.departure, enquiry.tour), ("departure", self.departure, self.tour))
        self.assertEqual(enquiry.travel_date, self.departure.start_date)

    def test_unknown_or_full_departure_is_ignored(self):
        res = self.client.get(f"{self.tour.get_absolute_url()}?departure=999999")
        self.assertNotContains(res, "Joining a group departure")
        self.departure.status = "full"
        self.departure.save()
        res = self.client.get(f"{self.tour.get_absolute_url()}?departure={self.departure.pk}")
        self.assertNotContains(res, "Joining a group departure")

    def test_departures_shown_from_today_until_end_of_year(self):
        soon = GroupDeparture.objects.create(
            kind="safari", tour=self.tour, start_date=datetime.date.today() + datetime.timedelta(days=5), price=900
        )
        past = GroupDeparture.objects.create(
            kind="safari", tour=self.tour, start_date=datetime.date.today() - datetime.timedelta(days=5), price=900
        )
        res = self.client.get("/group-departures/")
        self.assertContains(res, f'id="dep-{soon.pk}"')
        self.assertNotContains(res, f'id="dep-{past.pk}"')
        self.assertContains(res, "Kilimanjaro &amp; mountain climbs")
        self.assertContains(res, "Group joining safaris")
        self.assertContains(res, f"until December {SiteSettings.get().departures_year}")
        res = self.client.get("/group-departures/?type=safari")
        self.assertNotContains(res, "Kilimanjaro &amp; mountain climbs")
        month = soon.start_date.strftime("%Y-%m")
        self.assertContains(self.client.get(f"/group-departures/?month={month}"), f'id="dep-{soon.pk}"')

    def test_departures_only_show_configured_year(self):
        other = GroupDeparture.objects.create(
            kind="safari", tour=self.tour, start_date=datetime.date(SiteSettings.get().departures_year + 1, 1, 10), price=900
        )
        res = self.client.get("/group-departures/")
        self.assertContains(res, f'id="dep-{self.departure.pk}"')
        self.assertNotContains(res, f'id="dep-{other.pk}"')

    def test_departure_status(self):
        d = self.departure
        self.assertEqual(d.display_status[0], "open")
        d.booked_spaces = 10
        self.assertEqual(d.display_status[0], "few")
        d.booked_spaces = 12
        self.assertTrue(d.is_full)
        self.assertEqual(d.deposit, 510)
        self.assertEqual(d.end_date, d.start_date + datetime.timedelta(days=self.tour.duration_days - 1))

    def test_unpublished_tour_hidden(self):
        self.tour.is_published = False
        self.tour.save()
        self.assertEqual(self.client.get(self.tour.get_absolute_url()).status_code, 404)
        self.assertNotContains(self.client.get("/tours/"), self.tour.get_absolute_url())

    def test_uploaded_image_is_converted_to_webp(self):
        buf = io.BytesIO()
        Image.new("RGB", (3000, 2000), "orange").save(buf, "JPEG")
        cat = Category.objects.first()
        cat.image = SimpleUploadedFile("Big Photo.JPG", buf.getvalue(), content_type="image/jpeg")
        cat.save()
        self.assertTrue(cat.image.name.endswith(".webp"))
        with Image.open(cat.image.path) as im:
            self.assertEqual(im.format, "WEBP")
            self.assertLessEqual(im.width, 1920)
        # responsive copies exist and are used in srcset
        from .images import variant_name
        from .templatetags.tour_tags import picture

        cat.refresh_from_db()
        self.assertEqual(cat.image_widths["image"], [480, 800, 1200, 1920])
        for w in (480, 800, 1200):
            self.assertTrue(cat.image.storage.exists(variant_name(cat.image.name, w)))
        html = picture(cat.image, alt="x", sizes="50vw")
        self.assertIn("-w480.webp 480w", html)
        self.assertIn("1920w", html)

    def test_dashboard_change_refreshes_cached_pages(self):
        self.assertContains(self.client.get(self.tour.get_absolute_url()), self.tour.title)
        self.tour.title = "Brand new title for the climb"
        self.tour.save()
        self.assertContains(self.client.get(self.tour.get_absolute_url()), "Brand new title for the climb")

    def test_home_has_seasons_and_slides(self):
        res = self.client.get("/")
        self.assertContains(res, "When to go to")
        self.assertContains(res, "data-seasons")
        self.assertContains(res, 'type="speculationrules"')

    def test_admin_pages(self):
        User = get_user_model()
        User.objects.create_superuser("boss", "boss@example.com", "pass12345!")
        self.client.login(username="boss", password="pass12345!")
        for url in [
            "/admin/", "/admin/tours/tour/", f"/admin/tours/tour/{self.tour.pk}/change/", "/admin/tours/tour/add/",
            "/admin/tours/groupdeparture/", "/admin/tours/enquiry/", "/admin/tours/category/",
            "/admin/tours/faq/", "/admin/tours/page/", "/admin/tours/testimonial/",
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        res = self.client.get("/admin/tours/sitesettings/")
        self.assertRedirects(res, "/admin/tours/sitesettings/1/change/")

    def test_duplicate_tour_action(self):
        User = get_user_model()
        User.objects.create_superuser("boss", "boss@example.com", "pass12345!")
        self.client.login(username="boss", password="pass12345!")
        days = self.tour.days.count()
        self.client.post(
            "/admin/tours/tour/", {"action": "duplicate_tours", "_selected_action": [self.tour.pk]}
        )
        copy = Tour.objects.get(slug=self.tour.slug + "-copy")
        self.assertFalse(copy.is_published)
        self.assertEqual(copy.days.count(), days)
