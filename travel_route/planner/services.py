"""功能说明：AI 路线规划助手业务服务。"""
from collections.abc import Iterator
from typing import Any

from django.db import transaction
from django.db.models import Prefetch, QuerySet
from django.shortcuts import get_object_or_404

from planner.models import RoutePlan, RoutePlanStop


def clean_planner_form(post_data: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    """功能说明：清洗并校验路线规划页面提交的数据。"""
    # 读取表单字段并去除两端空白。
    cleaned_data = {
        'city': str(post_data.get('city', '')).strip(),
        'budget': str(post_data.get('budget', '')).strip(),
        'travel_time': str(post_data.get('travel_time', '')).strip(),
        'preferences': str(post_data.get('preferences', '')).strip(),
    }

    # 按页面必填项生成错误信息。
    # 错误收集到列表一次性返回，便于页面统一展示而非逐项中断。
    errors = []
    if not cleaned_data['city']:
        errors.append('请输入目的地城市。')
    if not cleaned_data['budget']:
        errors.append('请输入旅行预算。')
    if not cleaned_data['travel_time']:
        errors.append('请输入出行时间。')
    if not cleaned_data['preferences']:
        errors.append('请输入旅行偏好。')

    # 控制用户输入长度，避免保存异常长文本。
    # 长度上限与 RoutePlan 模型各字段的 max_length 保持一致。
    if len(cleaned_data['city']) > 50:
        errors.append('目的地城市不能超过 50 个字符。')
    if len(cleaned_data['budget']) > 80:
        errors.append('旅行预算不能超过 80 个字符。')
    if len(cleaned_data['travel_time']) > 80:
        errors.append('出行时间不能超过 80 个字符。')
    if len(cleaned_data['preferences']) > 300:
        errors.append('旅行偏好不能超过 300 个字符。')

    return cleaned_data, errors


def create_route_plan(user: Any, cleaned_data: dict[str, str]) -> RoutePlan:
    """功能说明：创建路线规划记录并调用 LangGraph 生成路线。"""
    # 先保存规划任务，保证失败信息也能在页面展示。
    plan = RoutePlan.objects.create(
        user=user,
        city=cleaned_data['city'],
        budget=cleaned_data['budget'],
        travel_time=cleaned_data['travel_time'],
        preferences=cleaned_data['preferences'],
    )

    # 调用 Agent 时延迟导入，避免未安装 LangGraph 时影响 Django 基础检查。
    try:
        from planner.Agent.graph import PlannerConfigError, run_route_planner
    except ImportError as exc:
        _mark_plan_failed(plan, f'AI 规划依赖未安装，请先安装 requirements.txt 中的 LangGraph 相关依赖。{exc}')
        return plan

    # 执行 LangGraph 并保存最终结果。
    # 配置类异常原样入库（提示可读），其余异常加统一前缀，都标记失败后返回。
    try:
        graph_result = run_route_planner(
            city=plan.city,
            budget=plan.budget,
            travel_time=plan.travel_time,
            preferences=plan.preferences,
        )
    except PlannerConfigError as exc:
        _mark_plan_failed(plan, str(exc))
        return plan
    except Exception as exc:  # noqa: BLE001
        _mark_plan_failed(plan, f'AI 路线规划失败：{exc}')
        return plan

    # 保存规划结果和站点。
    # 成功才进入落库；失败分支已在上面提前 return。
    save_route_plan_result(plan, graph_result)

    return plan


def stream_route_plan_events(user: Any, cleaned_data: dict[str, str]) -> Iterator[dict[str, Any]]:
    """功能说明：流式创建路线规划并逐步返回页面展示事件。"""
    # 创建规划记录，便于失败时也能保留错误状态。
    plan = RoutePlan.objects.create(
        user=user,
        city=cleaned_data['city'],
        budget=cleaned_data['budget'],
        travel_time=cleaned_data['travel_time'],
        preferences=cleaned_data['preferences'],
    )
    # 第一时间推送 plan_id，前端可据此展示“规划中”状态并支持中途关联记录。
    yield {'event': 'started', 'data': {'plan_id': plan.id}}

    # 延迟导入 Agent，避免缺少依赖时影响普通页面访问。
    try:
        from planner.Agent.graph import PlannerConfigError, stream_route_planner
    except ImportError as exc:
        # 失败写入库后，再用 SSE 错误事件把原因同步推给前端。
        _mark_plan_failed(plan, f'AI 规划依赖未安装，请先安装 requirements.txt 中的 LangGraph 相关依赖。{exc}')
        yield {'event': 'error', 'data': {'message': plan.error_message, 'plan_id': plan.id}}
        return

    # 转发 Agent 流式事件，拿到最终结果后写入数据库。
    try:
        graph_result = {}
        # 遍历 Agent 事件：中间事件原样转发给前端，graph_done 事件只截获数据不推送。
        for event_payload in stream_route_planner(
            city=plan.city,
            budget=plan.budget,
            travel_time=plan.travel_time,
            preferences=plan.preferences,
        ):
            if event_payload.get('event') == 'graph_done':
                # 完成事件仅用于收集落库数据，跳过避免重复推送给前端。
                graph_result = event_payload.get('data', {})
                continue
            yield event_payload
        save_route_plan_result(plan, graph_result)
    except PlannerConfigError as exc:
        _mark_plan_failed(plan, str(exc))
        yield {'event': 'error', 'data': {'message': plan.error_message, 'plan_id': plan.id}}
        return
    except Exception as exc:  # noqa: BLE001
        _mark_plan_failed(plan, f'AI 路线规划失败：{exc}')
        yield {'event': 'error', 'data': {'message': plan.error_message, 'plan_id': plan.id}}
        return

    # 返回保存后的最终数据，前端据此更新地图和详情链接。
    # done 事件携带落库后的状态，保证前端展示与数据库一致（含站点图片等关联字段）。
    yield {
        'event': 'done',
        'data': {
            'plan_id': plan.id,
            'status': plan.status,
            'final_plan': plan.final_plan,
            'process_steps': plan.process_steps,
            'map_stops': serialize_route_stops(plan),
        },
    }


def save_route_plan_result(plan: RoutePlan, graph_result: dict[str, Any]) -> None:
    """功能说明：保存 LangGraph 生成的路线规划结果。"""
    # 使用事务保存规划结果和站点，避免站点写入一半。
    with transaction.atomic():
        plan.intent_data = graph_result.get('intent', {})
        plan.process_steps = graph_result.get('process_steps', [])
        plan.final_plan = graph_result.get('final_plan', '')
        plan.status = RoutePlan.STATUS_SUCCESS
        plan.error_message = ''
        plan.save(update_fields=['intent_data', 'process_steps', 'final_plan', 'status', 'error_message'])
        _replace_plan_stops(plan, graph_result.get('route_stops', []))


def get_user_plan(user: Any, plan_id: int) -> RoutePlan:
    """功能说明：查询当前用户有权限查看的路线规划记录。"""
    # 限定用户范围，避免用户访问他人的规划结果。
    # 预加载链：select_related 一次 JOIN 取回用户；Prefetch+select_related 把站点及关联景点一次取完，防序列化时 N+1。
    return get_object_or_404(
        RoutePlan.objects.prefetch_related(
            Prefetch('stops', queryset=RoutePlanStop.objects.select_related('attraction'))
        ).select_related('user'),
        pk=plan_id,
        user=user,
    )


def get_recent_plans(user: Any, limit: int = 5) -> QuerySet[RoutePlan]:
    """功能说明：查询当前用户最近生成的路线规划记录。"""
    # 返回最近的少量历史记录，用于规划页面快捷查看。
    return RoutePlan.objects.filter(user=user).order_by('-created_at')[:limit]


def serialize_route_stops(plan: RoutePlan) -> list[dict[str, Any]]:
    """功能说明：将路线站点序列化为前端地图可直接使用的数据。"""
    # 按模型默认排序生成地图点位数据。
    # 排序由 Meta.ordering（day_index, sequence）保证，前端无需再排；字段名与 route_map.js 约定对齐。
    return [
        {
            'day_index': stop.day_index,
            'sequence': stop.sequence,
            'name': stop.name,
            'city_name': stop.city_name,
            'longitude': stop.longitude,
            'latitude': stop.latitude,
            'image': _get_stop_image(stop),
            'intro': stop.intro,
        }
        for stop in plan.stops.all()
    ]


def _get_stop_image(stop: RoutePlanStop) -> str:
    """功能说明：获取路线站点关联景点的图片地址。"""
    # 优先读取关联景点图片，历史路线无需额外保存冗余图片字段。
    if stop.attraction and stop.attraction.image:
        return stop.attraction.image
    return ''


def _mark_plan_failed(plan: RoutePlan, error_message: str) -> None:
    """功能说明：将路线规划记录标记为失败状态。"""
    # 写入可展示的失败原因和规划过程。
    plan.status = RoutePlan.STATUS_FAILED
    plan.error_message = error_message[:300]
    plan.process_steps = [
        {'title': '规划失败', 'description': plan.error_message, 'status': 'failed'},
    ]
    plan.save(update_fields=['status', 'error_message', 'process_steps'])


def _replace_plan_stops(plan: RoutePlan, route_stops: list[dict[str, Any]]) -> None:
    """功能说明：用新的路线站点替换规划记录下的旧站点。"""
    # 删除旧站点，保证重复生成时数据不会叠加。
    plan.stops.all().delete()

    # 批量创建站点，减少数据库写入次数。
    # 逐字段兜底默认值：Agent 产出的字典可能缺键，而模型字段非空，缺失时用遍历序号/plan 城市补号。
    stop_objects = []
    for index, stop in enumerate(route_stops, start=1):
        # 跳过缺少有效坐标的站点，避免地图无法正常标点。
        longitude = float(stop.get('longitude') or 0)
        latitude = float(stop.get('latitude') or 0)
        if not longitude or not latitude:
            continue
        stop_objects.append(
            RoutePlanStop(
                plan=plan,
                attraction_id=stop.get('attraction_id'),
                day_index=int(stop.get('day_index') or 1),
                sequence=int(stop.get('sequence') or index),
                name=str(stop.get('name') or ''),
                city_name=str(stop.get('city_name') or plan.city),
                longitude=longitude,
                latitude=latitude,
                intro=str(stop.get('intro') or ''),
            )
        )
    # 一次性批量插入，只触发一条 INSERT 语句；在调用方的事务内执行，失败整体回滚。
    RoutePlanStop.objects.bulk_create(stop_objects)
