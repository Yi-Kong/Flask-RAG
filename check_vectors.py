"""ChromaDB 向量库查看工具 — 查看分块内容、统计信息、搜索测试.

使用方式:
    python check_vectors.py              默认：概览 + 前 5 个分块 + 按文档统计
    python check_vectors.py overview     仅概览（集合列表、文档数）
    python check_vectors.py show 20      查看前 N 个分块的详细内容
    python check_vectors.py stats        按文档统计分块数量
    python check_vectors.py search       交互式语义搜索

需要先启动 ChromaDB 服务: chroma run --host 127.0.0.1 --port 8000 --path ./chroma_data
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from config import Config

_HOST = Config.CHROMA_HOST
_PORT = Config.CHROMA_PORT
_STRATEGY = getattr(Config, "CHROMA_STORAGE_STRATEGY", "per_document")
_COLLECTION_PREFIX = getattr(Config, "CHROMA_COLLECTION_PREFIX", "doc_")
_LEGACY_COLLECTION = getattr(Config, "CHROMA_COLLECTION", "document_chunks")


def _get_client():
    """获取 ChromaDB HttpClient."""
    import chromadb
    return chromadb.HttpClient(host=_HOST, port=_PORT)


def _is_doc_collection(name: str) -> bool:
    return name.startswith(_COLLECTION_PREFIX)


def overview():
    """列出所有集合及其文档数量."""
    client = _get_client()
    print("=" * 60)
    print("\U0001f4ca ChromaDB 概览（远程模式）")
    print(f"   服务地址: {_HOST}:{_PORT}")
    print(f"   存储策略: {_STRATEGY}")
    print("-" * 60)

    total = 0
    for name in client.list_collections():
        if _STRATEGY == "per_document" and not _is_doc_collection(name):
            continue
        col = client.get_collection(name)
        count = col.count()
        total += count
        print(f"   集合: {name:30s}  分块数: {count}")
    print(f"   {'─' * 50}")
    print(f"   总集合数: {len([name for name in client.list_collections() if _STRATEGY != 'per_document' or _is_doc_collection(name)])}")
    print(f"   总分块数: {total}")
    print("=" * 60)
    return client


def show_chunks_single(col, limit=10):
    """展示单个集合中的分块内容."""
    count = col.count()
    if count == 0:
        print(f"\n⚠️  集合 '{col.name}' 为空\n")
        return

    limit = min(limit, count)
    print(f"\n\U0001f4c4 集合 '{col.name}' 共有 {count} 个分块，展示前 {limit} 个:\n")

    data = col.get(limit=limit, include=["documents", "metadatas"])

    for i, chunk_id in enumerate(data["ids"]):
        meta = data["metadatas"][i]
        text = data["documents"][i]
        print(f"── 分块 {i+1}/{limit} ──")
        print(f"   ID:        {chunk_id}")
        print(f"   分块索引:  {meta.get('chunk_index')}")
        print(f"   标题:      {meta.get('title', '')}")
        print(f"   文件类型:  {meta.get('file_type', '')}")
        print(f"   文本长度:  {len(text)} 字符")
        print(f"   内容:")
        for line in text[:300].split("\n"):
            print(f"     │ {line}")
        if len(text) > 300:
            print(f"     │ ... (还有 {len(text) - 300} 字符)")
        print()


def show_chunks_per_doc(client, limit=10):
    """per_document 模式：展示各文档集合的前几个分块."""
    doc_cols = sorted(
        [(name, client.get_collection(name)) for name in client.list_collections() if _is_doc_collection(name)],
        key=lambda x: x[0],
    )

    if not doc_cols:
        port = os.getenv("FLASK_PORT")
        print(f"\n⚠️  没有找到文档集合，请先在网页 http://127.0.0.1:{port}/upload 上传文档。\n")
        return

    # 展示每个集合的前 2 个分块
    per_col = max(1, limit // max(len(doc_cols), 1))
    for name, col in doc_cols:
        show_chunks_single(col, limit=min(per_col, 2))


def group_by_document_per_doc(client):
    """per_document 模式：按文档统计分块."""
    doc_cols = [(name, client.get_collection(name)) for name in client.list_collections() if _is_doc_collection(name)]

    if not doc_cols:
        print("\n\U0001f4ca 没有找到文档集合")
        return

    print(f"\n\U0001f4ca 按文档统计分块（共 {len(doc_cols)} 个文档）:")
    for name, col in sorted(doc_cols, key=lambda x: x[0]):
        # 获取文档标题
        title = ""
        if col.count() > 0:
            data = col.get(limit=1, include=["metadatas"])
            if data.get("metadatas"):
                title = data["metadatas"][0].get("title", "")
        print(f"   {name}: {col.count():3d} 个分块  [{title}]")


def group_by_document_legacy(col):
    """single_collection 模式：按文档统计分块."""
    count = col.count()
    if count == 0:
        return

    data = col.get(limit=count, include=["metadatas"])
    docs = {}
    for meta in data["metadatas"]:
        doc_id = meta.get("document_id", "?")
        title = meta.get("title", "?")
        if doc_id not in docs:
            docs[doc_id] = {"title": title, "count": 0}
        docs[doc_id]["count"] += 1

    print(f"\n\U0001f4ca 按文档统计分块:")
    for doc_id, info in sorted(docs.items()):
        print(f"   doc#{doc_id}: {info['count']:3d} 个分块  [{info['title']}]")


def search_test_per_doc(client):
    """per_document 模式：在指定文档集合中搜索."""
    doc_cols = sorted(
        [(name, client.get_collection(name)) for name in client.list_collections() if _is_doc_collection(name)],
        key=lambda x: x[0],
    )

    if not doc_cols:
        print("\n⚠️  没有找到文档集合")
        return

    print("\n\U0001f50d 向量搜索测试（per_document 模式）")
    print("   可用文档集合:")
    for name, col in doc_cols:
        print(f"     {name} ({col.count()} 个分块)")

    doc_choice = input("\n   请输入集合名 (如 doc_1，回车搜索全部): ").strip()

    query = input("   请输入搜索关键词: ").strip()
    if not query:
        print("   已跳过。")
        return

    from sentence_transformers import SentenceTransformer
    print("   正在嵌入查询...")
    model = SentenceTransformer(Config.EMBEDDING_MODEL)
    q_emb = model.encode([query], normalize_embeddings=True)[0]

    top_n = int(os.getenv("SEARCH_TOP_N", "3"))

    if doc_choice:
        try:
            col = client.get_collection(name=doc_choice)
            results = col.query(
                query_embeddings=[q_emb.tolist()],
                n_results=min(top_n, col.count()),
            )
            _print_search_results(results, doc_choice)
        except Exception as e:
            print(f"   ❌ 集合 '{doc_choice}' 不存在: {e}")
    else:
        # 搜索所有文档集合（简化版跨文档搜索）
        all_results = []
        for name, col in doc_cols:
            if col.count() == 0:
                continue
            results = col.query(
                query_embeddings=[q_emb.tolist()],
                n_results=min(top_n, col.count()),
            )
            for i, chunk_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i]
                text = results["documents"][0][i]
                dist = results["distances"][0][i]
                all_results.append({
                    "collection": name,
                    "chunk_id": chunk_id,
                    "meta": meta,
                    "text": text,
                    "distance": dist,
                })

        all_results.sort(key=lambda x: x["distance"])
        print(f"\n   Top-{top_n} 搜索结果（跨 {len(doc_cols)} 个文档，查询: '{query}'）:\n")
        for i, r in enumerate(all_results[:top_n]):
            print(f"   #{i+1}  距离: {r['distance']:.4f}  |  "
                  f"{r['collection']}  |  {r['meta'].get('title', '')}  |  "
                  f"{r['text'][:80]}...")


def search_test_legacy(col):
    """single_collection 模式搜索."""
    count = col.count()
    if count == 0:
        return

    from sentence_transformers import SentenceTransformer
    print("\n\U0001f50d 向量搜索测试")
    query = input("   请输入搜索关键词 (回车跳过): ").strip()
    if not query:
        print("   已跳过。")
        return

    print("   正在嵌入查询...")
    model = SentenceTransformer(Config.EMBEDDING_MODEL)
    q_emb = model.encode([query], normalize_embeddings=True)[0]

    top_n = int(os.getenv("SEARCH_TOP_N", "3"))
    results = col.query(query_embeddings=[q_emb.tolist()], n_results=top_n)
    _print_search_results(results, col.name)


def _print_search_results(results, source_name):
    """打印搜索结果."""
    top_n = len(results["ids"][0]) if results.get("ids") and results["ids"][0] else 0
    print(f"\n   Top-{top_n} 搜索结果（集合: '{source_name}'）:\n")
    for i, chunk_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i]
        text = results["documents"][0][i]
        dist = results["distances"][0][i]
        print(f"   #{i+1}  距离: {dist:.4f}  |  "
              f"{meta.get('title', '')}  |  {text[:80]}...")


if __name__ == "__main__":
    sub_cmd = sys.argv[1] if len(sys.argv) > 1 else "overview"

    client = overview()

    if sub_cmd == "show":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        if _STRATEGY == "per_document":
            show_chunks_per_doc(client, limit)
        else:
            try:
                col = client.get_collection(_LEGACY_COLLECTION)
                show_chunks_single(col, limit)
            except Exception:
                print(f"\n⚠️  集合 '{_LEGACY_COLLECTION}' 不存在。请先上传一个文档。\n")
                sys.exit(0)
    elif sub_cmd == "stats":
        if _STRATEGY == "per_document":
            group_by_document_per_doc(client)
        else:
            try:
                col = client.get_collection(_LEGACY_COLLECTION)
                group_by_document_legacy(col)
            except Exception:
                print(f"\n⚠️  集合 '{_LEGACY_COLLECTION}' 不存在。\n")
                sys.exit(0)
    elif sub_cmd == "search":
        if _STRATEGY == "per_document":
            search_test_per_doc(client)
        else:
            try:
                col = client.get_collection(_LEGACY_COLLECTION)
                search_test_legacy(col)
            except Exception:
                print(f"\n⚠️  集合 '{_LEGACY_COLLECTION}' 不存在。\n")
                sys.exit(0)
    else:
        # 默认：展示前 5 个分块 + 按文档统计
        if _STRATEGY == "per_document":
            show_chunks_per_doc(client, limit=5)
            group_by_document_per_doc(client)
        else:
            try:
                col = client.get_collection(_LEGACY_COLLECTION)
                show_chunks_single(col, limit=5)
                group_by_document_legacy(col)
            except Exception:
                print(f"\n⚠️  集合 '{_LEGACY_COLLECTION}' 不存在。请先上传一个文档。\n")
                sys.exit(0)
