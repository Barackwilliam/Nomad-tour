import json
from urllib.parse import quote

from django import template
from django.templatetags.static import static
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def money(value):
    if value in (None, ""):
        return ""
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return value


@register.simple_tag
def img(image, fallback="tours/img/placeholder.webp"):
    """URL of an uploaded image, or a bundled fallback photo."""
    try:
        if image:
            return image.url
    except ValueError:
        pass
    return static(fallback)


def _srcset(image):
    """'url-w480 480w, url-w960 960w, url 1600w' for an ImageField file, or ''."""
    from ..images import variant_name

    try:
        if not image or not image.name:
            return ""
        instance, field = image.instance, image.field.name
        widths = (getattr(instance, "image_widths", None) or {}).get(field) or []
        if len(widths) < 2:
            return ""
        *copies, original = widths
        storage = image.storage
        parts = [f"{storage.url(variant_name(image.name, w))} {w}w" for w in copies]
        parts.append(f"{image.url} {original}w")
        return ", ".join(parts)
    except (ValueError, AttributeError):
        return ""


@register.simple_tag
def srcset(image):
    return _srcset(image)


@register.simple_tag
def picture(image, alt="", sizes="100vw", cls="", loading="lazy", width=1200, height=800,
            fallback="tours/img/placeholder.webp", priority=False):
    """Responsive <img>: small copies for phones, full size for big screens."""
    src = img(image, fallback)
    set_ = _srcset(image)
    attrs = [
        format_html('src="{}"', src),
        format_html('srcset="{}" sizes="{}"', set_, sizes) if set_ else "",
        format_html('alt="{}"', alt),
        format_html('class="{}"', cls) if cls else "",
        format_html('width="{}" height="{}"', width, height),
        mark_safe('fetchpriority="high" decoding="async"') if priority else format_html('loading="{}" decoding="async"', loading),
    ]
    return mark_safe("<img " + " ".join(a for a in attrs if a) + ">")


@register.simple_tag(takes_context=True)
def wa(context, text=""):
    site = context.get("site")
    number = site.whatsapp if site else ""
    return f"https://wa.me/{number}" + (f"?text={quote(text)}" if text else "")


@register.filter
def rich(text):
    """Render simple admin text: '## Heading', '- bullet', blank-line paragraphs."""
    html, bullets = [], []

    def flush():
        if bullets:
            html.append("<ul>" + "".join(f"<li>{escape(b)}</li>" for b in bullets) + "</ul>")
            bullets.clear()

    for block in (text or "").replace("\r\n", "\n").split("\n\n"):
        for line in block.split("\n"):
            s = line.strip()
            if not s:
                continue
            if s.startswith("### "):
                flush()
                html.append(f"<h3>{escape(s[4:])}</h3>")
            elif s.startswith("## "):
                flush()
                html.append(f"<h2>{escape(s[3:])}</h2>")
            elif s.startswith(("- ", "* ", "• ")):
                bullets.append(s[2:])
            else:
                flush()
                html.append(f"<p>{escape(s)}</p>")
        flush()
    return mark_safe("\n".join(html))


@register.filter
def cat_icon(category):
    """Icon id for a category in the sidebar menu."""
    slug = getattr(category, "slug", "") or ""
    for key, icon in (("kilimanjaro-and", "route"), ("kilimanjaro", "mountain"), ("safari", "paw"),
                      ("zanzibar", "wave"), ("beach", "wave"), ("day", "sun"), ("trek", "flag")):
        if key in slug:
            return icon
    return "compass"


@register.filter
def accent(text, word):
    """Wrap the first occurrence of `word` in <em> for an elegant italic accent in headings."""
    text = str(text or "")
    i = text.find(word) if word else -1
    if i < 0:
        return text
    return format_html("{}<em>{}</em>{}", text[:i], text[i:i + len(word)], text[i + len(word):])


@register.filter
def json_ld(data):
    """Embed structured data for Google (escapes '<' so it can't close the script tag)."""
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    return format_html('<script type="application/ld+json">{}</script>', mark_safe(payload))


@register.filter
def get_item(d, key):
    return d.get(key) if hasattr(d, "get") else None
