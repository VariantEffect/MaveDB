from django.contrib import admin
# from markdownx.admin import MarkdownxModelAdmin

from .models import News, SiteInformation

admin.site.register(News)
admin.site.register(SiteInformation)
# admin.site.register(SiteInformation, MarkdownxModelAdmin)
