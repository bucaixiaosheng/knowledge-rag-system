"""
文档管理接口
"""
import logging
import os
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile

from api.models.schemas import DocumentUploadResponse, IngestURLRequest

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_pipeline():
    """延迟初始化入库流水线"""
    from src.pipeline import IngestPipeline

    return IngestPipeline()


_pipeline_instance = None


def _pipeline():
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = _get_pipeline()
    return _pipeline_instance


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """上传文档入库"""
    suffix = os.path.splitext(file.filename)[1] if file.filename else ".txt"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        content = await file.read()
        f.write(content)
        tmp_path = f.name

    try:
        result = _pipeline().ingest_file(tmp_path)
        return DocumentUploadResponse(
            status=result.get("status", "unknown"),
            doc_id=result.get("doc_id"),
            title=result.get("title"),
            chunk_count=result.get("chunk_count"),
        )
    except Exception as e:
        logger.error(f"上传失败: {e}")
        raise HTTPException(500, str(e))
    finally:
        os.unlink(tmp_path)


@router.post("/url", response_model=DocumentUploadResponse)
async def ingest_url(request: IngestURLRequest):
    """URL入库"""
    try:
        result = _pipeline().ingest_url(request.url, tags=request.tags)
        return DocumentUploadResponse(
            status=result.get("status", "unknown"),
            doc_id=result.get("doc_id"),
            title=result.get("title"),
        )
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """删除文档"""
    _pipeline().delete_document(doc_id)
    return {"status": "ok", "message": f"文档 {doc_id} 已删除"}


@router.get("/stats")
async def get_stats():
    """获取系统统计"""
    from src.vector_store import VectorStore
    from src.knowledge_graph import KnowledgeGraph

    vs = VectorStore()
    kg = KnowledgeGraph()
    return {
        "vector": {
            "documents": vs.get_doc_count(),
            "chunks": vs.get_chunk_count(),
        },
        "graph": kg.get_stats(),
    }
