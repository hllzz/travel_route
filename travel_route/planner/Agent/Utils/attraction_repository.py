from typing import Any

from django.db.models import Q

from planner.Agent.Utils.route_utils import parse_budget_amount, rank_candidate_dicts, split_preferences
from travel.models import Attraction


def find_candidate_attractions(city: str, preferences: str, budget: str, limit: int = 16) -> list[dict[str, Any]]:
    """功能说明：根据城市、偏好和预算查询候选景点。"""
    # 先限定城市和非广告景点，保证规划结果来自用户目的地。
    queryset = Attraction.objects.filter(city_name__icontains=city, is_advertisement=False)

    # 根据偏好关键词尝试收窄候选范围。
    preference_query = Q()
    for keyword in split_preferences(preferences):
        preference_query |= Q(name__icontains=keyword) | Q(tags__icontains=keyword) | Q(area__icontains=keyword)
    if preference_query:
        preferred_queryset = queryset.filter(preference_query)
        if preferred_queryset.count() >= 4:
            queryset = preferred_queryset

    # 低预算或免费诉求优先从免费景点中取候选。
    budget_amount = parse_budget_amount(budget)
    if '免费' in budget or '低预算' in budget or budget_amount == 0:
        free_queryset = queryset.filter(is_free=True)
        if free_queryset.exists():
            queryset = free_queryset

    # 查询更多候选后交给排序工具综合打分。
    raw_candidates = queryset.order_by('-heat_score', '-score', '-comment_count', 'id')[: max(limit * 3, limit)]
    candidates = [_serialize_attraction(attraction) for attraction in raw_candidates]
    return rank_candidate_dicts(candidates, preferences, budget)[:limit]


def _serialize_attraction(attraction: Attraction) -> dict[str, Any]:
    """功能说明：将景点模型转换为 Agent 工具使用的字典。"""
    # 提取路线规划和地图展示需要的最小字段。
    return {
        'id': attraction.id,
        'poi_id': attraction.poi_id,
        'name': attraction.name,
        'area': attraction.area or '',
        'city_name': attraction.city_name,
        'comment_count': attraction.comment_count or 0,
        'score': attraction.score or 0,
        'image': attraction.image or '',
        'tags': attraction.tags or '',
        'market_price': attraction.market_price or 0,
        'preferential_price': attraction.preferential_price or 0,
        'actual_price': attraction.actual_price,
        'is_free': attraction.is_free,
        'longitude': attraction.longitude,
        'latitude': attraction.latitude,
        'heat_score': attraction.heat_score or 0,
    }
