from typing import TypedDict, Annotated, Any, Iterator

from langgraph.constants import START
from langgraph.graph import add_messages, StateGraph
from langchain_core.messages import AnyMessage, AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.prebuilt import ToolNode, tools_condition

from planner.Agent.Tools.attraction_tools import get_planner_tools
from planner.Agent.Utils.json_utils import load_json_dict
from planner.Agent.Utils.llm import PlannerConfigError,get_deepseek_chat_model
from planner.Agent.Utils.route_utils import parse_travel_days, split_preferences, sanitize_final_plan


class PlannerState(TypedDict):
    """功能说明：定义 AI 路线规划 LangGraph Agent 状态。"""
    # 对话历史：add_messages reducer 让各节点返回的新消息自动追加而非覆盖。
    messages: Annotated[list[AnyMessage], add_messages]
    # 用户输入的四个原始条件，作为工具参数和提示词拼装的兜底来源。
    city: str
    budget: str
    travel_time: str
    preferences: str
    # 以下四个字段是各工具的结构化产出，逐级填充后写入最终结果。
    intent: dict[str, Any]
    candidates: list[dict[str, Any]]
    route_stops: list[dict[str, Any]]
    validation_result: dict[str, Any]
    # 最终 Markdown 路线文本，Agent 无工具调用的那一轮回复清洗后写入。
    final_plan: str
    # 页面过程步骤列表，前端时间线据此逐步展示；已处理工具调用 ID 防重复同步。
    process_steps: list[dict[str, str]]
    processed_tool_call_ids: list[str]
def _build_initial_state(city: str, budget: str, travel_time: str, preferences: str) -> PlannerState:
    """功能说明：构建 LangGraph Agent 初始状态。"""
    # 只记录用户原始输入，结构化意图交给 LangGraph 工具调用生成。
    input_step = {
        'title': '输入接收',
        'description': f'已收到目的地 {city}、预算 {budget}、出行时间 {travel_time} 和旅行偏好。',
        'status': 'success',
    }

    # 初始消息只保存用户输入，系统提示在每次 Agent 节点调用时动态拼接。
    return {
        'messages': [
            HumanMessage(
                content=(
                    f'请为我规划旅游路线。\n'
                    f'目的地城市：{city}\n'
                    f'预算：{budget}\n'
                    f'出行时间：{travel_time}\n'
                    f'旅行偏好：{preferences}'
                )
            )
        ],
        'city': city,
        'budget': budget,
        'travel_time': travel_time,
        'preferences': preferences,
        # 四个结构化产出和最终文本全部置空，等待工具调用逐步填充。
        'intent': {},
        'candidates': [],
        'route_stops': [],
        'validation_result': {},
        'final_plan': '',
        'process_steps': [input_step],
        # 记录已同步过的工具调用 ID，sync 节点靠它实现幂等。
        'processed_tool_call_ids': [],
    }
def _build_agent_messages(state: PlannerState) -> list[AnyMessage]:
    """功能说明：构建 LLM Agent 节点的系统提示和历史消息。"""
    # 系统提示明确要求模型按标准工具调用循环自主决策。
    system_prompt = (
        '你是一个标准 LangGraph Tool-calling 旅游路线规划 Agent。\n'
        '你必须自主判断是否调用工具；不要让代码固定替你决定工具顺序。\n'
        '可用工具：\n'
        '1. parse_travel_intent：识别用户的目的地、预算、天数、偏好标签、旅行节奏和规划意图。\n'
        '2. search_attractions：根据城市、偏好和预算检索候选景点。\n'
        '3. build_route_candidates：根据候选景点生成路线站点和游览顺序。\n'
        '4. validate_route_plan：检查路线是否符合用户要求，并评估是否存在明显来回折返。\n'
        '执行约束：\n'
        '- 没有结构化意图时，必须先调用 parse_travel_intent。\n'
        '- 有结构化意图但没有候选景点时，必须调用 search_attractions。\n'
        '- 有候选景点但没有路线站点时，必须调用 build_route_candidates，并把 search_attractions 返回的完整 JSON 原样传入 attractions_json。\n'
        '- 有路线站点但没有检查结果时，必须调用 validate_route_plan，并把 build_route_candidates 返回的完整 JSON 原样传入 route_stops_json。\n'
        '- validate_route_plan 返回 optimized_route_stops 时，最终路线必须采用优化后的站点顺序。\n'
        '- 只有完成路线质量检查后，才能停止工具调用并输出最终中文路线规划。\n'
        '- 最终回答要包含每日顺序、站点介绍、偏好匹配理由、预算建议和路线检查结论。\n'
        '- 输出路线检查结论时保持原有的分点列表格式，只需用自然中文描述检查内容，不要使用反引号包裹的内部字段名或代码样式。\n'
        f"当前结构化输入：城市={state['city']}，预算={state['budget']}，"
        f"出行时间={state['travel_time']}，偏好={state['preferences']}。\n"
        f"当前意图识别结果：{state.get('intent') or '尚未识别'}。\n"
        f"当前状态：候选景点数量={len(state.get('candidates', []))}，"
        f"路线站点数量={len(state.get('route_stops', []))}，"
        f"是否已检查路线={bool(state.get('validation_result'))}。"
    )
    return [SystemMessage(content=system_prompt), *state.get('messages', [])]
