# 本地RAG + Neo4j 知识管理系统

基于本地向量检索（ChromaDB）和知识图谱（Neo4j）的混合RAG知识管理系统。

## 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 向量数据库 | ChromaDB | 轻量级本地向量存储 |
| 图数据库 | Neo4j Community | 知识图谱存储与查询 |
| Web框架 | FastAPI | 异步REST API |
| Embedding | sentence-transformers (all-MiniLM-L6-v2) | 本地向量化 |
| LLM | 智谱GLM-5 | 文档理解与对话生成 |
| 文档解析 | PyMuPDF, BeautifulSoup, markdown | PDF/HTML/MD多格式支持 |

## 目录结构

```
knowledge-rag-system/
├── .env                  # 环境变量配置
├── requirements.txt      # Python依赖
├── docker-compose.yml    # 容器编排
├── src/                  # 核心代码
├── api/                  # FastAPI接口层
│   ├── routes/           # 路由模块
│   └── models/           # 数据模型
├── scripts/              # 工具脚本
├── web/                  # 前端界面
├── docs/                 # 待入库文档
│   ├── pdf/
│   ├── html/
│   ├── markdown/
│   └── urls.txt
├── neo4j/                # Neo4j配置与数据
├── chroma/               # ChromaDB数据
├── logs/                 # 日志
└── tests/                # 测试
```

## 快速启动

### 1. 启动基础设施

```bash
docker compose up -d    # 启动 Neo4j + ChromaDB
```

### 2. 安装依赖

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 配置环境变量

编辑 `.env` 文件，填入你的智谱API Key：

```
LLM_API_KEY=你的智谱API_KEY
```

### 4. 初始化系统

```bash
python scripts/init_system.py
```

### 5. 启动API服务

```bash
uvicorn api.main:app --port 8100 --reload
```

### 6. 添加文档

```bash
python scripts/add_document.py ./docs/markdown/example.md
python scripts/add_document.py --url https://example.com/article
```

## API端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat/` | 对话式知识检索 |
| POST | `/api/v1/documents/upload` | 上传文档入库 |
| POST | `/api/v1/documents/url` | URL入库 |
| POST | `/api/v1/search/hybrid` | 混合检索 |
| POST | `/api/v1/graph/search` | 图谱搜索 |
| GET  | `/api/v1/health` | 健康检查 |
