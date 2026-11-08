from collections.abc import Iterator
from typing import Any

from django.conf import settings
from langchain_openai import ChatOpenAI
from openai import OpenAI


class PlannerConfigError(Exception):
    """功能说明：表示 AI 路线规划配置缺失或不可用。"""


def get_deepseek_client() -> OpenAI:
    """功能说明：创建 DeepSeek OpenAI 兼容客户端。"""
    # 校验 API Key，避免请求阶段才出现不明确的错误。
    api_key = getattr(settings, 'DEEPSEEK_API_KEY', '')
    if not api_key:
        raise PlannerConfigError('未配置 DEEPSEEK_API_KEY，请在环境变量中填写后再使用 AI 路线规划助手。')

    # 使用 DeepSeek OpenAI 兼容接口创建客户端。
    return OpenAI(api_key=api_key, base_url=getattr(settings, 'DEEPSEEK_BASE_URL', 'https://api.deepseek.com'))


def get_deepseek_chat_model(streaming: bool = False) -> ChatOpenAI:
    """功能说明：创建支持 LangGraph 工具绑定的 DeepSeek ChatOpenAI 模型。"""
    # 校验 API Key，确保 Agent 节点可以正常调用模型。
    api_key = getattr(settings, 'DEEPSEEK_API_KEY', '')
    if not api_key:
        raise PlannerConfigError('未配置 DEEPSEEK_API_KEY，请在环境变量或 .env 文件中填写后再使用 AI 路线规划助手。')

    # 使用 langchain-openai 的 OpenAI 兼容客户端，便于 bind_tools 接入 ToolNode。
    return ChatOpenAI(
        api_key=api_key,
        base_url=getattr(settings, 'DEEPSEEK_BASE_URL', 'https://api.deepseek.com'),
        model=getattr(settings, 'DEEPSEEK_MODEL', 'deepseek-v4-pro'),
        temperature=0,
        streaming=streaming,
        model_kwargs={
            'reasoning_effort': 'high',
            'extra_body': {'thinking': {'type': 'enabled'}},
        },
    )


def call_deepseek_chat(messages: list[dict[str, str]]) -> str:
    """功能说明：调用 DeepSeek Chat Completions 并返回文本内容。"""
    # 获取客户端和模型配置。
    client = get_deepseek_client()
    model_name = getattr(settings, 'DEEPSEEK_MODEL', 'deepseek-v4-pro')

    # 按用户提供的参数调用 DeepSeek。
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        stream=False,
        reasoning_effort='high',
        extra_body={'thinking': {'type': 'enabled'}},
    )

    # 返回第一条回复内容。
    content: Any = response.choices[0].message.content
    return str(content or '').strip()
