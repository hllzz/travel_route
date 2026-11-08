from typing import Any, Optional
from planner.Agent.Utils.json_utils import dump_json


def build_intent_messages(city: str, budget: str, travel_time: str, preferences: str) -> list[dict[str, str]]:
    """
    功能说明：构造DeepSeek识别路线规划意图的消息
    """
    system_prompt = (
        '你是一个旅游路线规划意图识别助手。'
        '请只输出一个Json对象，不要输出Markdown。'
        'Json字段的包括：city, budget, travel_time, days, preference_tags, pace, intent_summary。'
    )
    user_prompt = (
        f'目的地城市：{city}\n'
        f'预算：{budget}\n'
        f'出行时间：{travel_time}\n'
        f'旅行偏好：{preferences}\n'
        '请识别用户适合的旅行天数、标签偏好和旅行节奏'
    )
    return [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt},
    ]


def build_final_messages(city: str,
                         budget: str,
                         travel_time: str,
                         preferences: str,
                         intent: dict[str, Any],
                         route_stops: list[dict[str, Any]],
                         validation_result: Optional[dict[str, Any]] = None
                         ) -> list[dict[str, str]]:
    """
    功能说明：构造DeepSeek生成最终路线说明的消息
    """
    system_prompt = (
        '你是专业旅游路线规划助手。'
        '请基于已选景点生成中文路线说明，包含每日安排、游览顺序、预算建议和偏好匹配理由'
        '不要输出代码块'
    )
    user_prompt = (
        f'目的地城市：{city}\n'
        f'预算：{budget}\n'
        f'出行时间：{travel_time}\n'
        f'旅行偏好：{preferences}\n'
        f'识别意图：{dump_json(intent)}\n'
        f'路线检查结果：{dump_json(validation_result or {})}\n'
        f'路线站点：{dump_json(route_stops)}\n'
        '请输出自然、清晰、适合页面展示的路线规划'
    )
    return [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt},
    ]
