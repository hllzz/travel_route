import json
from typing import Optional

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from planner.models import RoutePlan
from planner.services import (
    clean_planner_form,
    create_route_plan,
    get_recent_plans,
    get_user_plan,
    serialize_route_stops,
    stream_route_plan_events,
)


@login_required
def planner_view(request: HttpRequest) -> HttpResponse:
    """功能说明：展示 AI 路线规划页面并处理规划提交。"""
    # 未登录用户由 login_required 重定向到登录页。
    # GET 请求展示空表单和最近的规划记录。
    if request.method != 'POST':
        return render_planner_page(request)

    # POST 请求清洗和校验表单数据。
    # 校验失败不直接提交，而是带着已填数据和错误信息重新渲染页面回显。
    cleaned_data, errors = clean_planner_form(request.POST)
    if errors:
        return render_planner_page(request, form_data=cleaned_data, errors=errors)

    # 创建规划记录并跳转到结果详情页。
    # 同步模式：create_route_plan 内部会阻塞跑完整个 Agent，成功失败都重定向到详情页展示。
    plan = create_route_plan(request.user, cleaned_data)
    return redirect('planner:route_plan_detail', plan_id=plan.id)


@login_required
def route_plan_detail_view(request: HttpRequest, plan_id: int) -> HttpResponse:
    """功能说明：展示当前用户的 AI 路线规划结果。"""
    # 查询当前用户自己的规划结果。
    plan = get_user_plan(request.user, plan_id)
    return render_planner_page(request, plan=plan)


@login_required
@require_POST
def stream_route_plan_view(request: HttpRequest) -> StreamingHttpResponse:
    """功能说明：以 SSE 流式返回 AI 路线规划过程和结果。"""
    # 先校验表单，校验失败也用 SSE 事件返回，便于前端统一处理。
    # 不用普通 JSON 而用 SSE：前端监听逻辑只写一套，错误也走事件通道。
    cleaned_data, errors = clean_planner_form(request.POST)
    if errors:
        response = StreamingHttpResponse(
            [_format_sse('validation_error', {'errors': errors})],
            content_type='text/event-stream; charset=utf-8',
        )
        # 错误短流同样禁用缓存，避免被代理缓存后其他用户看到别人的校验错误。
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    # 返回流式响应，逐步推送 LangGraph 执行过程。
    response = StreamingHttpResponse(
        _build_sse_stream(request.user, cleaned_data),
        content_type='text/event-stream; charset=utf-8',
    )
    # 禁用代理缓存并关闭 Nginx 缓冲，保证 SSE 事件能实时逐条到达浏览器。
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def _build_form_data_from_plan(plan: Optional[RoutePlan]) -> dict[str, str]:
    """功能说明：根据已有规划记录生成页面表单回显数据。"""
    # 无记录时返回空字典结构，模板无需做 None 判断。
    if plan is None:
        return {"city": "", "budget": "", "travel_time": "", "preferences": ""}
    # 查看历史规划时用记录字段回填表单，保持用户输入可见。
    return {"city": plan.city, "budget": plan.budget, "travel_time": plan.travel_time, "preferences": plan.preferences}

def render_planner_page(
    request: HttpRequest,
    form_data: Optional[dict[str, str]] = None,
    errors: Optional[list[str]] = None,
    plan: Optional[RoutePlan] = None,
) -> HttpResponse:
    """功能说明：渲染 AI 路线规划页面的通用模板。"""
    # 整理模板所需的表单、历史记录和地图数据。
    # 表单数据优先级：提交回显 > 规划记录回填 > 空表单；map_stops 只在带结果记录时序列化。
    context = {
        'form_data': form_data or _build_form_data_from_plan(plan),
        'errors': errors or [],
        'plan': plan,
        'recent_plans': get_recent_plans(request.user),
        'map_stops': serialize_route_stops(plan) if plan else [],
        'gaode_map_ak': settings.GAODE_MAP_AK,
    }
    return render(request, 'planner/route_planner.html', context)


def _build_sse_stream(user: object, cleaned_data: dict[str, str]):
    """功能说明：生成 AI 路线规划 SSE 文本流。"""
    # 转换服务层事件为标准 SSE 文本。
    # 生成器惰求值：StreamingHttpResponse 边消费边推送，视图返回时 Agent 才刚开始跑。
    for event_payload in stream_route_plan_events(user, cleaned_data):
        yield _format_sse(
            event_payload.get('event', 'message'),
            event_payload.get('data', {}),
        )


def _format_sse(event_name: str, data: dict) -> str:
    """功能说明：将事件名称和数据转换为 SSE 协议文本。"""
    # 使用 ensure_ascii=False，确保中文过程可以直接在浏览器中显示。
    # 双换行结尾是 SSE 协议的消息分隔符，缺失会导致事件不触发。
    payload = json.dumps(data, ensure_ascii=False)
    return f'event: {event_name}\ndata: {payload}\n\n'