def _build_agent_decision_step(response: AIMessage, state: PlannerState) -> dict[str, str]:
    """功能说明：根据LLM Agent 输出构建决策过程步骤"""

    # 本轮发起工具调用：生成 running 状态的“决策”步骤，列出模型选择的工具。
    tool_calls = getattr(response, 'tool_calls', []) or []
    if tool_calls:
        tool_names = [toolcall.get('name', 'unknown') for toolcall in tool_calls]

        return {
            'title': 'LLM Agent 决策',
            'description': f"模型自主决定调用工具：{'、'.join(tool_names)}",
            'status': 'running'
        }
    # 无工具调用即循环结束：有路线站点算成功，否则警告（模型未产出路线就提前结束）。
    status = 'success' if state.get('route_stops') else 'warning'
    return {
        'title': 'LLM Agent 完成',
        'description': '模型未再请求工具调用，标准Agent循环结束，并输出最终路线规划',
        'status': status
    }
def _message_has_tool_calls(message: AIMessage) -> bool:
    """功能说明：判断模型回复是否携带工具调用请求。"""
    # 兜底：早期消息对象可能没有 tool_calls 属性或为 None。
    return bool(getattr(message, 'tool_calls', []) or [])
def _message_content_to_text(message: AnyMessage) -> str:
    """功能说明：将 LangChain 消息内容统一转换为文本。"""
    # 普通字符串直接返回。
    content = getattr(message, 'content', '')
    if isinstance(content, str):
        return content

    # 兼容多模态或分段内容列表。
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                text_parts.append(str(item.get('text') or item.get('content') or ''))
            else:
                text_parts.append(str(item))
        return ''.join(text_parts)

    return str(content or '')
def _agent_node(state: PlannerState) -> dict[str, Any]:
    """功能说明：运行 LLM Agent 节点，由模型自主决定工具调用或结束。"""
    # 将工具绑定到模型，让 LLM 自主选择是否调用工具。
    model = get_deepseek_chat_model(streaming=False).bind_tools(get_planner_tools())
    # 动态拼接系统提示 + 历史消息后调用模型，拿到带工具调用或纯文本的回复。
    response = model.invoke(_build_agent_messages(state))

    # 记录 Agent 决策步骤，模型无工具调用时保存最终路线文本。
    process_steps = list(state.get('process_steps', []))
    process_steps.append(_build_agent_decision_step(response, state))
    result = {'messages': [response], 'process_steps': process_steps}
    # 模型不再请求工具调用时，本轮回复就是最终路线，清洗后存入状态。
    if not _message_has_tool_calls(response):
        result['final_plan'] = sanitize_final_plan(_message_content_to_text(response))
    return result
def _sync_tool_outputs(state: PlannerState) -> dict[str, Any]:
    """功能说明：解析尚未同步的 ToolNode 输出并更新结构化状态。"""
    # 准备可变副本，避免直接修改 LangGraph 状态对象。
    processed_tool_call_ids = set(state.get('processed_tool_call_ids', []))
    process_steps = list(state.get('process_steps', []))
    intent = dict(state.get('intent') or {})
    candidates = list(state.get('candidates', []))
    route_stops = list(state.get('route_stops', []))
    validation_result = dict(state.get('validation_result', {}))

    # 逐条处理尚未同步的 ToolMessage，按工具名称更新对应状态字段。
    # 只过滤消息流里的工具执行结果，其余历史消息跳过。
    for message in state.get('messages', []):
        if not isinstance(message, ToolMessage):
            continue
        # 跳过上一轮 sync 已同步过的调用，防止重复填充状态和重复追加步骤。
        tool_call_id = getattr(message, 'tool_call_id', '') or ''
        if tool_call_id in processed_tool_call_ids:
            continue
        # 工具结果正文是 JSON 字符串，先解析成字典再分发。
        tool_name = _resolve_tool_name(message, state)
        payload = load_json_dict(_message_content_to_text(message))

        # 按工具名分发到对应状态字段，并追加一条页面过程步骤。
        if tool_name == 'parse_travel_intent':
            intent = _build_intent_from_payload(payload, state)
            process_steps.append(_build_intent_step(intent))
        elif tool_name == 'search_attractions':
            # 工具异常返回非列表时降级为空候选，保证后续节点不炸。
            candidates = payload.get('attractions', [])
            if not isinstance(candidates, list):
                candidates = []
            process_steps.append(
                {'title': '景点检索', 'description': f'工具返回 {len(candidates)} 个候选景点。', 'status': 'success'}
            )
        elif tool_name == 'build_route_candidates':
            route_stops = payload.get('route_stops', [])
            if not isinstance(route_stops, list):
                route_stops = []
            process_steps.append(
                {'title': '路线生成', 'description': f'工具生成 {len(route_stops)} 个地图站点和游览顺序。', 'status': 'success'}
            )
        elif tool_name == 'validate_route_plan':
            validation_result = payload
            # 检查工具若给出优化后顺序（消除折返），则替换原站点列表。
            optimized_route_stops = payload.get('optimized_route_stops') or route_stops
            if isinstance(optimized_route_stops, list):
                route_stops = optimized_route_stops
            process_steps.append(_build_validation_step(payload))
        # 标记本条已同步，下一轮循环直接跳过。
        processed_tool_call_ids.add(tool_call_id)

    return {
        'intent': intent,
        'candidates': candidates,
        'route_stops': route_stops,
        'validation_result': validation_result,
        'process_steps': process_steps,
        'processed_tool_call_ids': list(processed_tool_call_ids),
    }


