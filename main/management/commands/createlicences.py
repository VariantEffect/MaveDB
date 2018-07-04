import sys
from main.models import Licence

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        l = Licence.get_cc0()
        sys.stdout.write("Created %s licence\n" % l.short_name)
        l = Licence.get_cc_by_nc_sa()
        sys.stdout.write("Created %s licence\n" % l.short_name)

