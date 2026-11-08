"""功能说明：景点应用路由配置（基础架构版本）。"""
from django.urls import path

from travel import views


app_name = 'travel'

urlpatterns = [
    path('attractions/', views.attraction_list_view, name='attraction_list'),
    path('attractions/<int:poi_id>/', views.attraction_detail_view, name='attraction_detail'),
    path('attractions/<int:poi_id>/favorite', views.toggle_favorite_view, name='toggle_favorite'),
    path('attractions/<int:poi_id>/comments', views.add_comment_view, name='add_comment')
]