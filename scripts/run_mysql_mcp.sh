#!/bin/bash
# ============================================================
# MySQL MCP Server 启动脚本
# 从项目根目录 .env 中读取 DATABASE_URL，解析后启动 MCP 服务
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

# 检查 DATABASE_URL 是否已设置
if [ -z "$DATABASE_URL" ]; then
    echo "[mysql-mcp] 错误: .env 中未找到 DATABASE_URL" >&2
    exit 1
fi

# 解析 DATABASE_URL 格式: mysql+pymysql://user:password@host:port/database?params
# 移除协议前缀 mysql+pymysql://
DB_URL="${DATABASE_URL#mysql+pymysql://}"
DB_URL="${DB_URL#mysql://}"

# 提取 user:password@host:port/database
DB_USER_PASS="${DB_URL%%@*}"
DB_HOST_PORT_DB="${DB_URL#*@}"

# 移除 ? 后的参数
DB_HOST_PORT_DB="${DB_HOST_PORT_DB%%\?*}"

export MYSQL_USER="${DB_USER_PASS%%:*}"
export MYSQL_PASSWORD="${DB_USER_PASS#*:}"

# 解析 host:port/database
DB_HOST_PORT="${DB_HOST_PORT_DB%/*}"
export MYSQL_DATABASE="${DB_HOST_PORT_DB##*/}"

# host 和 port
if [[ "$DB_HOST_PORT" == *:* ]]; then
    export MYSQL_HOST="${DB_HOST_PORT%:*}"
    export MYSQL_PORT="${DB_HOST_PORT##*:}"
else
    export MYSQL_HOST="$DB_HOST_PORT"
    export MYSQL_PORT="3306"
fi

echo "[mysql-mcp] 连接 $MYSQL_USER@$MYSQL_HOST:$MYSQL_PORT/$MYSQL_DATABASE" >&2

exec npx -y @benborla29/mcp-server-mysql
