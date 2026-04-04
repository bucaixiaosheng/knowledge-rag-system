# Knowledge RAG System

本地RAG + Neo4j知识管理系统

## 技术栈

- **向量数据库**: ChromaDB (Docker)
- **图数据库**: Neo4j Community 5.x (Docker)
- **Web框架**: FastAPI
- **Embedding**: sentence-transformers/all-MiniLM-L6-v2 (本地)
- **LLM**: 智谱GLM-5 (OpenAI SDK兼容)

## 快速开始

```bash
# 1. 启动基础设施
docker compose up -d

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env  # 编辑填入LLM_API_KEY

# 4. 启动API服务
uvicorn api.main:app --port 8100 --reload
```

## 端口

| 服务 | 端口 |
|------|------|
| API | 8100 |
| Neo4j Browser | 7474 |
| Neo4j Bolt | 7687 |
| ChromaDB | 8300 |

## API文档

启动后访问: http://localhost:8100/docs
