import os
import io
import tarfile

from django.http import HttpResponse

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated

from .admin import PageviewResource, VisitorResource


@api_view(http_method_names=("get",))
@permission_classes(permission_classes=(IsAdminUser, IsAuthenticated))
def get_pageview_stats(request):
    response = HttpResponse(content_type="application/x-gzip", status=200)
    response[
        "Content-Disposition"
    ] = "attachment; filename=mavedb_stats.tar.gz"
    tarball = tarfile.open(fileobj=response, mode="w:gz")

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

    return response
