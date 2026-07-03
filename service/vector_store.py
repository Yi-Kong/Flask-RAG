"""ChromaDB 向量存储服务 — HttpClient 客户端-服务器模式.

使用方式：
    需先启动 ChromaDB 服务: chroma run --host 127.0.0.1 --port 8000 --path ./chroma_data

存储策略（通过 CHROMA_STORAGE_STRATEGY 配置）:
  - "single_collection": 所有文档存入单个集合（旧方案，通过 metadata.document_id 区分）
  - "per_document":      每文档创建一个独立集合，集合名格式 {prefix}{document_id}

距离度量: cosine（配合 L2 归一化嵌入向量）
"""
import logging
from typing import Any, Dict, List, Optional

import numpy as np

from config import Config
from exceptions import ServiceException

logger = logging.getLogger(__name__)

# ── 从 Config 读取配置 ──────────────────────────────────────────────
_HOST = Config.CHROMA_HOST
_PORT = Config.CHROMA_PORT
_STRATEGY = getattr(Config, "CHROMA_STORAGE_STRATEGY", "per_document")
_COLLECTION_PREFIX = getattr(Config, "CHROMA_COLLECTION_PREFIX", "doc_")
_LEGACY_COLLECTION = getattr(Config, "CHROMA_COLLECTION", "document_chunks")

# 全局客户端实例（惰性加载）
_client: Any = None


# ── 集合命名工具 ────────────────────────────────────────────────────

def _doc_collection_name(document_id: int) -> str:
    """生成文档专属集合名，如 ``doc_3``."""
    return f"{_COLLECTION_PREFIX}{document_id}"


def _is_doc_collection(name: str) -> bool:
    """判断集合名是否属于文档集合."""
    return name.startswith(_COLLECTION_PREFIX)


def _parse_doc_id(name: str) -> Optional[int]:
    """从集合名解析文档 ID."""
    if not name.startswith(_COLLECTION_PREFIX):
        return None
    try:
        return int(name[len(_COLLECTION_PREFIX):])
    except ValueError:
        return None


# ── 客户端管理 ──────────────────────────────────────────────────────

def get_client_service():
    """返回全局 ChromaDB HttpClient 实例（客户端-服务器模式）."""
    global _client
    if _client is None:
        import chromadb

        host_port = f"{_HOST}:{_PORT}"
        logger.info("正在连接 ChromaDB（远程模式）: %s", host_port)
        _client = chromadb.HttpClient(host=_HOST, port=_PORT)

    return _client


def _get_doc_collection(client, document_id: int):
    """获取或创建文档专属集合（per_document 模式）."""
    col_name = _doc_collection_name(document_id)
    try:
        return client.get_collection(name=col_name)
    except Exception:
        collection = client.create_collection(
            name=col_name,
            metadata={"hnsw:space": "cosine", "document_id": document_id},
        )
        logger.info("ChromaDB 集合已创建: %s (文档 id=%d)", col_name, document_id)
        return collection


def _get_legacy_collection():
    """获取旧版单集合（single_collection 模式兼容）."""
    client = get_client_service()
    try:
        return client.get_collection(name=_LEGACY_COLLECTION)
    except Exception:
        collection = client.create_collection(
            name=_LEGACY_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("ChromaDB 集合已创建: %s", _LEGACY_COLLECTION)
        return collection


# ── 核心 CRUD ───────────────────────────────────────────────────────

def add_chunks_service(
    document_id: int,
    chunks: List[Dict],
    embeddings: np.ndarray,
    title: str = "",
    file_type: str = "",
) -> int:
    """将分块及其向量嵌入存入该文档的专属集合.

    Args:
        document_id: 数据库中的文档 ID.
        chunks: chunk_text() 返回的分块列表.
        embeddings: embed_texts() 返回的向量数组，shape (N, dim).
        title: 文档标题（存入元数据）.
        file_type: 文件类型（存入元数据）.

    Returns:
        成功存储的分块数量.
    """
    if not chunks:
        logger.warning("add_chunks: 分块列表为空")
        return 0

    client = get_client_service()

    if _STRATEGY == "per_document":
        collection = _get_doc_collection(client, document_id)
    else:
        collection = _get_legacy_collection()

    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[Dict] = []

    for chunk in chunks:
        chunk_index = chunk["index"]

        if _STRATEGY == "per_document":
            ids.append(str(chunk_index))
            metadatas.append({
                "chunk_index": chunk_index,
                "title": title,
                "file_type": file_type,
            })
        else:
            ids.append(f"{document_id}_{chunk_index}")
            metadatas.append({
                "document_id": document_id,
                "chunk_index": chunk_index,
                "title": title,
                "file_type": file_type,
            })

        documents.append(chunk["text"])

    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings.tolist(),
        metadatas=metadatas,
    )

    logger.info(
        "ChromaDB 存储完成：文档 '%s' (id=%d) → %d 个分块（策略=%s）",
        title, document_id, len(ids), _STRATEGY,
    )
    return len(ids)


