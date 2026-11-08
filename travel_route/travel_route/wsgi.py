"""功能说明：Django WSGI 服务入口。"""
import os

from django.core.wsgi import get_wsgi_application


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travel_route.settings')

application = get_wsgi_application()
