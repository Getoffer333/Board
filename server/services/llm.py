"""LLM 在线调用服务。支持 DeepSeek 兼容 API。"""

import json
import httpx

from ..db import get_setting

# DeepSeek 默认配置
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


def _call_llm(prompt: str) -> str:
    """调用 LLM，返回原始文本响应。"""
    base_url = get_setting("llm_base_url", DEFAULT_BASE_URL).rstrip("/")
    api_key = get_setting("llm_api_key", "")
    model = get_setting("llm_model", DEFAULT_MODEL)

    if not api_key:
        raise RuntimeError("未配置 LLM API Key，请在设置中填写")

    url = f"{base_url}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一个专业的求职助手。请严格按照要求的 JSON 格式返回结果，不要添加任何解释文字或 markdown 包裹。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 4096,
    }

    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            # 去掉可能的 ```json 包裹
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:]) if lines[0].startswith("```") else content
                if content.endswith("```"):
                    content = content[:-3].strip()
            return content
    except httpx.HTTPError as e:
        raise RuntimeError(f"LLM 调用失败: {e}")
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"LLM 返回格式异常: {e}")


def call_llm_json(prompt: str) -> dict:
    """调用 LLM 并解析为 JSON。"""
    raw = _call_llm(prompt)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # 尝试从文本中提取 JSON
        import re
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            return json.loads(match.group())
        raise RuntimeError(f"LLM 返回无法解析为 JSON: {raw[:200]}...")