def search_service(
    query_embedding: np.ndarray,
    top_k: int,
    document_id: Optional[int] = None,
) -> List[Dict]:
    """在向量库中搜索最相似的 Top-K 个分块.

    Args:
        query_embedding: 查询文本的嵌入向量，shape (dim,).
        top_k: 返回结果数量.
        document_id: 可选，限定检索范围到指定文档.

    Returns:
        搜索结果列表，每项包含:
            - id: chunk ID
            - document_id: 所属文档 ID
            - chunk_index: 分块序号
            - text: 分块文本
            - score: 余弦相似度
            - title: 文档标题
            - file_type: 文件类型
    """
    client = get_client_service()

    if _STRATEGY == "per_document":
        if document_id is not None:
            return _search_in_doc_collection(client, query_embedding, top_k, document_id)
        else:
            return _search_all_doc_collections(client, query_embedding, top_k)
    else:
        return _search_in_legacy_collection(query_embedding, top_k, document_id)


def _search_in_doc_collection(
    client, query_embedding: np.ndarray, top_k: int, document_id: int
) -> List[Dict]:
    """在指定文档的专属集合中搜索."""
    collection = _get_doc_collection(client, document_id)
    count = collection.count()
    if count == 0:
        return []

    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=min(top_k, count),
    )
    return _format_results(results, document_id)


def _search_all_doc_collections(
    client, query_embedding: np.ndarray, top_k: int
) -> List[Dict]:
    """跨所有文档集合搜索，合并排序后返回 Top-K 结果.

    遍历每个文档专属 Collection，分别查询 top_k 条结果，
    按余弦距离升序合并排序，取全局 Top-K。
    """
    all_results: List[Dict] = []

    for name in client.list_collections():
        if not _is_doc_collection(name):
            continue
        doc_id = _parse_doc_id(name)
        if doc_id is None:
            continue

        try:
            collection = client.get_collection(name=name)
        except Exception:
            continue

        count = collection.count()
        if count == 0:
            continue

        results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=min(top_k, count),
        )
        formatted = _format_results(results, doc_id)
        all_results.extend(formatted)

    # 按余弦距离升序排序（距离越小越相似）
    all_results.sort(key=lambda x: x.get("score", float("inf")))

    top_results = all_results[:top_k]
    logger.info(
        "跨文档搜索完成：扫描 %d 个文档集合，命中 %d 条，返回 top_%d=%d",
        len([n for n in client.list_collections() if _is_doc_collection(n)]),
        len(all_results),
        top_k,
        len(top_results),
    )
    return top_results


def _search_in_legacy_collection(
    query_embedding: np.ndarray, top_k: int, document_id: Optional[int]
) -> List[Dict]:
    """在旧版单集合中搜索（single_collection 兼容）."""
    collection = _get_legacy_collection()
    where_filter = {"document_id": document_id} if document_id is not None else None

    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=min(top_k, collection.count()),
        where=where_filter,
    )
    return _format_results(results, document_id)


def _format_results(results: dict, default_doc_id: Optional[int] = None) -> List[Dict]:
    """将 ChromaDB query 结果格式化为统一列表."""
    formatted: List[Dict] = []
    if not results.get("ids") or not results["ids"][0]:
        return formatted

    for i, chunk_id in enumerate(results["ids"][0]):
        metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
        formatted.append({
            "id": chunk_id,
            "document_id": metadata.get("document_id", default_doc_id),
            "chunk_index": metadata.get("chunk_index"),
            "text": results["documents"][0][i] if results.get("documents") else "",
            "score": results["distances"][0][i] if results.get("distances") else 0.0,
            "title": metadata.get("title", ""),
            "file_type": metadata.get("file_type", ""),
        })

    logger.info("ChromaDB 搜索完成：top_k 命中=%d", len(formatted))
    return formatted


