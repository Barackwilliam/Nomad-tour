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
def json_ld(data):
    """Embed structured data for Google (escapes '<' so it can't close the script tag)."""
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    return format_html('<script type="application/ld+json">{}</script>', mark_safe(payload))


@register.filter
def get_item(d, key):
    return d.get(key) if hasattr(d, "get") else None
