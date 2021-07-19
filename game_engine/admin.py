from django.contrib import admin
from game_engine.models import Match, User, UserCode, MatchResult, UserPerformance

# Register your models here.
admin.site.register(Match)
admin.site.register(MatchResult)
admin.site.register(User)
admin.site.register(UserCode)
admin.site.register(UserPerformance)