def delete_document_service(document_id: int) -> int:
    """删除指定文档在 ChromaDB 中的所有分块.

    Args:
        document_id: 数据库中的文档 ID.

    Returns:
        删除的分块数量.
    """
    client = get_client_service()

    if _STRATEGY == "per_document":
        col_name = _doc_collection_name(document_id)
        try:
            collection = client.get_collection(name=col_name)
            count = collection.count()
            client.delete_collection(name=col_name)
            logger.info(
                "ChromaDB 清理完成：文档 id=%d → 删除集合 '%s'（%d 个分块）",
                document_id, col_name, count,
            )
            return count
        except Exception:
            logger.info("ChromaDB 清理：文档 id=%d 的集合 '%s' 不存在", document_id, col_name)
            return 0
    else:
        collection = _get_legacy_collection()
        collection.delete(where={"document_id": document_id})
        logger.info("ChromaDB 清理完成：文档 id=%d（旧方案 where 删除）", document_id)
        return 0


def get_document_count(document_id: int) -> int:
    """获取指定文档在 ChromaDB 中的分块数量.

    Args:
        document_id: 数据库中的文档 ID.

    Returns:
        分块数量.
    """
    client = get_client_service()

    if _STRATEGY == "per_document":
        try:
            collection = client.get_collection(name=_doc_collection_name(document_id))
            return collection.count()
        except Exception:
            return 0
    else:
        collection = _get_legacy_collection()
        existing = collection.get(where={"document_id": document_id})
        return len(existing["ids"]) if existing and existing["ids"] else 0


# ── 管理后台方法 ──────────────────────────────────────────────────


def collections_overview_service() -> dict:
    """获取 ChromaDB 所有 Collection 概览.

    Returns:
        dict: {host, port, collections: [{name, count, document_id}], total_chunks}.
    """
    client = get_client_service()
    collections_info = []
    total_chunks = 0

    for name in client.list_collections():
        col = client.get_collection(name)
        count = col.count()

        if _STRATEGY == "per_document":
            if not _is_doc_collection(name):
                continue
            doc_id = _parse_doc_id(name)
            collections_info.append({
                "name": name,
                "count": count,
                "document_id": doc_id,
            })
        else:
            collections_info.append({
                "name": name,
                "count": count,
            })

        total_chunks += count

    return {
        "host": f"{_HOST}:{_PORT}",
        "collections": collections_info,
        "total_chunks": total_chunks,
    }


def chunks_paginated_service(
    page: int = 1,
    page_size: int = 20,
    document_id: int | None = None,
) -> dict:
    """分页获取 ChromaDB 中的分块列表（含文档统计）.

    Args:
        page: 页码.
        page_size: 每页数量.
        document_id: 按文档筛选（可选）.

    Returns:
        dict: {total, page, page_size, total_pages, chunks, doc_stats}.
    """
    client = get_client_service()

    if _STRATEGY == "per_document":
        return _chunks_paginated_per_doc(client, page, page_size, document_id)
    else:
        return _chunks_paginated_legacy(page, page_size, document_id)


