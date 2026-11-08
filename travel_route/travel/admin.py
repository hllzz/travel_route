from django.contrib import admin

from travel.models import Attraction, AttractionComment, AttractionFavorite


@admin.register(Attraction)
class AttractionAdmin(admin.ModelAdmin):
    """功能说明：在 Django 后台管理旅游景点。"""

    list_display = ('name', 'city_name', 'area', 'score', 'is_free', 'heat_score')
    list_display_links = ('name',)
    list_filter = ('city_name', 'is_free', 'is_recommend', 'is_advertisement')
    search_fields = ('name', 'city_name', 'area', 'tags')
    readonly_fields = ('poi_id', 'longitude', 'latitude')
    ordering = ('-heat_score', '-score', '-comment_count', 'id')
    list_per_page = 20
    save_on_top = True


@admin.register(AttractionFavorite)
class AttractionFavoriteAdmin(admin.ModelAdmin):
    """功能说明：在 Django 后台管理景点收藏。"""

    list_display = ('user', 'attraction', 'created_at')
    list_display_links = ('user', 'attraction')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'attraction__name')
    ordering = ('-created_at', '-id')
    list_per_page = 20


@admin.register(AttractionComment)
class AttractionCommentAdmin(admin.ModelAdmin):
    """功能说明：在 Django 后台管理景点评论。"""

    list_display = ('user', 'attraction', 'content_preview',  'created_at')
    list_display_links = ('user', 'attraction')
    list_filter = ( 'created_at', )
    search_fields = ('user__username', 'attraction__name', 'content')
    ordering = ('-created_at', '-id')
    list_per_page = 20

    @admin.display(description='评论内容')
    def content_preview(self, obj: AttractionComment) -> str:
        """功能说明：在后台列表展示评论内容预览。"""
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
