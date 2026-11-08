"""功能说明：Django ASGI 服务入口。"""
import os

from django.core.asgi import get_asgi_application


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travel_route.settings')

application = get_asgi_application()
