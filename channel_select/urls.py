from django.urls import path
from . import views

app_name = 'channel_select'

urlpatterns = [
    path('', views.channel_list, name='channel_list'),
    path('<int:channel_id>/', views.channel_detail, name='channel_detail'),
]
