"""Image helpers.

Every uploaded photo is resized and converted to WebP before it is stored, and
smaller copies (480, 800 and 1200 px wide) are saved next to it. Templates use them in
`srcset`, so a phone downloads a ~40 KB image instead of the full-size photo.
"""
import io
import logging
import os
import uuid

from django.core.files.base import ContentFile
from django.utils.deconstruct import deconstructible
from django.utils.text import slugify
from PIL import Image, ImageOps

log = logging.getLogger("tours")

MAX_WIDTH = 1920
QUALITY = 80
VARIANT_WIDTHS = (480, 800, 1200)


@deconstructible
class upload_to:
    """upload_to callable that names files <folder>/<slug>-<random>.webp."""

    def __init__(self, folder):
        self.folder = folder

    def __call__(self, instance, filename):
        base = slugify(os.path.splitext(os.path.basename(filename))[0])[:60] or "image"
        return f"{self.folder}/{base}-{uuid.uuid4().hex[:8]}.webp"

    def __eq__(self, other):
        return isinstance(other, upload_to) and other.folder == self.folder


def variant_name(name, width):
    base, _ext = os.path.splitext(name)
    return f"{base}-w{width}.webp"


def optimise(field_file, max_width=MAX_WIDTH):
    """Convert a freshly uploaded (not yet saved) image to an optimised WebP in place."""
    if not field_file or getattr(field_file, "_committed", True):
        return
    try:
        field_file.open()
        img = Image.open(field_file)
        if img.format == "WEBP" and img.width <= max_width:
            field_file.seek(0)
            return  # already optimised
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
        if img.width > max_width:
            img.thumbnail((max_width, max_width * 4), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "WEBP", quality=QUALITY, method=5)
    except Exception:
        return  # not an image we can read; keep the original
    name = os.path.splitext(os.path.basename(field_file.name))[0] + ".webp"
    field_file.save(name, ContentFile(buf.getvalue()), save=False)


def make_variants(field_file):
    """Save the smaller copies of an image (skips widths larger than the original).
    Returns the copy widths followed by the original's width, e.g. [480, 960, 1600]."""
    if not field_file or not field_file.name:
        return []
    storage = field_file.storage
    try:
        with storage.open(field_file.name, "rb") as fh:
            img = Image.open(fh)
            img.load()
    except Exception:
        log.warning("Could not open %s to make image variants", field_file.name)
        return []
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    done = []
    for width in VARIANT_WIDTHS:
        if img.width <= width:
            continue
        copy = img.copy()
        copy.thumbnail((width, width * 4), Image.LANCZOS)
        buf = io.BytesIO()
        copy.save(buf, "WEBP", quality=74, method=5)
        name = variant_name(field_file.name, width)
        if storage.exists(name):
            storage.delete(name)
        storage.save(name, ContentFile(buf.getvalue()))
        done.append(width)
    return done + [img.width]  # last item: width of the original


def image_width(field_file):
    """Width of the stored image, read from the file header (cheap)."""
    try:
        with field_file.storage.open(field_file.name, "rb") as fh:
            return Image.open(fh).width
    except Exception:
        return 0


class OptimisedImagesMixin:
    """Model mixin: optimise every ImageField listed in IMAGE_FIELDS on save and
    keep the small responsive copies in sync. The widths that exist are stored in
    `image_widths` so templates never point at a missing file."""

    IMAGE_FIELDS = ()
    IMAGE_MAX_WIDTH = MAX_WIDTH

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._image_names = {f: self._raw_image_name(f) for f in self.IMAGE_FIELDS}

    def _raw_image_name(self, field):
        # Read from __dict__ so deferred fields (.only()) don't trigger extra queries.
        value = self.__dict__.get(field)
        return getattr(value, "name", value) or ""

    def save(self, *args, **kwargs):
        for name in self.IMAGE_FIELDS:
            optimise(getattr(self, name), self.IMAGE_MAX_WIDTH)
        super().save(*args, **kwargs)
        changed = {}
        for field in self.IMAGE_FIELDS:
            current = self._raw_image_name(field)
            if current and current != self._image_names.get(field):
                changed[field] = make_variants(getattr(self, field))
            elif not current:
                changed[field] = []
            self._image_names[field] = current
        if changed and hasattr(self, "image_widths"):
            widths = dict(self.image_widths or {})
            widths.update({k: v for k, v in changed.items()})
            if widths != (self.image_widths or {}):
                self.image_widths = widths
                type(self).objects.filter(pk=self.pk).update(image_widths=widths)

    def srcset_widths(self, field):
        return (self.image_widths or {}).get(field, [])