def _resolve_tool_name(message: ToolMessage, state: PlannerState) -> str:
    """功能说明：解析 ToolMessage 对应的工具名称。"""
    # 当前 LangGraph 版本会在 ToolMessage 中直接携带工具名。
    message_name = getattr(message, 'name', '') or ''
    if message_name:
        return message_name

    # 兼容没有 name 字段的情况，通过 tool_call_id 回查 AIMessage.tool_calls。
    tool_call_id = getattr(message, 'tool_call_id', '') or ''
    for history_message in state.get('messages', []):
        if not isinstance(history_message, AIMessage):
            continue
        for tool_call in getattr(history_message, 'tool_calls', []) or []:
            if tool_call.get('id') == tool_call_id:
                return tool_call.get('name', '')
    return ''


def _build_intent_from_payload(payload: dict[str, Any], state: PlannerState) -> dict[str, Any]:
    """功能说明：规范化大模型工具返回的旅游规划意图。"""
    # 从工具结果中提取字段，缺失时使用用户输入和规则解析兜底。
    preference_tags = payload.get('preference_tags') or split_preferences(state['preferences'])
    if isinstance(preference_tags, str):
        preference_tags = split_preferences(preference_tags)
    if not isinstance(preference_tags, list):
        preference_tags = split_preferences(state['preferences'])

    # 旅行天数优先使用模型识别结果，无法转换时回退到规则解析。
    try:
        days = int(payload.get('days') or parse_travel_days(state['travel_time']))
    except (TypeError, ValueError):
        days = parse_travel_days(state['travel_time'])

    # 返回结构稳定的意图字典，便于后续保存和提示词使用。
    return {
        'city': payload.get('city') or state['city'],
        'budget': payload.get('budget') or state['budget'],
        'travel_time': payload.get('travel_time') or state['travel_time'],
        'days': days,
        'preference_tags': preference_tags,
        'pace': payload.get('pace') or '',
        'intent_summary': payload.get('intent_summary') or '',
    }


def _build_intent_step(intent: dict[str, Any]) -> dict[str, str]:
    """功能说明：根据结构化意图构建页面过程步骤。"""
    # 汇总大模型识别出的核心意图，展示给用户和教师讲解。
    tags = intent.get('preference_tags') or []
    description = (
        f"大模型识别别目的地 {intent.get('city')}，旅行天数约 {intent.get('days')} 天，"
        f"偏好为 {tags}，节奏为 {intent.get('pace')}。"
    )
    return {'title': '意图识别', 'description': description, 'status': 'success'}


def _build_validation_step(validation_result: dict[str, Any]) -> dict[str, str]:
    """功能说明：根据路线检查结果构建页面过程步骤。"""
    # 按检查问题生成成功或警告状态。
    issues = validation_result.get('issues', [])
    suggestions = validation_result.get('suggestions', [])
    score = validation_result.get('score', 0)
    distance_ratio = validation_result.get('distance_ratio', 1)

    if issues:
        description = f"检查评分 {score} 分，折返指数 {distance_ratio}，发现：{'；'.join(issues)}"
        if suggestions:
            description = f"{description}。建议：{'；'.join(suggestions)}"
        return {'title': '路线质量检查', 'description': description, 'status': 'warning'}

    return {
        'title': '路线质量检查',
        'description': f'检查评分 {score} 分，折返指数 {distance_ratio}，路线符合用户要求且没有明显来回折返。',
        'status': 'success',
    }
