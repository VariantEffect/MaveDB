import os
import sys
import json

from main.models import Licence

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        path = os.path.join(settings.MAIN_DIR, "licences.json")
        with open(path, "rt") as fp:
            data = json.load(fp)

        for licence_params in data["licences"]:
            legal = licence_params["legal_code"]
            created = (
                Licence.objects.filter(
                    short_name=licence_params["short_name"]
                ).count()
                == 0
            )
            licence = Licence.create_licence(
                short_name=licence_params["short_name"],
                long_name=licence_params["long_name"],
                link=licence_params["link"],
                file_name=legal["value"] if legal["file"] else None,
                legal_code=legal["value"]
                if not legal["file"]
                else "UNDEFINED",
                version=licence_params["version"],
            )
            sys.stdout.write(
                "{} '{}' with fields:\n{}\n\n".format(
                    "Created" if created else "Updated",
                    licence.short_name,
                    json.dumps(
                        {
                            "short_name": licence.short_name,
                            "long_name": licence.long_name,
                            "legal_code": "{}({} chars trunc)".format(
                                licence.legal_code[0:100],
                                max(0, len(licence.legal_code) - 100),
                            ),
                            "link": licence.link,
                            "version": licence.version,
                        },
                        indent=2,
                    ),
                )
            )
