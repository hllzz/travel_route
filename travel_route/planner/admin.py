from django.contrib import admin

from planner.models import RoutePlan, RoutePlanStop


@admin.register(RoutePlan)
class RoutePlanAdmin(admin.ModelAdmin):
    """功能说明：在 Django 后台管理 AI 路线规划。"""

    list_display = ('user', 'city', 'status', 'created_at')
    list_display_links = ('user', 'city')
    list_filter = ('status', 'city', 'created_at')
    search_fields = ('user__username', 'city', 'budget', 'preferences')
    readonly_fields = ('intent_data', 'process_steps', 'final_plan', 'created_at')
    ordering = ('-created_at', '-id')
    list_per_page = 20
    save_on_top = True


@admin.register(RoutePlanStop)
class RoutePlanStopAdmin(admin.ModelAdmin):
    """功能说明：在 Django 后台管理路线规划站点。"""

    list_display = ('plan', 'day_index', 'sequence', 'name', 'city_name')
    list_display_links = ('plan', 'name')
    list_filter = ('day_index', 'city_name')
    search_fields = ('plan__city', 'name', 'city_name')
    ordering = ('plan', 'day_index', 'sequence')
    list_per_page = 20
