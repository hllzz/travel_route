"""功能说明：旅游规划系统根路由配置（基础架构版本）。"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


# 配置 Django 自带后台管理的站点标题。
admin.site.site_header = '旅游规划平台后台管理'
admin.site.site_title = '旅游规划后台'
admin.site.index_title = '后台数据管理'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('travel/', include('travel.urls')),
    path('guides/', include('guides.urls')),
    path('planner/', include('planner.urls')),
]

# 开发环境下开放用户头像上传文件访问。
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
