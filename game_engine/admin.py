from django.contrib import admin
from game_engine.models import Match, User, UserCode

# Register your models here.
admin.site.register(Match)
admin.site.register(User)
admin.site.register(UserCode)
