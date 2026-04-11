"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.views.static import serve

urlpatterns = [
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
    path('admin/', admin.site.urls),
    path('', include('accounts.urls', namespace='accounts')),
    path('dashboard/video-ai/', include('video_ai.urls', namespace='video_ai')),
    path('admin-panel/', include('admin_panel.urls', namespace='admin_panel')),
    path('', include('google_auth.urls', namespace='google_auth')),
    path('', include('aivideo_component.urls', namespace='aivideo_component')),
    path('', include('jobs.urls', namespace='jobs')),
    # DEBUG=False（staging）でも media ファイルを配信する
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
