"""Sending email from the website.

Two ways, chosen by environment variables:

1. BREVO_API_KEY set  -> Brevo's HTTPS API (works on Render's free plan, which blocks SMTP ports).
2. EMAIL_HOST set     -> normal SMTP (e.g. the cPanel mailbox mail.nomadexplorertours.com).
3. neither            -> nothing leaves the server (Django console backend, printed to the log).

Sending happens in a background thread so a slow mail server never delays the visitor.
"""
import json
import logging
import threading
import urllib.error
import urllib.request

from django.conf import settings
from django.core.mail import EmailMessage

log = logging.getLogger("tours")

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def backend_name():
    if settings.BREVO_API_KEY:
        return "brevo"
    if settings.EMAIL_HOST:
        return "smtp"
    return "none"


def _send_brevo(subject, body, to, reply_to=None, from_email=None, from_name=None):
    payload = {
        "sender": {"email": from_email or settings.DEFAULT_FROM_EMAIL, "name": from_name or settings.EMAIL_FROM_NAME},
        "to": [{"email": addr} for addr in to],
        "subject": subject,
        "textContent": body,
    }
    if reply_to:
        payload["replyTo"] = {"email": reply_to}
    req = urllib.request.Request(
        BREVO_URL,
        data=json.dumps(payload).encode(),
        headers={"api-key": settings.BREVO_API_KEY, "content-type": "application/json", "accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return res.status
    except urllib.error.HTTPError as e:  # show Brevo's own explanation in the logs
        raise RuntimeError(f"Brevo error {e.code}: {e.read().decode(errors='replace')[:500]}") from None


def _send_django(subject, body, to, reply_to=None, from_email=None, from_name=None):
    sender = from_email or settings.DEFAULT_FROM_EMAIL
    if from_name:
        sender = f"{from_name} <{sender}>"
    EmailMessage(subject, body, sender, to, reply_to=[reply_to] if reply_to else None).send(fail_silently=False)


def send(subject, body, to, reply_to=None, raise_errors=False):
    """Send a plain-text email. Errors are logged (or raised when raise_errors=True)."""
    to = [addr for addr in to if addr]
    if not to:
        return False
    fn = _send_brevo if settings.BREVO_API_KEY else _send_django
    try:
        fn(subject, body, to, reply_to=reply_to)
        log.info("Email sent via %s to %s: %s", backend_name(), ", ".join(to), subject)
        return True
    except Exception:
        log.exception("Email via %s to %s failed", backend_name(), ", ".join(to))
        if raise_errors:
            raise
        return False


def send_async(*args, **kwargs):
    if not settings.EMAIL_ASYNC:
        return send(*args, **kwargs)
    threading.Thread(target=send, args=args, kwargs=kwargs, daemon=True).start()
    return True
