from django.contrib import admin

from metadata.models import (
    Keyword, DoiIdentifier, PubmedIdentifier, SraIdentifier
)

# Register your models here.
admin.site.register(Keyword)
admin.site.register(PubmedIdentifier)
admin.site.register(DoiIdentifier)
admin.site.register(SraIdentifier)