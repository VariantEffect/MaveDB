from import_export import resources
from tracking.models import Pageview, Visitor

from django.contrib import admin
from reversion.models import Version

from . import models

# Register with admin
admin.site.register(models.FailedTask)
admin.site.register(Version)


# Define import-export CSV resources
class PageviewResource(resources.ModelResource):
    class Meta:
        model = Pageview
        fields = (
            "id",
            "visitor",
            "visitor__ip_address",
            "url",
            "referer",
            "query_string",
            "method",
            "view_time",
        )
        export_order = (
            "id",
            "visitor",
            "visitor__ip_address",
            "url",
            "referer",
            "query_string",
            "method",
            "view_time",
        )


class VisitorResource(resources.ModelResource):
    class Meta:
        model = Visitor
        fields = (
            "user",
            "user__id",
            "user__username",
            "session_key",
            "ip_address",
            "user_agent",
            "start_time",
            "expiry_age",
            "expiry_time",
            "time_on_site",
            "end_time",
        )
        export_order = (
            "user",
            "user__id",
            "user__username",
            "session_key",
            "ip_address",
            "user_agent",
            "start_time",
            "expiry_age",
            "expiry_time",
            "time_on_site",
            "end_time",
        )
