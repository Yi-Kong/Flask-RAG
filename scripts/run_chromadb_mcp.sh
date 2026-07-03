#!/bin/bash
# ============================================================
# ChromaDB MCP Server 启动脚本
# 从项目根目录 .env 中读取 ChromaDB 连接配置
# 首次运行自动安装 chromadb-mcp，后续直接启动
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

CACHE_DIR="${HOME}/.cache/chromadb-mcp-server"
PKG_DIR="${CACHE_DIR}/node_modules/chromadb-mcp"
PKG_VERSION="0.1.0"

# 首次运行：安装 chromadb-mcp
if [ ! -f "${PKG_DIR}/dist/index.js" ]; then
    echo "[chromadb-mcp] 首次启动，正在安装 chromadb-mcp@${PKG_VERSION} ..." >&2
    mkdir -p "${CACHE_DIR}"
    cd "${CACHE_DIR}"
    npm init -y --silent 2>/dev/null
    npm install "chromadb-mcp@${PKG_VERSION}" --silent
    echo "[chromadb-mcp] 安装完成" >&2
fi

# 从 .env 加载 ChromaDB 配置（CHROMA_HOST, CHROMA_PORT）
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    . "$PROJECT_DIR/.env"
    set +a
fi

# 构建 CHROMA_HOST（chromadb-mcp 需要的格式）
if [ -n "$CHROMA_PORT" ] && [ -n "$CHROMA_HOST" ]; then
    # .env 中 CHROMA_HOST 和 CHROMA_PORT 是分开的，需要拼成 URL
    export CHROMA_HOST="http://${CHROMA_HOST}:${CHROMA_PORT}"
elif [ -z "$CHROMA_HOST" ]; then
    export CHROMA_HOST="http://127.0.0.1:8000"
fi

echo "[chromadb-mcp] 连接 $CHROMA_HOST" >&2

exec node "${PKG_DIR}/dist/index.js"
