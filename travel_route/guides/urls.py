"""功能说明：攻略应用路由配置（基础架构版本）。"""
from django.urls import path

from guides import views
app_name = 'guides'

urlpatterns = [
    path('', views.guide_list_view, name='guide_list'),
    path('<int:guide_id>/', views.guide_detail_view, name='guide_detail'),
    path('create/', views.guide_create_view, name='guide_create'),
    path('attraction/search/', views.attraction_search_view, name='attraction_search'),
]