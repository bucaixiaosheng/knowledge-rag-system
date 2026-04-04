"""
FastAPI应用入口
知识管理系统 API - 本地RAG + Neo4j知识图谱检索系统
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import chat, documents, graph, search

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="知识管理系统 API",
    description="本地RAG + Neo4j知识图谱检索系统",
    version="1.0.0",
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router, prefix="/api/v1/chat", tags=["对话"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["文档"])
app.include_router(graph.router, prefix="/api/v1/graph", tags=["图谱"])
app.include_router(search.router, prefix="/api/v1/search", tags=["搜索"])


@app.get("/api/v1/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "knowledge-rag-system"}
