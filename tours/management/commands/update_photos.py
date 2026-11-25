"""Swap in the client's new photos (December 2026).

Each entry only replaces a photo that is still the original seed photo, so pictures the
client has uploaded himself in the dashboard are never overwritten. Safe to run many times.
"""
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand

from tours import cache as content_cache
from tours.models import Category, SiteSettings, Tour

SEED = Path(__file__).resolve().parents[2] / "seed" / "images"

SETTINGS = {  # field: (old seed photo, new photo)
    "hero_image": ("12-safari-tanzania", "safari-photographer-elephants"),
    "hero_image_2": ("north", "elephant-crossing-safari-vehicle"),
    "hero_image_3": ("beach-holiday", "rhino-mother-calf"),
    "cta_image": ("ngorongoro-day2", "misty-giraffes-zebras"),
}
CATEGORIES = {"tanzania-safaris": ("12-safari-tanzania", "elephant-land-cruiser-ngorongoro")}
TOURS = {
    "2-days-tanzania-camping-safari": ("2days-tanzania-camping-safari", "giraffes-zebras-eland"),
    "4-days-wild-and-culture-mid-range-safari": ("4days-midrange-safari", "elephant-crossing-safari-vehicle"),
    "8-days-tanzania-budget-camping-safari": ("8days-tanzania-camping-safari", "lion-cubs-playing"),
    "4-days-budget-camping-safari-serengeti-ngorongoro-and-tarangire": ("4days-camping-safari", "rhinos-group"),
    "4-days-group-joining-wildebeest-migration-safari": ("12-safari-tanzania", "giraffe-golden-grass"),
    "3-days-serengeti-and-ngorongoro-lodge-safari": ("3days-midrange-safari", "zebra-foal-ngorongoro"),
    "ngorongoro-crater-day-trip": ("ngorongoro-day2", "lion-safari-vehicle-ngorongoro"),
}


def is_original(field_file, old_stem):
    name = Path(field_file.name or "").name
    return not name or name.startswith(old_stem + "-") or name == old_stem + ".webp"


class Command(BaseCommand):
    help = "Replace the original seed photos with the client's new photos (keeps any photo uploaded later)."

    def swap(self, obj, field, old, new):
        ff = getattr(obj, field)
        if not is_original(ff, old):
            return False
        with (SEED / f"{new}.webp").open("rb") as fh:
            getattr(obj, field).save(f"{new}.webp", File(fh), save=False)
        return True

    def handle(self, *args, **opts):
        n = 0
        s = SiteSettings.get()
        changed = [f for f, (old, new) in SETTINGS.items() if self.swap(s, f, old, new)]
        if changed:
            s.save()
            n += len(changed)
        for slug, (old, new) in CATEGORIES.items():
            obj = Category.objects.filter(slug=slug).first()
            if obj and self.swap(obj, "image", old, new):
                obj.save()
                n += 1
        for slug, (old, new) in TOURS.items():
            obj = Tour.objects.filter(slug=slug).first()
            if obj and self.swap(obj, "image", old, new):
                obj.save()
                n += 1
        content_cache.bump()
        self.stdout.write(self.style.SUCCESS(f"{n} photos updated."))
