"""功能说明：AI 路线规划 JSON 解析工具。"""
import json
from typing import Any


def dump_json(data: Any) -> str:
    """功能说明：将 Python 数据转换为中文友好的 JSON 字符串。"""
    # 保留中文字符，便于工具消息和页面调试阅读。
    return json.dumps(data, ensure_ascii=False)


def extract_json_object(content: str) -> dict[str, Any]:
    """功能说明：从大模型返回文本中提取第一个 JSON 对象。"""
    # 优先尝试完整 JSON 解析。
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        return parsed

    # 逐字符定位第一个完整 JSON 对象，兼容模型包裹说明文字的情况。
    start_index = content.find('{')
    if start_index < 0:
        return {}
    brace_count = 0
    for index in range(start_index, len(content)):
        character = content[index]
        if character == '{':
            brace_count += 1
        elif character == '}':
            brace_count -= 1
            if brace_count == 0:
                json_text = content[start_index:index + 1]
                try:
                    result = json.loads(json_text)
                except json.JSONDecodeError:
                    return {}
                return result if isinstance(result, dict) else {}

    # 没有匹配到完整 JSON 对象时返回空字典。
    return {}


def load_json_dict(content: str) -> dict[str, Any]:
    """功能说明：将 JSON 字符串安全解析为字典。"""
    # 解析失败时返回空字典，避免工具链中断。
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
