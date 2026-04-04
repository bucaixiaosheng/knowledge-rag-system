# api/models/schemas.py
"""Pydantic数据模型：API请求/响应Schema"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---- 对话相关 ----


class ChatRequest(BaseModel):
    """对话请求"""

    query: str = Field(..., description="用户查询")
    top_k: int = Field(default=5, description="返回结果数量")


class SourceInfo(BaseModel):
    """来源信息"""

    doc_id: str
    title: str = ""
    score: float = 0.0


class ChatResponse(BaseModel):
    """对话响应"""

    answer: str
    sources: list[dict] = Field(default_factory=list)
    context_count: int = 0


# ---- 文档入库相关 ----


class IngestURLRequest(BaseModel):
    """URL入库请求"""

    url: str = Field(..., description="文档URL")
    tags: list[str] | None = Field(default=None, description="标签列表")


class IngestResponse(BaseModel):
    """文档入库响应"""

    status: str
    doc_id: Optional[str] = None
    title: Optional[str] = None
    chunk_count: Optional[int] = None
    entity_count: Optional[int] = None
    anchor_count: Optional[int] = None
    domains: list[str] = Field(default_factory=list)
    error: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""

    status: str
    doc_id: Optional[str] = None
    title: Optional[str] = None
    chunk_count: Optional[int] = None
    message: Optional[str] = None


# ---- 搜索相关 ----


class SearchRequest(BaseModel):
    """搜索请求"""

    query: str = Field(..., description="搜索查询")
    top_k: int = Field(default=10, description="返回结果数量")
    vector_weight: float = Field(default=0.5, description="向量检索权重")
    graph_weight: float = Field(default=0.3, description="图谱检索权重")
    keyword_weight: float = Field(default=0.2, description="关键词检索权重")


class SearchResultItem(BaseModel):
    """单条搜索结果"""

    chunk_id: str
    content: str
    doc_id: str
    score: float
    source: str = ""
    metadata: dict = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """搜索响应"""

    results: list[dict] = Field(default_factory=list)
    count: int = 0


# ---- 图谱相关 ----


class GraphQuery(BaseModel):
    """图谱查询请求"""

    keyword: str = Field(..., description="搜索关键词")
    limit: int = Field(default=10, description="返回结果数量")


class GraphStats(BaseModel):
    """图谱统计"""

    document_count: int = 0
    entity_count: int = 0
    concept_count: int = 0
    tag_count: int = 0
    relation_count: int = 0


# ---- 系统统计 ----


class VectorStats(BaseModel):
    """向量库统计"""

    documents: int = 0
    chunks: int = 0


class SystemStats(BaseModel):
    """系统统计"""

    vector: VectorStats = Field(default_factory=VectorStats)
    graph: dict = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
