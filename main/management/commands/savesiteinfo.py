import os
import sys
import json

from django.conf import settings

from main.serializers import SiteInformationSerializer
from main.models import SiteInformation

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        path = os.path.join(settings.MAIN_DIR, "site_info.json")
        with open(path, "wt") as fp:
            instance = SiteInformation.get_instance()
            if instance:
                data = SiteInformationSerializer(instance).data
                json.dump(data, fp, indent=4, sort_keys=True)
        sys.stdout.write("Site information saved to 'data/site_info.json'.\n")
