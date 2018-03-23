from django.contrib import admin

from .models import News, SiteInformation, Licence

# Register with admin
admin.site.register(News)
admin.site.register(Licence)
admin.site.register(SiteInformation)





