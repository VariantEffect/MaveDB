import os
import sys
import json

from django.conf import settings
from django.db import transaction

from main.models import SiteInformation

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    @transaction.atomic
    def handle(self, *args, **kwargs):
        path = os.path.join(settings.MAIN_DIR, "site_info.json")
        with open(path, "rt") as fp:
            info = json.load(fp)
            instance = SiteInformation.get_instance()
            for field, value in info.items():
                sys.stdout.write("Setting field '{}'\n".format(field))
                file_path = os.path.join(settings.MAIN_DIR, value)
                if os.path.isfile(file_path):
                    with open(file_path, "rt") as fp:
                        sys.stdout.write(
                            "\tReading from file %s\n" % file_path
                        )
                        value = fp.read()
                setattr(instance, field, value)
            instance.save()
        sys.stdout.write("Updated from 'data/site_info.json'\n")
