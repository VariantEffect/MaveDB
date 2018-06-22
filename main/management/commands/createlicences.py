from main.models import Licence

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        Licence.populate()

