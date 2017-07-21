from django.contrib import admin
# from markdownx.admin import MarkdownxModelAdmin

from .models import News, SiteInformation, Experiment, ScoreSet

admin.site.register(News)
admin.site.register(SiteInformation)
admin.site.register(Experiment)
admin.site.register(ScoreSet)
# admin.site.register(SiteInformation, MarkdownxModelAdmin)
