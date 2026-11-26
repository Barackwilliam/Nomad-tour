from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from tours import mailer
from tours.models import SiteSettings


class Command(BaseCommand):
    help = "Send a test email and show exactly what goes wrong. Usage: python manage.py send_test_email [address]"

    def add_arguments(self, parser):
        parser.add_argument("to", nargs="?", help="Recipient (default: the enquiry notification address).")

    def handle(self, *args, **opts):
        to = opts["to"] or settings.ENQUIRY_NOTIFY_EMAIL or SiteSettings.get().email
        backend = mailer.backend_name()
        self.stdout.write(f"Method: {backend}   From: {settings.DEFAULT_FROM_EMAIL}   To: {to}")
        if backend == "none":
            raise CommandError("No email method configured: set BREVO_API_KEY (or EMAIL_HOST + password).")
        if backend == "smtp":
            self.stdout.write(
                f"SMTP {settings.EMAIL_HOST}:{settings.EMAIL_PORT} SSL={settings.EMAIL_USE_SSL} "
                f"TLS={settings.EMAIL_USE_TLS} user={settings.EMAIL_HOST_USER}"
            )
        try:
            mailer.send("Test email from your website", "If you can read this, website emails work.", [to], raise_errors=True)
        except Exception as e:
            raise CommandError(f"Sending failed: {e}")
        self.stdout.write(self.style.SUCCESS("Sent. Check the inbox (and the spam folder)."))
