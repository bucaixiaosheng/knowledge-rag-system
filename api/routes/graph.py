"""
图谱查询接口
POST /search           - 图谱全文搜索
GET  /document/{id}    - 文档图谱
GET  /similar/{id}     - 相似文档
GET  /stats            - 图谱统计
"""
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.knowledge_graph import KnowledgeGraph

router = APIRouter()
logger = logging.getLogger(__name__)

# ── 组件单例 ────────────────────────────────────────────────────
_kg: KnowledgeGraph | None = None


def _get_kg() -> KnowledgeGraph:
    global _kg
    if _kg is None:
        _kg = KnowledgeGraph()
    return _kg


# ── 请求模型 ────────────────────────────────────────────────────
class GraphSearchRequest(BaseModel):
    keyword: str
    limit: int = 10


# ── API endpoints ───────────────────────────────────────────────

@router.post("/search")
async def search_graph(request: GraphSearchRequest):
    """图谱全文搜索"""
    try:
        kg = _get_kg()
        results = kg.search_documents_by_keyword(request.keyword, limit=request.limit)
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"图谱搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/document/{doc_id}")
async def get_document_graph(doc_id: str, depth: int = 2):
    """获取文档的知识图谱（实体、概念、标签及关联）"""
    try:
        kg = _get_kg()
        result = kg.get_document_graph(doc_id, depth=depth)
        if result.get("document") is None:
            raise HTTPException(status_code=404, detail=f"文档 {doc_id} 不存在")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档图谱失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/similar/{doc_id}")
async def find_similar(doc_id: str, limit: int = 5):
    """基于共同实体/概念查找相似文档"""
    try:
        kg = _get_kg()
        results = kg.find_similar_documents(doc_id, limit=limit)
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"查找相似文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def graph_stats():
    """图谱统计（节点数、关系数）"""
    try:
        kg = _get_kg()
        return kg.get_stats()
    except Exception as e:
        logger.error(f"获取图谱统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
