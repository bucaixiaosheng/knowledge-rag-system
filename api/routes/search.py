"""
搜索接口：混合检索 & 纯向量检索

Endpoints:
  POST /hybrid   — 混合检索（HybridRetriever：向量 + 图谱 + BM25）
  POST /vector   — 纯向量检索（VectorStore）
"""
import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.entity_extractor import EntityExtractor
from src.hybrid_retriever import HybridRetriever
from src.knowledge_graph import KnowledgeGraph
from src.vector_store import VectorStore

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# 组件初始化（模块级单例，整个路由共享）
# ---------------------------------------------------------------------------
_vs = VectorStore()
_kg = KnowledgeGraph()
_ext = EntityExtractor()
_retriever = HybridRetriever(_vs, _kg, _ext)


# ---------------------------------------------------------------------------
# Request / Response 模型
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., min_length=1, description="搜索查询文本")
    top_k: int = Field(default=10, ge=1, le=100, description="返回结果数量")
    vector_weight: float = Field(default=0.4, ge=0.0, le=1.0, description="向量检索权重")
    graph_weight: float = Field(default=0.35, ge=0.0, le=1.0, description="图谱检索权重")
    keyword_weight: float = Field(default=0.25, ge=0.0, le=1.0, description="关键词检索权重")


class VectorSearchRequest(BaseModel):
    """纯向量搜索请求"""
    query: str = Field(..., min_length=1, description="搜索查询文本")
    top_k: int = Field(default=10, ge=1, le=100, description="返回结果数量")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/hybrid")
async def hybrid_search(request: SearchRequest):
    """混合检索：向量 + 图谱 + BM25 三路加权融合"""
    logger.info(
        "混合检索: query=%r, top_k=%d, weights=(%.2f, %.2f, %.2f)",
        request.query, request.top_k,
        request.vector_weight, request.graph_weight, request.keyword_weight,
    )
    results = _retriever.retrieve(
        query=request.query,
        top_k=request.top_k,
        vector_weight=request.vector_weight,
        graph_weight=request.graph_weight,
        keyword_weight=request.keyword_weight,
    )
    return {"results": results, "count": len(results)}


@router.post("/vector")
async def vector_search(request: VectorSearchRequest):
    """纯向量检索：ChromaDB 语义搜索"""
    logger.info("向量检索: query=%r, top_k=%d", request.query, request.top_k)
    results = _vs.search(request.query, top_k=request.top_k)
    return {"results": results, "count": len(results)}
