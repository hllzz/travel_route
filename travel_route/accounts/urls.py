"""功能说明：账号应用路由配置（基础架构版本）。"""
from django.urls import path

from accounts import views


app_name = 'accounts'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/favorites/<int:favorite_id>/remove', views.remove_favorite_view, name='remove_favorite'),
path('profile/favorites/', views.my_favorites_view, name='my_favorites'),
    path('profile/guides/', views.my_guides_view, name='my_guides'),
]
