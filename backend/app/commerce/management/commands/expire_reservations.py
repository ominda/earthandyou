from django.core.management.base import BaseCommand
from commerce.services import expire_stale_reservations


class Command(BaseCommand):
    help = "Expire stale reservations and release their inventory."

    def handle(self, *args, **options):
        count = expire_stale_reservations()
        if count:
            self.stdout.write(self.style.SUCCESS(f"Expired {count} reservation(s)."))
        else:
            self.stdout.write("No stale reservations found.")
