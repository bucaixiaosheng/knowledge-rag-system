"""
文档管理接口
POST   /upload     - 文件上传入库
POST   /url        - URL入库
DELETE /{doc_id}   - 删除文档
GET    /stats      - 系统统计
"""
import logging
import os
import tempfile

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.document_loader import DocumentLoader
from src.text_chunker import TextChunker
from src.vector_store import VectorStore
from src.knowledge_graph import KnowledgeGraph
from src.entity_extractor import EntityExtractor
from src.embedding import EmbeddingEngine
from src.config import CHUNK_SIZE, CHUNK_OVERLAP

router = APIRouter()
logger = logging.getLogger(__name__)

# ── 组件单例（懒加载） ──────────────────────────────────────────
_loader: DocumentLoader | None = None
_chunker: TextChunker | None = None


def _get_loader() -> DocumentLoader:
    global _loader
    if _loader is None:
        _loader = DocumentLoader()
    return _loader


def _get_chunker() -> TextChunker:
    global _chunker
    if _chunker is None:
        _chunker = TextChunker(CHUNK_SIZE, CHUNK_OVERLAP)
    return _chunker


# ── 请求/响应模型 ───────────────────────────────────────────────
class IngestURLRequest(BaseModel):
    url: str
    tags: list[str] | None = None


class DocumentResponse(BaseModel):
    status: str
    doc_id: Optional[str] = None
    title: Optional[str] = None
    chunk_count: Optional[int] = None
    anchor_count: Optional[int] = None
    entity_count: Optional[int] = None
    domains: Optional[list[str]] = None
    message: Optional[str] = None


# ── 内部入库逻辑 ────────────────────────────────────────────────
def _ingest_doc(doc: dict, tags: list[str] | None = None) -> dict:
    """
    核心入库流程：解析 → 切块 → 向量化 → 图谱建图
    直接调用各服务模块，不依赖 pipeline.py
    """
    doc_id = doc["doc_id"]
    kg = KnowledgeGraph()

    # 1. 去重
    if kg.document_exists(doc_id):
        return {"status": "skipped", "doc_id": doc_id, "message": "already_exists"}

    # 2. 切块
    chunker = _get_chunker()
    chunks = chunker.chunk_text(
        text=doc["content"],
        doc_id=doc_id,
        metadata={"title": doc["title"], "source": doc["source"]},
    )
    if not chunks:
        return {"status": "error", "doc_id": doc_id, "message": "no_chunks_produced"}

    # 3. 向量化
    vs = VectorStore()
    vs.add_chunks(chunks)

    # 4. LLM 提取实体 / 概念 / 锚关键词
    extractor = EntityExtractor()
    extracted = extractor.extract(doc["content"][:3000])
    entities = extracted.get("entities", [])
    concepts = extracted.get("concepts", [])
    anchor_keywords = extracted.get("anchor_keywords", [])
    summary = extracted.get("summary", doc["content"][:200])

    # 5. 创建文档节点
    from datetime import datetime
    now = datetime.utcnow().isoformat()
    kg.create_document({
        "doc_id": doc_id,
        "title": doc["title"],
        "source": doc["source"],
        "doc_type": doc["doc_type"],
        "content_summary": summary,
        "created_at": now,
        "updated_at": now,
        "chunk_count": len(chunks),
        "metadata": str(doc.get("metadata", {})),
    })

    # 6. 自动分类
    domains = kg.classify_document(doc["title"], doc["content"], doc_id)
    kg.link_document_to_domain(doc_id, domains)

    # 7. 实体 / 概念 / 关系
    if entities:
        kg.create_entities(entities, doc_id)
    if concepts:
        kg.create_concepts(concepts, doc_id)
    relations = extracted.get("relations", [])
    if relations:
        kg.create_relations(relations)

    # 8. 标签
    doc_tags = tags or extracted.get("tags", [])
    if doc_tags:
        kg.add_tags(doc_tags, doc_id)

    # 9. Chunk 节点 + 锚关键词
    all_anchors: list[dict] = []
    for chunk in chunks:
        kg.create_chunk_node(chunk)
        if not anchor_keywords:
            chunk_anchors = extractor.extract_anchor_keywords_only(
                chunk["content"], doc["title"]
            )
        else:
            chunk_anchors = anchor_keywords
        kg.create_anchor_keywords(chunk_anchors, chunk["chunk_id"], doc_id)
        all_anchors.extend(chunk_anchors)

    # 10. 锚关键词 embedding + 相似度建边
    seen: set[str] = set()
    unique_anchors: list[dict] = []
    for ak in all_anchors:
        if ak["keyword"] not in seen:
            seen.add(ak["keyword"])
            unique_anchors.append(ak)

    if unique_anchors:
        emb_engine = EmbeddingEngine()
        kw_texts = [ak["keyword"] for ak in unique_anchors]
        embeddings = emb_engine.embed_texts(kw_texts)
        for ak, emb in zip(unique_anchors, embeddings):
            kg.update_anchor_embeddings(ak["keyword"], emb)
        kg.build_anchor_similarity_edges(threshold=0.5)

    # 11. 跨领域关联
    kg.discover_cross_domain_links()

    logger.info(
        f"✅ 入库完成: {doc_id} | chunks={len(chunks)} | "
        f"anchors={len(unique_anchors)} | entities={len(entities)} | "
        f"domains={domains}"
    )

    return {
        "status": "success",
        "doc_id": doc_id,
        "title": doc["title"],
        "chunk_count": len(chunks),
        "anchor_count": len(unique_anchors),
        "entity_count": len(entities),
        "domains": domains,
    }


# ── API endpoints ───────────────────────────────────────────────

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...)):
    """上传文件并入库"""
    suffix = os.path.splitext(file.filename)[1] if file.filename else ".txt"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        loader = _get_loader()
        doc = loader.load_file(tmp_path)
        result = _ingest_doc(doc)
        return DocumentResponse(**result)
    except Exception as e:
        logger.error(f"上传入库失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)


@router.post("/url", response_model=DocumentResponse)
async def ingest_url(request: IngestURLRequest):
    """URL 内容入库"""
    try:
        loader = _get_loader()
        doc = loader.load_url(request.url)
        result = _ingest_doc(doc, tags=request.tags)
        return DocumentResponse(**result)
    except Exception as e:
        logger.error(f"URL入库失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """删除文档（向量库 + 图谱）"""
    try:
        vs = VectorStore()
        kg = KnowledgeGraph()
        vs.delete_by_doc(doc_id)
        kg.delete_document(doc_id)
        return {"status": "ok", "message": f"文档 {doc_id} 已删除"}
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """系统统计（向量库 + 图谱）"""
    try:
        vs = VectorStore()
        kg = KnowledgeGraph()
        return {
            "vector": {
                "documents": vs.get_doc_count(),
                "chunks": vs.get_chunk_count(),
            },
            "graph": kg.get_stats(),
        }
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
