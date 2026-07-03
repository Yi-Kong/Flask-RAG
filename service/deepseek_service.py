"""DeepSeek API 调用服务.

使用 OpenAI 兼容的 chat/completions 接口。
所有配置从环境变量读取，不硬编码 API Key。
"""
import json
import logging
from typing import Optional

import requests
from config import Config

logger = logging.getLogger(__name__)


def _get_config():
    """从 Config 读取 DeepSeek 配置."""
    return {
        "api_key": Config.DEEPSEEK_API_KEY,
        "base_url": Config.DEEPSEEK_BASE_URL,
        "model": Config.DEEPSEEK_MODEL,
        "timeout": Config.DEEPSEEK_TIMEOUT,
        "max_tokens": Config.DEEPSEEK_MAX_TOKENS,
        "temperature": Config.DEEPSEEK_TEMPERATURE,
    }


def chat_service(
    messages: list,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """调用 DeepSeek Chat API 获取回复.

    Args:
        messages: 消息列表，格式 [{"role": "user"|"system"|"assistant", "content": "..."}].
        temperature: 温度参数，为 None 时使用配置默认值.
        max_tokens: 最大生成 token 数，为 None 时使用配置默认值.

    Returns:
        模型回复文本.

    Raises:
        ValueError: API Key 未配置.
        ConnectionError: 网络连接失败.
        TimeoutError: 请求超时.
        RuntimeError: API 返回错误.
    """
    cfg = _get_config()

    if not cfg["api_key"]:
        raise ValueError("DeepSeek API Key 未配置，请设置环境变量 DEEPSEEK_API_KEY")

    url = f"{cfg['base_url'].rstrip('/')}/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": temperature if temperature is not None else cfg["temperature"],
        "max_tokens": max_tokens if max_tokens is not None else cfg["max_tokens"],
        "stream": False,
    }

    # 安全日志：不打印完整 API Key
    masked_key = cfg["api_key"][:8] + "***" if len(cfg["api_key"]) > 8 else "***"
    logger.info(
        "调用 DeepSeek API: model=%s, url=%s, key=%s, timeout=%ds",
        cfg["model"], url, masked_key, cfg["timeout"],
    )

    try:
        resp = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=cfg["timeout"],
        )
    except requests.exceptions.Timeout:
        logger.error("DeepSeek API 请求超时（%ds）", cfg["timeout"])
        raise TimeoutError(f"DeepSeek API 请求超时（{cfg['timeout']}秒）")
    except requests.exceptions.ConnectionError as e:
        logger.error("DeepSeek API 连接失败: %s", e)
        raise ConnectionError(f"DeepSeek API 连接失败: {str(e)}")
    except requests.exceptions.RequestException as e:
        logger.error("DeepSeek API 请求异常: %s", e)
        raise RuntimeError(f"DeepSeek API 请求异常: {str(e)}")

    if not resp.ok:
        logger.error("DeepSeek API 返回错误: status=%d, body=%s", resp.status_code, resp.text[:500])
        raise RuntimeError(f"DeepSeek API 返回错误（{resp.status_code}）")

    try:
        data = resp.json()
    except json.JSONDecodeError as e:
        logger.error("DeepSeek API 响应解析失败: %s", e)
        raise RuntimeError("DeepSeek API 响应格式异常")

    # 提取回答内容
    choices = data.get("choices", [])
    if not choices:
        logger.error("DeepSeek API 返回空 choices: %s", json.dumps(data, ensure_ascii=False)[:500])
        raise RuntimeError("DeepSeek API 未返回有效回答")

    content = choices[0].get("message", {}).get("content", "")
    if not content:
        logger.warning("DeepSeek API 返回内容为空")

    # 打印 token 用量（用于监控）
    usage = data.get("usage", {})
    if usage:
        logger.info(
            "DeepSeek API 调用完成: prompt_tokens=%s, completion_tokens=%s, total_tokens=%s",
            usage.get("prompt_tokens", "?"),
            usage.get("completion_tokens", "?"),
            usage.get("total_tokens", "?"),
        )

    return content


def chat_with_prompt_service(
    system_prompt: str,
    user_prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """使用 system + user 双消息调用 DeepSeek Chat.

    Args:
        system_prompt: 系统提示词.
        user_prompt: 用户提示词（含参考资料 + 用户问题）.
        temperature: 温度参数.
        max_tokens: 最大生成 token 数.

    Returns:
        模型回复文本.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    return chat_service(messages, temperature=temperature, max_tokens=max_tokens)
