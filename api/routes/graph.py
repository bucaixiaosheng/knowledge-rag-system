"""
图谱查询接口
"""
import logging

from fastapi import APIRouter

from api.models.schemas import GraphQuery

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_kg():
    """延迟初始化知识图谱"""
    from src.knowledge_graph import KnowledgeGraph

    return KnowledgeGraph()


_kg_instance = None


def _kg():
    global _kg_instance
    if _kg_instance is None:
        _kg_instance = _get_kg()
    return _kg_instance


@router.post("/search")
async def search_graph(query: GraphQuery):
    """全文搜索图谱"""
    results = _kg().search_documents_by_keyword(query.keyword, limit=query.limit)
    return {"results": results, "count": len(results)}


@router.get("/document/{doc_id}")
async def get_document_graph(doc_id: str, depth: int = 2):
    """获取文档的知识图谱"""
    result = _kg().get_document_graph(doc_id, depth=depth)
    return result


@router.get("/similar/{doc_id}")
async def find_similar(doc_id: str, limit: int = 5):
    """查找相似文档"""
    results = _kg().find_similar_documents(doc_id, limit=limit)
    return {"results": results}


@router.get("/stats")
async def graph_stats():
    """图谱统计"""
    return _kg().get_stats()
