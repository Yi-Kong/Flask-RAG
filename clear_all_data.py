"""清除 MySQL 和 ChromaDB 中的所有数据（保留表结构）.

用法: python clear_all_data.py
"""
import os
import sys
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv

from config import Config

# 加载 .env
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

_COLLECTION_PREFIX = getattr(Config, "CHROMA_COLLECTION_PREFIX", "doc_")
_STRATEGY = getattr(Config, "CHROMA_STORAGE_STRATEGY", "per_document")


def _parse_mysql_conn():
    """从 DATABASE_URL 解析 MySQL 连接参数."""
    url = Config.SQLALCHEMY_DATABASE_URI
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": parsed.port or 3306,
        "user": parsed.username or "root",
        "password": parsed.password or "",
        "database": parsed.path.lstrip("/") or "campus_rag",
        "charset": params.get("charset", ["utf8mb4"])[0],
    }


def clear_mysql():
    """按外键依赖顺序删除 MySQL 所有表中的数据."""
    print("=" * 50)
    print("🔵 清理 MySQL 数据库 (campus_rag)")
    print("=" * 50)

    try:
        import pymysql
    except ImportError:
        print("❌ 请先安装 pymysql: pip install pymysql")
        return False

    conn_info = _parse_mysql_conn()
    print(f"  连接地址: {conn_info['host']}:{conn_info['port']}/{conn_info['database']}")

    conn = pymysql.connect(**conn_info)
    cursor = conn.cursor()

    try:
        # 禁用外键检查，避免删除顺序问题
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

        tables = ["qa_records", "documents", "conversations", "users"]

        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
            count = cursor.fetchone()[0]
            cursor.execute(f"DELETE FROM `{table}`")
            print(f"  ✅ {table}: 删除 {count} 条记录")

        # 重新启用外键检查
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
        print("\n🎉 MySQL 清理完成！所有表数据已清空，表结构保留。")

    except Exception as e:
        conn.rollback()
        print(f"❌ MySQL 清理失败: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

    return True


def clear_chromadb():
    """清除 ChromaDB 中所有文档集合的向量数据."""
    print("\n" + "=" * 50)
    print("🟢 清理 ChromaDB 向量数据库")
    print("=" * 50)

    try:
        import chromadb

        host = Config.CHROMA_HOST
        port = Config.CHROMA_PORT
        print(f"  服务地址: {host}:{port}")
        client = chromadb.HttpClient(host=host, port=port)

        if _STRATEGY == "per_document":
            # ── per_document 模式：遍历删除所有 doc_* 集合 ──
            deleted_count = 0
            for name in client.list_collections():
                if name.startswith(_COLLECTION_PREFIX):
                    col = client.get_collection(name)
                    chunk_count = col.count()
                    client.delete_collection(name=name)
                    print(f"  ✅ 删除集合 '{name}'（{chunk_count} 个分块）")
                    deleted_count += 1

            if deleted_count == 0:
                print("  ℹ️  没有找到文档集合，ChromaDB 已为空")
            print(f"\n🎉 ChromaDB 清理完成！共删除 {deleted_count} 个集合。")

        else:
            # ── single_collection 兼容模式 ──
            collection_name = Config.CHROMA_COLLECTION

            try:
                collection = client.get_collection(name=collection_name)
                count_before = collection.count()
                print(f"  当前向量数量: {count_before}")

                if count_before > 0:
                    collection.delete(where={})
                    print(f"  ✅ 已清空集合 '{collection_name}'（{count_before} 个向量）")
                else:
                    print("  ✅ 向量库已为空，无需清理")

                print(f"\n🎉 ChromaDB 清理完成！集合 {collection_name} 已清空。")

            except Exception as e:
                if "does not exist" in str(e).lower() or "not found" in str(e).lower():
                    print(f"  ℹ️  集合 '{collection_name}' 不存在，无需清理")
                    print("\n🎉 ChromaDB 清理完成！")
                else:
                    raise e

    except Exception as e:
        print(f"❌ ChromaDB 清理失败: {e}")
        print(f"   请确保 ChromaDB 服务已启动: chroma run --host {Config.CHROMA_HOST} --port {Config.CHROMA_PORT} --path ./chroma_data")
        return False

    return True


def main():
    print("\n🚀 开始清理项目所有数据...\n")
    print("⚠️  警告: 此操作将删除所有数据且不可恢复！")
    print("    - MySQL 表: users, documents, conversations, qa_records")
    if _STRATEGY == "per_document":
        print(f"    - ChromaDB: 所有 '{_COLLECTION_PREFIX}*' 集合")
    else:
        print(f"    - ChromaDB: 集合 '{Config.CHROMA_COLLECTION}'")
    print("    - 表结构和集合结构将被保留\n")

    confirm = input("请输入 'yes' 确认操作: ")
    if confirm.strip().lower() != "yes":
        print("❌ 操作已取消")
        sys.exit(0)

    success = True
    success = clear_mysql() and success
    success = clear_chromadb() and success

    if success:
        print("\n" + "=" * 50)
        print("✅ 所有数据清理完成！")
        print("=" * 50)
    else:
        print("\n⚠️  部分清理失败，请检查错误信息")
        sys.exit(1)


if __name__ == "__main__":
    main()
