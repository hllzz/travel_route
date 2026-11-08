"""功能说明：AI 路线规划 LangGraph 工具。"""
from langchain_core.tools import tool

from planner.Agent.Utils.attraction_repository import find_candidate_attractions
from planner.Agent.Utils.json_utils import dump_json, extract_json_object, load_json_dict
from planner.Agent.Utils.llm import call_deepseek_chat
from planner.Agent.Utils.prompt_utils import build_intent_messages
from planner.Agent.Utils.route_utils import build_route_stops, validate_route_plan_quality


@tool
def parse_travel_intent(city: str, budget: str, travel_time: str, preferences: str) -> str:
    """功能说明：调用大模型识别用户旅游路线规划意图。"""
    # 构造意图识别提示词并调用 DeepSeek，要求模型返回结构化 JSON。
    messages = build_intent_messages(
        city=city,
        budget=budget,
        travel_time=travel_time,
        preferences=preferences,
    )
    content = call_deepseek_chat(messages)

    # 从模型输出中提取 JSON，避免模型附加说明文字影响工具链。
    intent = extract_json_object(content)
    return dump_json(intent)


@tool
def search_attractions(city: str, preferences: str, budget: str, limit: int = 16) -> str:
    """功能说明：根据城市、旅行偏好和预算检索可用于路线规划的候选景点。"""
    # 查询候选景点并返回 JSON 字符串，供 ToolNode 写入工具消息。
    attractions = find_candidate_attractions(city=city, preferences=preferences, budget=budget, limit=limit)
    return dump_json({'attractions': attractions, 'count': len(attractions)})


@tool
def build_route_candidates(attractions_json: str, travel_time: str, budget: str, preferences: str) -> str:
    """功能说明：根据候选景点、出行时间、预算和偏好生成有顺序的路线站点。"""
    # 解析上一步工具返回的候选景点。
    payload = load_json_dict(attractions_json)
    attractions = payload.get('attractions', [])
    if not isinstance(attractions, list):
        attractions = []

    # 构建按天和顺序排列的路线站点。
    route_stops = build_route_stops(
        candidates=attractions,
        travel_time=travel_time,
        budget=budget,
        preferences=preferences,
    )
    return dump_json({'route_stops': route_stops, 'count': len(route_stops)})


@tool
def validate_route_plan(route_stops_json: str, travel_time: str, budget: str, preferences: str) -> str:
    """功能说明：检查路线是否符合用户要求，并评估是否存在明显来回折返。"""
    # 解析路线站点数据，兼容工具链传入的 JSON 字符串。
    payload = load_json_dict(route_stops_json)
    route_stops = payload.get('route_stops', [])
    if not isinstance(route_stops, list):
        route_stops = []

    # 执行路线质量检查并返回结构化结果。
    validation_result = validate_route_plan_quality(
        route_stops=route_stops,
        travel_time=travel_time,
        budget=budget,
        preferences=preferences,
    )
    return dump_json(validation_result)


def get_planner_tools() -> list:
    """功能说明：返回 LangGraph ToolNode 需要注册的工具列表。"""
    # 集中注册工具，避免图构建时重复声明。
    return [parse_travel_intent, search_attractions, build_route_candidates, validate_route_plan]
