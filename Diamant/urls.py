"""Diamant URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from game_engine import views

from django.conf import settings
from django.conf.urls.static import static

router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'user_performances', views.UserPerformanceViewSet)
router.register(r'matches', views.MatchViewSet)
router.register(r'request_match', views.MatchProvider, basename="request_match")
router.register(r'code_list', views.UserCodeViewSet)
router.register(r'match_history', views.MatchResultViewSet)
router.register(r'settings', views.SettingsViewSet, basename=views.SettingsViewSet.basename)


urlpatterns = [
    path('', include(router.urls)),
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),
    path('oauth/', include('oauth.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