def build_route_graph():
    """功能说明：构建标准 LangGraph Tool-calling Agent 图。"""
    # 标准结构：Agent 自主决策 -> ToolNode 执行工具 -> sync 回填状态 -> Agent 继续决策。
    workflow = StateGraph(PlannerState)
    # agent 是大脑（LLM），tools 是预构建 ToolNode（执行工具），sync 是状态回填桥接。
    workflow.add_node('agent', _agent_node)
    workflow.add_node('tools', ToolNode(get_planner_tools()))
    workflow.add_node('sync', _sync_tool_outputs)
    # 入口直接进 agent；agent 后用 tools_condition 分流：有工具调用走 tools，否则结束。
    workflow.add_edge(START, 'agent')
    workflow.add_conditional_edges('agent', tools_condition)
    # tools 执行完先经 sync 把工具结果回填到结构化状态，再回到 agent 继续决策。
    workflow.add_edge('tools', 'sync')
    workflow.add_edge('sync', 'agent')
    # compile 后得到可 invoke/stream 的运行时对象。
    return workflow.compile()
#if (!window.ReadableStream || !form.dataset.streamUrl)
#return;   // 直接 return，不 preventDefault
#浏览器支持 ReadableStream（现代浏览器都支持）；表单上有 data-stream-url 属性选择stream_route的方式，不支持选择run_route
def run_route_planner(city: str, budget: str, travel_time: str, preferences: str) -> dict[str, Any]:
    """功能说明：运行标准 LangGraph Agent 并返回路线规划结果。"""
    # invoke 阻塞跑完整循环，返回最终状态（与 stream 版本结果等价，仅交互方式不同）。
    graph = build_route_graph()
    final_state = graph.invoke(_build_initial_state(city, budget, travel_time, preferences))
    return _build_result_payload(final_state)
def _build_result_payload(state: PlannerState) -> dict[str, Any]:
    """功能说明：从 LangGraph 状态中提取可保存的路线规划结果。"""
    # 只挑服务层需要落库/展示的字段；messages 等运行时数据不外传。
    return {
        'intent': state.get('intent', {}),
        'candidates': state.get('candidates', []),
        'route_stops': state.get('route_stops', []),
        'validation_result': state.get('validation_result', {}),
        'final_plan': state.get('final_plan', ''),
        'process_steps': state.get('process_steps', []),
    }
def stream_route_planner(city: str, budget: str, travel_time: str, preferences: str) -> Iterator[dict[str, Any]]:
    """功能说明：流式运行标准 LangGraph Agent 并逐步返回规划事件。"""
    graph = build_route_graph()
    state = _build_initial_state(city, budget, travel_time, preferences)
    # 手动补一条“任务启动”步骤，让前端立刻看到反馈，不等第一个节点跑完。
    start_step = {'title': '任务启动', 'description': '已收到规划条件，正在启动标准 LangGraph Agent。', 'status': 'running'}
    state['process_steps'] = [start_step] + list(state.get('process_steps', []))
    # 记录已推送的步骤数，后续只推送增量，避免快照模式下重复发同一步骤。
    yielded_step_count = len(state['process_steps'])
    #每yield一次相当于return一次
    yield {'event': 'step', 'data': start_step}
    yield {'event': 'step', 'data': state['process_steps'][1]}

    # 标记最终路线文本是否已推送，防止多轮快照重复发送。
    final_text_yielded = False
    # stream_mode='values'：每个节点执行完产出一个完整状态快照，据此增量推送事件。
    for chunk in graph.stream(state, stream_mode='values'):
        # 快照里出现 final_plan 说明 Agent 已产出最终路线，立即推送正文。
        final_plan = str(chunk.get('final_plan') or '')
        if final_plan and not final_text_yielded:
            final_text_yielded = True
            yield {'event': 'final_start', 'data': {'message': '标准 Agent 已完成工具调用，正在输出最终路线。'}}
            yield {'event': 'final_delta', 'data': {'content': final_plan}}

        # 输出本轮新增的过程步骤。
        for step in chunk.get('process_steps', [])[yielded_step_count:]:
            yielded_step_count += 1
            yield {'event': 'step', 'data': step}
        # 保留最新快照，供循环结束后的兜底判断使用。
        state = chunk

    # 兜底：若最后一个快照在循环内未触发推送（如末轮才写入 final_plan），补发一次。
    if state.get('final_plan') and not final_text_yielded:
        yield {'event': 'final_start', 'data': {'message': '标准 Agent 已生成最终路线。'}}
        yield {'event': 'final_delta', 'data': {'content': state['final_plan']}}
    # 图运行结束后的收尾：推送站点数据供前端画地图，最后推送完整结果落库。
    yield {'event': 'route_stops', 'data': {'route_stops': state.get('route_stops', [])}}
    yield {'event': 'graph_done', 'data': _build_result_payload(state)}








