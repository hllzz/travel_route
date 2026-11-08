from django.contrib import admin

from guides.models import TravelGuide, TravelGuideAttraction, TravelGuideImage


@admin.register(TravelGuide)
class TravelGuideAdmin(admin.ModelAdmin):
    """功能说明：在 Django 后台管理旅游攻略。"""

    list_display = ('title', 'author', 'city', 'view_count', 'created_at')
    list_display_links = ('title',)
    list_filter = ('city', 'created_at')
    search_fields = ('title', 'author__username', 'city', 'summary', 'content')
    readonly_fields = ('view_count', 'created_at', 'updated_at')
    ordering = ('-created_at', '-id')
    list_per_page = 20
    save_on_top = True


@admin.register(TravelGuideImage)
class TravelGuideImageAdmin(admin.ModelAdmin):
    """功能说明：在 Django 后台管理攻略图片。"""

    list_display = ('guide', 'image_preview', 'sort_order', 'created_at')
    list_display_links = ('guide',)
    list_filter = ('created_at',)
    search_fields = ('guide__title',)
    ordering = ('guide', 'sort_order', 'id')
    list_per_page = 20

    @admin.display(description='图片')
    def image_preview(self, obj: TravelGuideImage) -> str:
        """功能说明：在后台列表展示图片缩略图。"""
        from django.utils.html import format_html
        if obj.image:
            return format_html(
                '<img src="{}" style="width:64px;height:64px;object-fit:cover;" />',
                obj.image.url,
            )
        return '无图片'


@admin.register(TravelGuideAttraction)
class TravelGuideAttractionAdmin(admin.ModelAdmin):
    """功能说明：在 Django 后台管理攻略关联景点。"""

    list_display = ('guide', 'attraction', 'created_at')
    list_display_links = ('guide', 'attraction')
    list_filter = ('created_at',)
    search_fields = ('guide__title', 'attraction__name')
    ordering = ('-created_at', '-id')
    list_per_page = 20
