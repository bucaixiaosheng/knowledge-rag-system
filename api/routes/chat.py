"""
对话接口
"""
import logging

from fastapi import APIRouter

from api.models.schemas import ChatRequest, ChatResponse

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_rag():
    """延迟初始化RAG对话引擎"""
    from src.pipeline import IngestPipeline
    from src.vector_store import VectorStore
    from src.knowledge_graph import KnowledgeGraph
    from src.entity_extractor import EntityExtractor
    from src.hybrid_retriever import HybridRetriever
    from src.rag_chat import RAGChat

    _vs = VectorStore()
    _kg = KnowledgeGraph()
    _ext = EntityExtractor()
    _retriever = HybridRetriever(_vs, _kg, _ext)
    return RAGChat(_retriever)


# 全局延迟单例
_rag_instance = None


def _rag():
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = _get_rag()
    return _rag_instance


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """对话式知识检索"""
    rag = _rag()
    result = rag.chat(request.query, top_k=request.top_k)
    return result


@router.post("/clear")
async def clear_history():
    """清空对话历史"""
    rag = _rag()
    rag.clear_history()
    return {"status": "ok"}
