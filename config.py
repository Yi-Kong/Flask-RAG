"""应用配置 — 所有配置全部来源于 .env 文件或环境变量，不提供默认值."""
import os

from dotenv import load_dotenv

# 加载项目根目录下的 .env 文件
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _parse_bool(val: str | None) -> bool | None:
    """解析布尔型环境变量，val 为 None 时返回 None."""
    if val is None:
        return None
    return val.strip().lower() in ("true", "1", "yes", "on")


def _parse_set(val: str | None) -> set | None:
    """解析逗号分隔的集合型环境变量，val 为 None 时返回 None."""
    if val is None:
        return None
    return {item.strip().lower() for item in val.split(",") if item.strip()}


class Config:
    # ── 数据库连接地址 ──────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")

    # 关闭对象修改追踪，减少额外开销
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ECHO = _parse_bool(os.getenv("SQLALCHEMY_ECHO"))

    # ── 文件上传配置 ────────────────────────────────────────
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER")
    # 如果 UPLOAD_FOLDER 是相对路径，转为绝对路径
    if UPLOAD_FOLDER and not os.path.isabs(UPLOAD_FOLDER):
        UPLOAD_FOLDER = os.path.join(BASE_DIR, UPLOAD_FOLDER)

    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH"))
    ALLOWED_EXTENSIONS = _parse_set(os.getenv("ALLOWED_EXTENSIONS"))

    # ── RAG 处理配置 ────────────────────────────────────────
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP"))
    # 嵌入模型: 支持 HuggingFace 模型名 或 本地路径
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
    EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE"))

    # ── RAG 相关性阈值 ──────────────────────────────────────
    # 余弦距离上限：超过此值的检索结果视为不相关，会被过滤
    # BGE-small-zh 配合 L2 归一化，余弦距离范围 0（完全相同）到 2（完全相反）
    # 默认 0.7 对应余弦相似度约 0.65
    RAG_RELEVANCE_THRESHOLD = float(os.getenv("RAG_RELEVANCE_THRESHOLD", "0.7"))
    # 高可信度阈值：任一结果余弦距离 ≤ 此值则判定为 HIGH
    RAG_HIGH_CONFIDENCE_THRESHOLD = float(os.getenv("RAG_HIGH_CONFIDENCE_THRESHOLD", "0.4"))

    # ChromaDB 存储策略
    #   "single_collection": 所有文档存入单个集合（旧方案）
    #   "per_document":      每文档创建一个独立集合（推荐）
    CHROMA_STORAGE_STRATEGY = os.getenv("CHROMA_STORAGE_STRATEGY", "per_document")

    # ChromaDB 集合名（single_collection 模式使用）
    CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "document_chunks")

    # ChromaDB 集合名前缀（per_document 模式使用，集合名格式: {prefix}{document_id}）
    CHROMA_COLLECTION_PREFIX = os.getenv("CHROMA_COLLECTION_PREFIX", "doc_")

    # ChromaDB 服务地址（HttpClient 模式，需先启动 chroma run）
    CHROMA_HOST = os.getenv("CHROMA_HOST", "127.0.0.1")
    CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))

    # ── DeepSeek API 配置 ───────────────────────────────────
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL")
    DEEPSEEK_TIMEOUT = int(os.getenv("DEEPSEEK_TIMEOUT"))
    DEEPSEEK_MAX_TOKENS = int(os.getenv("DEEPSEEK_MAX_TOKENS"))
    DEEPSEEK_TEMPERATURE = float(os.getenv("DEEPSEEK_TEMPERATURE"))

    # ── Flask 应用配置 ──────────────────────────────────────
    # Secret 类，不给默认值，必须从 .env 获取
    SECRET_KEY = os.getenv("SECRET_KEY")

    # ── JWT 认证配置 ────────────────────────────────────────
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")       # Secret，不给默认值
    JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "2"))

    # ── Coze API 配置 ───────────────────────────────────────
    COZE_API_TOKEN = os.getenv("COZE_API_TOKEN")        # Secret，不给默认值
    COZE_WORKFLOW_ID = os.getenv("COZE_WORKFLOW_ID")    # Secret，不给默认值

    # ── Cookie 配置（非 Secret，可给默认值）─────────────────
    COOKIE_MAX_AGE = int(os.getenv("COOKIE_MAX_AGE", "7200"))
    COOKIE_HTTPONLY = (_parse_bool(os.getenv("COOKIE_HTTPONLY")) is not False)
    COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "Lax")


# ── 启动校验 ────────────────────────────────────────────────────

_REQUIRED_SECRETS = [
    "SECRET_KEY",
    "JWT_SECRET_KEY",
    "SQLALCHEMY_DATABASE_URI",
]


def validate_config():
    """校验必需的 Secret 配置项是否已设置，缺失则抛出 RuntimeError."""
    missing = []
    for key in _REQUIRED_SECRETS:
        if not getattr(Config, key, None):
            missing.append(key)
    if missing:
        raise RuntimeError(
            f"缺少必需的配置项，请在 .env 文件中设置: {', '.join(missing)}\n"
            f"参考 .env.example 文件创建或更新你的 .env 配置。"
        )
