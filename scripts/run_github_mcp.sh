#!/bin/bash
# ============================================================
# GitHub MCP Server 启动脚本
# 从项目根目录 .env 中读取 GITHUB_TOKEN，启动 MCP 服务
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# 从 .env 加载环境变量
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    . "$PROJECT_DIR/.env"
    set +a
fi

# 检查 GITHUB_TOKEN 是否已设置
if [ -z "$GITHUB_TOKEN" ]; then
    echo "[github-mcp] 错误: .env 中未找到 GITHUB_TOKEN" >&2
    echo "[github-mcp] 请先在 .env 中添加: GITHUB_TOKEN=ghp_xxxxxxxxxxxx" >&2
    exit 1
fi

# GitHub MCP 服务器使用 GITHUB_PERSONAL_ACCESS_TOKEN 环境变量
export GITHUB_PERSONAL_ACCESS_TOKEN="$GITHUB_TOKEN"

echo "[github-mcp] GitHub MCP 服务启动中..." >&2

exec npx -y @modelcontextprotocol/server-github
