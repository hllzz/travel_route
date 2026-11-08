"""功能说明：用户账号后台管理配置。"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.html import format_html

from accounts.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """功能说明：在 Django 后台管理自定义用户。"""

    fieldsets = DjangoUserAdmin.fieldsets + (
        ('头像信息', {'fields': ('avatar_preview', 'avatar')}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ('头像信息', {'fields': ('avatar',)}),
    )
    list_display = ('avatar_preview', 'username', 'email', 'is_staff', 'is_superuser', 'is_active', 'date_joined')
    list_display_links = ('avatar_preview', 'username')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    readonly_fields = ('avatar_preview', 'last_login', 'date_joined')
    ordering = ('-date_joined', 'username')
    list_per_page = 20
    save_on_top = True

    @admin.display(description='头像')
    def avatar_preview(self, obj: User) -> str:
        """功能说明：在后台列表和详情页展示用户头像缩略图。"""
        # 已上传头像时展示图片缩略图。
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width:32px;height:32px;border-radius:50%;object-fit:cover;" />',
                obj.avatar.url,
            )

        # 未上传头像时展示用户名首字母占位。
        first_char = (obj.username or 'U')[:1].upper()
        return format_html(
            '<span style="display:inline-flex;width:32px;height:32px;border-radius:50%;'
            'align-items:center;justify-content:center;background:#1f8f6a;color:#fff;font-weight:700;">{}</span>',
            first_char,
        )
