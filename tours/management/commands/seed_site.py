import datetime
import json
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from tours.models import FAQ, Category, GroupDeparture, Page, SiteSettings, Tour, TourDay, TourImage, TourPrice

SEED = Path(__file__).resolve().parents[2] / "seed"


class Command(BaseCommand):
    help = (
        "Load the starting content (tours, categories, 2027 group departures, FAQs, pages and photos). "
        "Safe to run many times: existing records are left alone unless --update is given."
    )

    def add_arguments(self, parser):
        parser.add_argument("--update", action="store_true", help="Overwrite records that already exist.")
        parser.add_argument("--no-images", action="store_true", help="Skip uploading photos (faster, for tests).")
        parser.add_argument(
            "--if-empty", action="store_true",
            help="Only run when there are no tours yet (used on every deploy, so deleted tours never come back).",
        )

    def handle(self, *args, **opts):
        if opts["if_empty"] and Tour.objects.exists():
            self.stdout.write("Tours already exist; skipping seed data.")
            return
        self.update = opts["update"]
        self.images = not opts["no_images"]
        data = json.loads((SEED / "data.json").read_text())
        with transaction.atomic():
            self.load_settings(data["settings"])
            cats = self.load_categories(data["categories"])
            tours = self.load_tours(data["tours"], cats)
            self.load_departures(data["departures"], tours)
            self.load_faqs(data["faqs"])
            self.load_pages(data["pages"])
        self.stdout.write(self.style.SUCCESS("Seed data loaded."))

    # -- helpers ------------------------------------------------------------
    def attach(self, obj, field, name):
        """Upload seed/images/<name> into obj.<field> (to Supabase when configured)."""
        if not (self.images and name):
            return
        current = getattr(obj, field)
        if current and not self.update:
            return
        path = SEED / "images" / name
        if not path.exists():
            self.stderr.write(f"  missing image {name}")
            return
        with path.open("rb") as fh:
            getattr(obj, field).save(name, File(fh), save=False)

    # -- loaders ------------------------------------------------------------
    def load_settings(self, d):
        s = SiteSettings.get()
        changed = False
        for field in ("about_text", "intro_text", "who_we_are", "mission", "vision", "values", "about_closing_text"):
            if not getattr(s, field) or self.update:
                setattr(s, field, d[field])
                changed = True
        for field, key in (("hero_image", "hero_image"), ("hero_image_2", "hero_image_2"), ("hero_image_3", "hero_image_3"),
                           ("about_image", "about_image"), ("cta_image", "cta_image")):
            if self.images and (not getattr(s, field) or self.update):
                self.attach(s, field, d[key])
                changed = True
        if changed:
            s.save()
        self.stdout.write("Site settings ready")

    def load_categories(self, items):
        out = {}
        for c in items:
            obj = Category.objects.filter(slug=c["slug"]).first()
            if obj is None or self.update:
                obj = obj or Category(slug=c["slug"])
                for f in ("name", "menu_label", "tagline", "intro", "order", "meta_title", "meta_description", "show_in_menu"):
                    setattr(obj, f, c[f])
            self.attach(obj, "image", c["image"])
            obj.save()
            out[c["slug"]] = obj
        self.stdout.write(f"{len(out)} categories")
        return out

    def load_tours(self, items, cats):
        out, created = {}, 0
        for t in items:
            obj = Tour.objects.filter(slug=t["slug"]).first()
            is_new = obj is None
            if is_new or self.update:
                obj = obj or Tour(slug=t["slug"])
                obj.category = cats[t["category"]]
                for f in (
                    "title", "summary", "duration_days", "duration_label", "style", "level", "tour_type", "group_size",
                    "destinations", "start_point", "end_point", "overview", "highlights", "included", "excluded",
                    "price_from", "is_featured", "order", "legacy_path",
                ):
                    setattr(obj, f, t[f])
            self.attach(obj, "image", t["image"])
            obj.save()
            if is_new or self.update:
                created += is_new
                obj.days.all().delete()
                TourDay.objects.bulk_create([TourDay(tour=obj, **d) for d in t["days"]])
                obj.prices.all().delete()
                TourPrice.objects.bulk_create(
                    [TourPrice(tour=obj, label=p["label"], price=p["price"], order=i) for i, p in enumerate(t["prices"])]
                )
                if self.images:
                    obj.gallery.all().delete()
                    for i, name in enumerate(t["gallery"]):
                        g = TourImage(tour=obj, order=i)
                        self.attach(g, "image", name)
                        if g.image:
                            g.save()
            out[t["slug"]] = obj
        self.stdout.write(f"{len(out)} tours ({created} new)")
        return out

    def load_departures(self, items, tours):
        n = 0
        for d in items:
            tour = tours.get(d["tour"])
            start = datetime.date.fromisoformat(d["start"])
            if GroupDeparture.objects.filter(tour=tour, start_date=start).exists():
                continue
            if d["price"] is None:
                continue
            GroupDeparture.objects.create(kind=d["kind"], tour=tour, start_date=start, price=d["price"], note=d["note"])
            n += 1
        self.stdout.write(f"{n} new group departures")

    def load_faqs(self, items):
        n = 0
        for f in items:
            if FAQ.objects.filter(question=f["question"]).exists():
                continue
            FAQ.objects.create(**f)
            n += 1
        self.stdout.write(f"{n} new FAQs")

    def load_pages(self, items):
        for p in items:
            obj = Page.objects.filter(slug=p["slug"]).first()
            if obj is None or self.update:
                obj = obj or Page(slug=p["slug"])
                for f in ("title", "kind", "intro", "body", "show_in_footer", "order", "legacy_path"):
                    setattr(obj, f, p[f])
            self.attach(obj, "image", p["image"])
            obj.save()
        self.stdout.write(f"{len(items)} pages")