def _chunks_paginated_per_doc(
    client, page: int, page_size: int, document_id: int | None
) -> dict:
    """per_document 模式的分页浏览."""
    # ── 构建文档统计 ──
    doc_stats = []
    doc_collections = []

    for name in client.list_collections():
        if not _is_doc_collection(name):
            continue
        doc_id = _parse_doc_id(name)
        col = client.get_collection(name)
        count = col.count()
        if doc_id is not None:
            doc_stats.append({
                "document_id": doc_id,
                "title": "",
                "file_type": "",
                "count": count,
            })
            doc_collections.append((doc_id, col))

    doc_stats.sort(key=lambda x: x["document_id"])
    doc_collections.sort(key=lambda x: x[0])

    total = sum(d["count"] for d in doc_stats)

    if total == 0:
        return {
            "total": 0, "page": 1, "page_size": page_size,
            "total_pages": 0, "chunks": [], "doc_stats": doc_stats,
        }

    # ── 单文档模式 ──
    if document_id is not None:
        try:
            collection = client.get_collection(name=_doc_collection_name(document_id))
        except Exception:
            return {
                "total": 0, "page": 1, "page_size": page_size,
                "total_pages": 0, "chunks": [], "doc_stats": doc_stats,
            }

        doc_total = collection.count()
        offset = (page - 1) * page_size
        data = collection.get(
            offset=offset,
            limit=page_size,
            include=["documents", "metadatas"],
        )

        chunks = _build_chunk_list(data, document_id)
        return {
            "total": doc_total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (doc_total + page_size - 1) // page_size),
            "chunks": chunks,
            "doc_stats": doc_stats,
        }

    # ── 全局模式：跨集合聚合分页 ──
    offset = (page - 1) * page_size
    skipped = 0
    chunks = []

    for doc_id, col in doc_collections:
        col_count = col.count()
        if col_count == 0:
            continue

        if skipped + col_count <= offset:
            skipped += col_count
            continue

        local_offset = max(0, offset - skipped)
        local_limit = min(page_size - len(chunks), col_count - local_offset)

        if local_limit > 0:
            data = col.get(
                offset=local_offset,
                limit=local_limit,
                include=["documents", "metadatas"],
            )
            chunks.extend(_build_chunk_list(data, doc_id))

        skipped += col_count
        if len(chunks) >= page_size:
            break

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "chunks": chunks,
        "doc_stats": doc_stats,
    }


def _chunks_paginated_legacy(
    page: int, page_size: int, document_id: int | None
) -> dict:
    """single_collection 模式的分页浏览."""
    collection = _get_legacy_collection()
    total = collection.count()

    if total == 0:
        return {
            "total": 0, "page": 1, "page_size": page_size,
            "total_pages": 0, "chunks": [], "doc_stats": [],
        }

    all_meta = collection.get(include=["metadatas"])
    doc_map: dict = {}
    for meta in all_meta["metadatas"]:
        did = meta.get("document_id", "?")
        if did not in doc_map:
            doc_map[did] = {
                "document_id": did,
                "title": meta.get("title", ""),
                "file_type": meta.get("file_type", ""),
                "count": 0,
            }
        doc_map[did]["count"] += 1

    doc_stats = sorted(doc_map.values(), key=lambda x: x["document_id"])

    where_filter = {"document_id": document_id} if document_id else None
    offset = (page - 1) * page_size
    data = collection.get(
        offset=offset,
        limit=page_size,
        where=where_filter,
        include=["documents", "metadatas"],
    )

    chunks = _build_chunk_list(data, document_id)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "chunks": chunks,
        "doc_stats": doc_stats,
    }


def _build_chunk_list(data: dict, default_doc_id: Optional[int] = None) -> List[Dict]:
    """从 ChromaDB get 结果构建 chunk 列表."""
    chunks = []
    for i, chunk_id in enumerate(data.get("ids", [])):
        meta = data["metadatas"][i] if data.get("metadatas") else {}
        text = data["documents"][i] if data.get("documents") else ""
        chunks.append({
            "id": chunk_id,
            "document_id": meta.get("document_id", default_doc_id),
            "chunk_index": meta.get("chunk_index"),
            "title": meta.get("title", ""),
            "file_type": meta.get("file_type", ""),
            "text": text,
            "char_count": len(text),
        })
    return chunks


def search_similar_service(
    query_text: str,
    top_k: int = 5,
    document_id: Optional[int] = None,
) -> dict:
    """语义搜索：嵌入查询文本并返回相似分块.

    Args:
        query_text: 搜索关键词.
        top_k: 返回结果数量.
        document_id: 限定检索的文档 ID（可选）.

    Returns:
        dict: {query, results: [{..., similarity}]}.

    Raises:
        ServiceException: 嵌入或搜索失败.
    """
    from service.embedder import embed_query_service

    if not query_text.strip():
        return {"query": query_text, "results": []}

    try:
        q_emb = embed_query_service(query_text)
        results = search_service(q_emb, top_k=top_k, document_id=document_id)
    except Exception as e:
        logger.error("语义搜索失败: %s", e)
        raise ServiceException(f"搜索失败: {str(e)}")

    for r in results:
        r["similarity"] = round(1.0 - r["score"], 4)

    return {"query": query_text, "results": results}
