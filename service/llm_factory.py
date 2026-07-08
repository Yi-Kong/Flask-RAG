"""LLM 工厂 — 管理多模型 Profile，创建 LangChain ChatModel 实例.

支持通过 Config.LLM_PROFILES_JSON 配置多个模型 Profile，
运行时通过 LLM_DEFAULT_PROFILE / LLM_RAG_PROFILE 切换。

所有 OpenAI-compatible API（DeepSeek / Qwen / GLM / Kimi 等）
统一通过 langchain-openai 的 ChatOpenAI 调用。
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from langchain_openai import ChatOpenAI
from config import Config

logger = logging.getLogger(__name__)


# ── 数据模型 ──────────────────────────────────────────────────────────

@dataclass
class LLMProfile:
    """单个 LLM 模型 Profile."""
    name: str                                    # Profile 唯一名称（如 "deepseek", "openai"）
    provider: str = "openai_compatible"           # "openai" 或 "openai_compatible"
    model: str = ""                              # 模型名（如 "deepseek-chat", "gpt-4o"）
    api_key: str = ""                            # API Key
    base_url: str = ""                           # API Base URL（openai 可用默认值）
    temperature: float = 0.3
    max_tokens: int = 2048
    timeout: int = 60


# ── Profile 解析 ─────────────────────────────────────────────────────

def _build_default_profile() -> Optional[LLMProfile]:
    """从旧版 DEEPSEEK_* 配置项构建默认 deepseek profile（向后兼容）."""
    if not Config.DEEPSEEK_API_KEY:
        return None
    return LLMProfile(
        name="deepseek",
        provider="openai_compatible",
        model=Config.DEEPSEEK_MODEL,
        api_key=Config.DEEPSEEK_API_KEY,
        base_url=Config.DEEPSEEK_BASE_URL,
        temperature=Config.DEEPSEEK_TEMPERATURE,
        max_tokens=Config.DEEPSEEK_MAX_TOKENS,
        timeout=Config.DEEPSEEK_TIMEOUT,
    )


def _parse_profiles() -> Dict[str, LLMProfile]:
    """解析 LLM_PROFILES_JSON 配置，返回 {name: LLMProfile} 字典.

    如果 LLM_PROFILES_JSON 为空，自动从旧版 DEEPSEEK_* 构建默认 profile。
    """
    profiles: Dict[str, LLMProfile] = {}
    profiles_json = Config.LLM_PROFILES_JSON

    if profiles_json:
        try:
            raw_list = json.loads(profiles_json)
            if not isinstance(raw_list, list):
                logger.error("LLM_PROFILES_JSON 格式错误：应为 JSON 数组，实际为 %s", type(raw_list))
                raw_list = []
        except json.JSONDecodeError as e:
            logger.error("LLM_PROFILES_JSON 解析失败: %s", e)
            raw_list = []
    else:
        raw_list = []

    for p in raw_list:
        try:
            profile = LLMProfile(
                name=p["name"],
                provider=p.get("provider", "openai_compatible"),
                model=p.get("model", ""),
                api_key=p.get("api_key", ""),
                base_url=p.get("base_url", ""),
                temperature=float(p.get("temperature", 0.3)),
                max_tokens=int(p.get("max_tokens", 2048)),
                timeout=int(p.get("timeout", 60)),
            )
            if not profile.name or not profile.model:
                logger.warning("跳过无效 profile（缺少 name 或 model）: %s", p)
                continue
            profiles[profile.name] = profile
        except (KeyError, ValueError, TypeError) as e:
            logger.warning("跳过无效 profile 条目: %s, 错误: %s", p, e)

    # 向后兼容：无 profile 配置时从旧版 DEEPSEEK_* 构建
    if not profiles:
        default = _build_default_profile()
        if default:
            profiles[default.name] = default
            logger.info("未配置 LLM_PROFILES_JSON，从 DEEPSEEK_* 配置自动构建 profile: %s", default.name)

    return profiles


# ── 缓存 ─────────────────────────────────────────────────────────────

_profile_cache: Optional[Dict[str, LLMProfile]] = None
_chat_model_cache: Dict[str, ChatOpenAI] = {}


def _get_profiles_cached() -> Dict[str, LLMProfile]:
    """获取缓存的 profiles（首次调用时解析）."""
    global _profile_cache
    if _profile_cache is None:
        _profile_cache = _parse_profiles()
        masked_profiles = [
            {**{k: v for k, v in p.__dict__.items() if k != "api_key"},
             "api_key": (p.api_key[:8] + "***") if len(p.api_key) > 8 else "***"}
            for p in _profile_cache.values()
        ]
        logger.info("加载 %d 个 LLM profile: %s", len(_profile_cache), masked_profiles)
    return _profile_cache


def reset_profile_cache() -> None:
    """重置 profile 缓存（用于配置热更新或测试）."""
    global _profile_cache, _chat_model_cache
    _profile_cache = None
    _chat_model_cache.clear()


# ── 公开 API ─────────────────────────────────────────────────────────

def list_profiles() -> List[str]:
    """返回所有可用的 profile 名称列表."""
    return list(_get_profiles_cached().keys())


def get_profile(name: Optional[str] = None) -> LLMProfile:
    """获取指定 profile 的配置数据.

    Args:
        name: profile 名称，为 None 时使用 LLM_DEFAULT_PROFILE.

    Returns:
        LLMProfile 对象.

    Raises:
        ValueError: profile 名称不存在.
        RuntimeError: 没有任何可用的 profile.
    """
    profiles = _get_profiles_cached()
    target = name or Config.LLM_DEFAULT_PROFILE

    if not profiles:
        raise RuntimeError(
            "没有可用的 LLM profile。请在 .env 中配置 LLM_PROFILES_JSON "
            "或设置 DEEPSEEK_API_KEY（向后兼容模式）。"
        )
    if target not in profiles:
        available = list(profiles.keys())
        raise ValueError(f"未知的 LLM profile: '{target}'，可用: {available}")

    return profiles[target]


def create_chat_model(profile_name: Optional[str] = None) -> ChatOpenAI:
    """根据 profile 创建 LangChain ChatOpenAI 实例.

    实例会被缓存，同一 profile 多次调用返回同一对象。

    Args:
        profile_name: profile 名称，为 None 时使用默认 profile.

    Returns:
        配置好的 ChatOpenAI 实例，可直接用于 LangChain Chain.

    Raises:
        ValueError: profile 不存在.
        RuntimeError: 无可用 profile.
    """
    profile = get_profile(profile_name)
    cache_key = profile.name

    if cache_key in _chat_model_cache:
        return _chat_model_cache[cache_key]

    kwargs: dict = {
        "model": profile.model,
        "api_key": profile.api_key,
        "temperature": profile.temperature,
        "max_tokens": profile.max_tokens,
        "timeout": profile.timeout,
    }
    # ChatOpenAI 的 base_url 参数名
    if profile.base_url:
        kwargs["base_url"] = profile.base_url

    llm = ChatOpenAI(**kwargs)

    masked_key = profile.api_key[:8] + "***" if len(profile.api_key) > 8 else "***"
    logger.info(
        "创建 ChatOpenAI 实例: profile=%s, model=%s, base_url=%s, key=%s",
        profile.name, profile.model, profile.base_url, masked_key,
    )

    _chat_model_cache[cache_key] = llm
    return llm


def get_rag_llm() -> ChatOpenAI:
    """获取 RAG 问答专用的 LLM 实例.

    优先使用 LLM_RAG_PROFILE 配置的模型，
    未配置时 fallback 到 LLM_DEFAULT_PROFILE。
    """
    target = Config.LLM_RAG_PROFILE if Config.LLM_RAG_PROFILE else None
    return create_chat_model(target)
