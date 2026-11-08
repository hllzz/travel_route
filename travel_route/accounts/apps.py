from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """功能说明：配置账号应用基础信息。"""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = '账号管理'
