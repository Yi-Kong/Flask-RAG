"""向量嵌入服务 — Sentence-Transformers 惰性加载单例.

模型首次调用时自动加载，之后复用同一实例。
默认使用 BAAI/bge-small-zh-v1.5（中文优化，512 维输出）.

模型加载策略（按优先级）:
  1. config.EMBEDDING_MODEL 指定的本地路径
  2. 本地路径不存在时回退到 BAAI/bge-small-zh-v1.5（从 HuggingFace 在线下载）

国内用户先用 download_model.py 下载到本地: python download_model.py
"""
import logging
import os
from typing import List

import numpy as np

logger = logging.getLogger(__name__)

# 全局模型实例（惰性加载）
_model = None
_model_name = None


def _resolve_model_path() -> str:
    """解析模型路径，本地优先.

    Returns:
        可用的模型路径（本地路径或 HuggingFace 模型名）.
    """
    try:
        from config import Config
        configured = Config.EMBEDDING_MODEL
    except Exception:
        configured = os.getenv("EMBEDDING_MODEL")

    if not configured:
        raise RuntimeError("EMBEDDING_MODEL 未配置，请在 .env 中设置")

    # 如果配置的是本地路径且存在，直接使用
    if os.path.isdir(configured):
        config_path = os.path.join(configured, "config.json")
        if os.path.isfile(config_path):
            logger.info("使用本地模型: %s", configured)
            return configured
        else:
            logger.warning("本地模型目录存在但缺少 config.json: %s", configured)

    # 如果是相对路径，尝试从项目根目录解析
    if not os.path.isabs(configured):
        local_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            configured,
        )
        if os.path.isdir(local_path) and os.path.isfile(os.path.join(local_path, "config.json")):
            logger.info("使用本地模型（项目路径）: %s", local_path)
            return local_path

    # 作为 HuggingFace 模型名在线加载
    logger.info("本地模型未找到，将从 HuggingFace 下载: %s", configured)
    return configured


def get_model():
    """返回全局 SentenceTransformer 实例，首次调用时加载模型.

    模型仅加载一次，后续调用复用同一实例。
    """
    global _model, _model_name
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model_name = _resolve_model_path()
        logger.info("正在加载嵌入模型: %s ...", _model_name)
        _model = SentenceTransformer(_model_name)
        logger.info(
            "嵌入模型加载完成: %s (输出维度=%d)",
            _model_name,
            _model.get_sentence_embedding_dimension(),
        )
    return _model


def embed_texts_service(texts: List[str], batch_size: int = None) -> np.ndarray:
    if batch_size is None:
        try:
            from config import Config
            batch_size = Config.EMBEDDING_BATCH_SIZE
        except Exception:
            batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE"))

    """批量将文本列表转换为向量嵌入.

    Args:
        texts: 待嵌入的文本列表.
        batch_size: 编码时的批量大小.

    Returns:
        shape (N, dim) 的 float32 numpy 数组，已 L2 归一化.
    """
    if not texts:
        logger.warning("embed_texts 收到空列表")
        return np.array([], dtype=np.float32)

    model = get_model()
    logger.info("正在对 %d 条文本进行向量嵌入 ...", len(texts))

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,  # L2 归一化，配合 cosine 距离
    )

    logger.info("向量嵌入完成：%d 条 → shape=%s", len(texts), embeddings.shape)
    return embeddings.astype(np.float32)


def embed_query_service(text: str) -> np.ndarray:
    """将单条查询文本转换为向量嵌入.

    Args:
        text: 查询文本.

    Returns:
        shape (dim,) 的 float32 numpy 数组，已 L2 归一化.
    """
    model = get_model()
    embedding = model.encode(
        [text],
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return embedding[0].astype(np.float32)


def reset_model():
    """重置模型实例（主要用于测试）. """
    global _model
    if _model is not None:
        del _model
        _model = None
        import gc
        gc.collect()
        logger.info("嵌入模型已重置")
