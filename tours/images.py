"""Image helpers: every uploaded photo is resized and converted to WebP before it
is stored, so pages stay fast even when the admin uploads 8 MB phone photos."""
import io
import os
import uuid

from django.core.files.base import ContentFile
from django.utils.deconstruct import deconstructible
from django.utils.text import slugify
from PIL import Image, ImageOps

MAX_WIDTH = 1920
QUALITY = 80


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


class OptimisedImagesMixin:
    """Model mixin: optimise every ImageField listed in IMAGE_FIELDS on save."""

    IMAGE_FIELDS = ()
    IMAGE_MAX_WIDTH = MAX_WIDTH

    def save(self, *args, **kwargs):
        for name in self.IMAGE_FIELDS:
            optimise(getattr(self, name), self.IMAGE_MAX_WIDTH)
        super().save(*args, **kwargs)
