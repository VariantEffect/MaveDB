import reversion

from django.contrib import admin

from metadata.models import (
    Keyword, DoiIdentifier, PubmedIdentifier, SraIdentifier,
    ExternalIdentifier
)

# Register your models here.
# admin.site.register(Keyword)
# admin.site.register(PubmedIdentifier)
# admin.site.register(DoiIdentifier)
# admin.site.register(SraIdentifier)

reversion.register(Keyword, fields=Keyword.tracked_fields())
reversion.register(PubmedIdentifier, fields=ExternalIdentifier.tracked_fields())
reversion.register(DoiIdentifier, fields=ExternalIdentifier.tracked_fields())
reversion.register(SraIdentifier, fields=ExternalIdentifier.tracked_fields())

