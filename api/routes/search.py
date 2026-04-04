"""
搜索接口
"""
import logging

from fastapi import APIRouter

from api.models.schemas import SearchRequest

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_retriever():
    """延迟初始化混合检索器"""
    from src.vector_store import VectorStore
    from src.knowledge_graph import KnowledgeGraph
    from src.entity_extractor import EntityExtractor
    from src.hybrid_retriever import HybridRetriever

    _vs = VectorStore()
    _kg = KnowledgeGraph()
    _ext = EntityExtractor()
    return HybridRetriever(_vs, _kg, _ext)


def _get_vector_store():
    """延迟初始化向量存储"""
    from src.vector_store import VectorStore

    return VectorStore()


_retriever_instance = None
_vs_instance = None


def _retriever():
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = _get_retriever()
    return _retriever_instance


def _vector_store():
    global _vs_instance
    if _vs_instance is None:
        _vs_instance = _get_vector_store()
    return _vs_instance


@router.post("/hybrid")
async def hybrid_search(request: SearchRequest):
    """混合检索：向量 + 图谱 + 关键词"""
    results = _retriever().retrieve(
        query=request.query,
        top_k=request.top_k,
        vector_weight=request.vector_weight,
        graph_weight=request.graph_weight,
        keyword_weight=request.keyword_weight,
    )
    return {"results": results, "count": len(results)}


@router.post("/vector")
async def vector_search(request: SearchRequest):
    """纯向量检索"""
    results = _vector_store().search(request.query, top_k=request.top_k)
    return {"results": results, "count": len(results)}
