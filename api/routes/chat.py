"""
对话接口：RAG 对话式知识检索

Endpoints:
  POST /        — 对话检索（RAGChat.chat）
  POST /clear   — 清空对话历史
"""
import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.entity_extractor import EntityExtractor
from src.hybrid_retriever import HybridRetriever
from src.knowledge_graph import KnowledgeGraph
from src.rag_chat import RAGChat
from src.reranker import Reranker
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
_reranker = Reranker()
_rag = RAGChat(retriever=_retriever, reranker=_reranker)


# ---------------------------------------------------------------------------
# Request / Response 模型
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """对话请求"""
    query: str = Field(..., min_length=1, description="用户查询")
    top_k: int = Field(default=5, ge=1, le=50, description="检索结果数量")


class ChatResponse(BaseModel):
    """对话响应"""
    answer: str
    sources: list[dict]
    context_count: int


class ClearResponse(BaseModel):
    """清空历史响应"""
    status: str
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """对话式知识检索（完整 RAG 流程：检索 → 重排 → LLM 生成）"""
    logger.info("对话请求: query=%r, top_k=%d", request.query, request.top_k)
    result = _rag.chat(request.query, top_k=request.top_k)
    return ChatResponse(**result)


@router.post("/clear", response_model=ClearResponse)
async def clear_history():
    """清空对话历史"""
    _rag.clear_history()
    logger.info("对话历史已清空")
    return ClearResponse(status="ok", message="对话历史已清空")
