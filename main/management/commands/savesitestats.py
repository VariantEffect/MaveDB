import os
import sys
import json

from django.conf import settings

from main.serializers import SiteInformationSerializer
from main.models import SiteInformation

from django.core.management.base import BaseCommand

import os
import io
import tarfile

from core.admin import PageviewResource, VisitorResource


def get_pageview_stats(path):
    tarball = tarfile.open(name=path, mode="w:gz")

    pageview_file = io.BytesIO()
    pageview_file.write(PageviewResource().export().csv.encode("utf-8"))
    pageview_file.seek(0, os.SEEK_END)
    pageview_info = tarfile.TarInfo(name="pageviews.csv")
    pageview_info.size = pageview_file.tell()
    pageview_file.seek(0)

    visitor_file = io.BytesIO()
    visitor_file.write(VisitorResource().export().csv.encode("utf-8"))
    visitor_file.seek(0, os.SEEK_END)
    visitor_info = tarfile.TarInfo(name="visitors.csv")
    visitor_info.size = visitor_file.tell()
    visitor_file.seek(0)

    tarball.addfile(tarinfo=pageview_info, fileobj=pageview_file)
    tarball.addfile(tarinfo=visitor_info, fileobj=visitor_file)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--path", type=str, help="Path to save tarball to."
        )

    def handle(self, *args, **kwargs):
        path = os.path.join(os.path.abspath(kwargs["path"]), "stats.tar.gz")
        get_pageview_stats(path)
        sys.stdout.write("Site information saved to '{}'.\n".format(path))
