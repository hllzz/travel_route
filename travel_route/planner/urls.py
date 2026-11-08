from django.urls import path
from . import views

app_name = 'planner'

urlpatterns = [
    path('', views.planner_view, name='planner'),
    path('plan/<int:plan_id>/', views.route_plan_detail_view, name='route_plan_detail'),
    path('stream/', views.stream_route_plan_view, name='stream_route_plan'),
]
