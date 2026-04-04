# 📚 Knowledge RAG System — 本地 RAG + Neo4j 知识管理系统

> 基于**混合检索（向量 + 知识图谱 + 关键词）**的本地知识管理系统，支持 PDF/HTML/Markdown/URL/微信公众号多格式文档入库，提供对话式 RAG 问答、图谱可视化查询和 CLI 工具。

---

## ✨ 功能特性

- **🧠 混合检索引擎**：向量语义检索（ChromaDB）+ 知识图谱检索（Neo4j）+ 关键词检索（BM25）三路融合，加权重排序
- **🕸️ 层级化知识图谱**：KnowledgeRoot → Domain → SubDomain → Document → Chunk → AnchorKeyword，支持跨领域知识自动关联
- **🔗 锚关键词机制**：自动提取文档核心关键词，通过语义相似度建立跨文档、跨领域的知识桥接
- **📄 多格式文档支持**：PDF / HTML / Markdown / 纯文本 / URL 爬取 / 微信公众号文章
- **🤖 RAG 对话问答**：基于检索上下文的智能问答，支持多轮对话
- **🏷️ 自动学科分类**：LLM + 关键词匹配自动将文档归入学科领域，支持多学科交叉
- **📊 实体与概念抽取**：LLM 自动提取实体、概念、关系，构建丰富知识图谱
- **⏰ 定时自动入库**：APScheduler 定时扫描文档目录和 URL 列表，增量入库
- **🖥️ Web 前端界面**：对话检索 / 混合搜索 / 图谱查询 / 文档管理四个面板
- **🔧 CLI 工具**：命令行添加/删除文档、查看统计
- **🐳 Docker Compose 部署**：一键启动 Neo4j + ChromaDB 基础设施
- **⚙️ systemd 服务**：生产环境 systemd 部署配置

---

## 🛠️ 技术栈

| 组件 | 技术选型 | 版本 | 说明 |
|------|---------|------|------|
| 向量数据库 | ChromaDB | 0.5.x | 轻量级，支持本地持久化，余弦相似度 |
| 图数据库 | Neo4j Community | 5.x | 免费版，Docker 部署，支持 APOC 插件 |
| Web 框架 | FastAPI | 0.115+ | 异步 REST API，自动 OpenAPI 文档 |
| Embedding | sentence-transformers | 3.x | `all-MiniLM-L6-v2` 本地推理，384 维向量 |
| LLM | 智谱 GLM-5 | - | OpenAI SDK 兼容，用于实体抽取和 RAG 生成 |
| 文档解析 | PyMuPDF, BeautifulSoup, markdown | - | PDF / HTML / MD 多格式解析 |
| 中文分词 | jieba | - | BM25 关键词检索 |
| 任务调度 | APScheduler | 3.x | 定时扫描入库 |
| 容器编排 | Docker Compose | v2 | Neo4j + ChromaDB 统一管理 |
| 前端 | HTML + CSS + JavaScript | - | 轻量级 SPA，无需构建工具 |

### 硬件需求

| 资源 | 最低要求 | 推荐配置 |
|------|---------|---------|
| CPU | 4 核 | 8 核 |
| 内存 | 8 GB | 16 GB |
| 磁盘 | 20 GB SSD | 50 GB SSD |
| WSL2 内存分配 | 8 GB | 16 GB |

---

## 🚀 快速开始

### 前置条件

- Python 3.12+
- Docker & Docker Compose v2
- (WSL2) 至少 8GB 内存分配

### 1. 克隆项目

```bash
git clone git@github.com:bucaixiaosheng/knowledge-rag-system.git
cd knowledge-rag-system
```

### 2. 启动基础设施（Neo4j + ChromaDB）

```bash
docker compose up -d

# 验证服务
docker compose ps
curl http://localhost:8300/api/v1/heartbeat  # ChromaDB
# Neo4j Browser: http://localhost:7474
```

### 3. 创建虚拟环境 & 安装依赖

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. 配置环境变量

编辑 `.env` 文件，填入你的智谱 API Key：

```bash
# 必填：智谱 API Key
LLM_API_KEY=你的智谱API_KEY

# 其余配置已有默认值，按需调整
```

### 5. 初始化系统

```bash
python scripts/init_system.py
```

此脚本会：
- 创建必要的目录结构（`docs/`, `logs/`, `neo4j/`, `chroma/`）
- 验证 ChromaDB、Neo4j、Embedding 模型、LLM SDK 的连接

然后在 Neo4j Browser（`http://localhost:7474`）中执行初始化脚本：

```bash
# 复制 neo4j/init/01_schema.cypher 的内容到 Neo4j Browser 执行
# 这会创建约束、索引和示例数据
```

### 6. 启动 API 服务

```bash
source venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8100 --reload
```

API 文档：`http://localhost:8100/docs`（Swagger UI）

### 7. 添加文档

```bash
# 单文件入库
python scripts/add_document.py ./docs/markdown/example.md

# URL 入库
python scripts/add_document.py --url https://example.com/article

# 批量目录入库
python scripts/add_document.py --dir ./docs/pdf --tags "技术文档"
```

### 8. 访问前端

```bash
# 开发模式（简单静态文件服务）
cd web && python3 -m http.server 8080
# 浏览器打开 http://localhost:8080
```

---

## ⚙️ 配置说明

所有配置通过 `.env` 文件管理，位于项目根目录。

### 环境变量一览

```bash
# =================== Neo4j ===================
NEO4J_URI=bolt://localhost:7687       # Neo4j Bolt 协议地址
NEO4J_USER=neo4j                      # 用户名
NEO4J_PASSWORD=knowledge2026          # 密码（与 docker-compose.yml 中一致）

# =================== ChromaDB =================
CHROMA_HOST=localhost                  # ChromaDB 地址
CHROMA_PORT=8300                       # ChromaDB 端口（映射自容器 8000）
CHROMA_COLLECTION=knowledge_docs       # 向量集合名称

# =================== Embedding ================
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2  # 本地 Embedding 模型
EMBEDDING_DEVICE=cpu                   # 推理设备（cpu / cuda）

# =================== LLM =====================
LLM_BASE_URL=https://open.bigmodel.cn/api/coding/paas/v4  # 智谱 API 地址
LLM_API_KEY=你的智谱API_KEY                                  # ⚠️ 必填
LLM_MODEL=glm-5                       # 模型名称

# =================== 文档处理 =================
CHUNK_SIZE=512                         # 文本切块大小（字符数）
CHUNK_OVERLAP=50                       # 切块重叠字符数
MAX_WORKERS=4                          # 并行处理线程数

# =================== API =====================
API_HOST=0.0.0.0                       # API 监听地址
API_PORT=8100                          # API 监听端口
```

### Docker Compose 端口映射

| 服务 | 容器端口 | 主机端口 | 说明 |
|------|---------|---------|------|
| Neo4j HTTP | 7474 | 7474 | Neo4j Browser |
| Neo4j Bolt | 7687 | 7687 | Cypher 查询协议 |
| ChromaDB | 8000 | 8300 | 向量数据库 API |
| FastAPI | 8100 | 8100 | 知识管理 API |

---

## 📡 API 接口文档

系统提供 **13 个 REST API 端点**，分为 4 个功能模块：

### 基础

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/health` | 健康检查 |

### 💬 对话（`/api/v1/chat`）

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/chat/` | 对话式知识检索（RAG 问答） |
| `POST` | `/api/v1/chat/clear` | 清空对话历史 |

**请求示例**：

```bash
curl -X POST http://localhost:8100/api/v1/chat/ \
  -H "Content-Type: application/json" \
  -d '{"query": "什么是RAG？", "top_k": 5}'
```

**响应示例**：

```json
{
  "answer": "RAG（Retrieval-Augmented Generation）是一种结合信息检索和文本生成的技术...",
  "sources": [
    {"doc_id": "doc_abc123", "title": "RAG技术方案", "score": 0.92}
  ],
  "context_count": 5
}
```

### 📄 文档管理（`/api/v1/documents`）

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/documents/upload` | 上传文档入库（multipart/form-data） |
| `POST` | `/api/v1/documents/url` | URL 入库 |
| `DELETE` | `/api/v1/documents/{doc_id}` | 删除文档 |
| `GET` | `/api/v1/documents/stats` | 获取系统统计 |

**上传文档**：

```bash
curl -X POST http://localhost:8100/api/v1/documents/upload \
  -F "file=@/path/to/document.pdf"
```

**URL 入库**：

```bash
curl -X POST http://localhost:8100/api/v1/documents/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article", "tags": ["技术"]}'
```

### 🔍 搜索（`/api/v1/search`）

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/search/hybrid` | 混合检索（向量 + 图谱 + 关键词） |
| `POST` | `/api/v1/search/vector` | 纯向量检索 |

**混合搜索**：

```bash
curl -X POST http://localhost:8100/api/v1/search/hybrid \
  -H "Content-Type: application/json" \
  -d '{
    "query": "知识图谱",
    "top_k": 10,
    "vector_weight": 0.5,
    "graph_weight": 0.3,
    "keyword_weight": 0.2
  }'
```

### 🕸️ 图谱（`/api/v1/graph`）

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/graph/search` | 图谱全文搜索 |
| `GET` | `/api/v1/graph/document/{doc_id}` | 获取文档的知识图谱 |
| `GET` | `/api/v1/graph/similar/{doc_id}` | 查找相似文档 |
| `GET` | `/api/v1/graph/stats` | 图谱统计信息 |

---

## 🔧 CLI 工具使用说明

`scripts/add_document.py` 提供命令行文档管理能力：

```bash
source venv/bin/activate

# 查看帮助
python scripts/add_document.py --help

# 📄 单文件入库
python scripts/add_document.py ./docs/pdf/技术方案.pdf
python scripts/add_document.py ./docs/markdown/笔记.md --tags "技术,笔记"

# 🌐 URL 入库
python scripts/add_document.py --url https://example.com/article

# 📁 批量目录入库
python scripts/add_document.py --dir ./docs/pdf
python scripts/add_document.py --dir ./docs/markdown --tags "文档"

# 🗑️ 删除文档
python scripts/add_document.py --delete doc_abc123

# 📊 查看系统统计
python scripts/add_document.py --stats
```

### 初始化工具

```bash
# 创建目录结构 + 验证服务连接
python scripts/init_system.py
```

---

## 📁 项目目录结构

```
knowledge-rag-system/
├── .env                            # 环境变量配置
├── .gitignore                      # Git 忽略规则
├── docker-compose.yml              # Docker Compose 编排（Neo4j + ChromaDB）
├── requirements.txt                # Python 依赖
├── README.md                       # 项目文档
│
├── src/                            # 🔧 核心代码
│   ├── __init__.py
│   ├── config.py                   # 配置管理（读取 .env）
│   ├── document_loader.py          # 文档加载（PDF/HTML/MD/URL）
│   ├── text_chunker.py             # 递归文本切块
│   ├── embedding.py                # Embedding 封装（sentence-transformers）
│   ├── vector_store.py             # ChromaDB 向量存储操作
│   ├── knowledge_graph.py          # Neo4j 知识图谱操作
│   ├── entity_extractor.py         # LLM 实体/概念/锚关键词抽取
│   ├── hybrid_retriever.py         # 混合检索器（向量+图谱+关键词）
│   ├── reranker.py                 # LLM 重排序
│   ├── pipeline.py                 # 入库流水线（核心，一条龙）
│   ├── rag_chat.py                 # RAG 对话引擎
│   ├── wechat_ingest.py            # 微信公众号文章入库
│   └── scheduler.py                # APScheduler 定时任务
│
├── api/                            # 🌐 FastAPI 接口层
│   ├── __init__.py
│   ├── main.py                     # FastAPI 入口（app 实例、中间件、路由注册）
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── chat.py                 # 对话接口（RAG 问答、清空历史）
│   │   ├── documents.py            # 文档管理（上传、URL入库、删除、统计）
│   │   ├── graph.py                # 图谱查询（全文搜索、文档图谱、相似文档）
│   │   └── search.py               # 搜索接口（混合检索、向量检索）
│   └── models/
│       ├── __init__.py
│       └── schemas.py              # Pydantic 数据模型
│
├── web/                            # 🖥️ 前端界面
│   ├── index.html                  # 主页面（4 面板：对话/搜索/图谱/文档管理）
│   ├── style.css                   # 样式
│   └── app.js                      # 交互逻辑
│
├── scripts/                        # 🛠️ 工具脚本
│   ├── add_document.py             # 文档管理 CLI（添加/删除/统计）
│   └── init_system.py              # 系统初始化脚本
│
├── neo4j/                          # 🗄️ Neo4j 配置与数据
│   ├── data/                       # 数据持久化（Docker volume）
│   ├── logs/                       # Neo4j 日志
│   ├── init/
│   │   └── 01_schema.cypher        # 初始化脚本（约束、索引、示例数据）
│   └── conf/
│       └── neo4j.conf              # Neo4j 自定义配置
│
├── chroma/                         # 📦 ChromaDB 数据持久化
│
├── docs/                           # 📄 待入库文档
│   ├── pdf/                        # PDF 文档
│   ├── html/                       # HTML 文档
│   ├── markdown/                   # Markdown 文档
│   └── urls.txt                    # 定时爬取 URL 列表
│
├── logs/                           # 📋 运行日志
│
├── tests/                          # 🧪 测试
│   └── test_hybrid_retriever.py
│
├── knowledge-rag.service           # ⚙️ systemd 服务（FastAPI）
└── neo4j-knowledge.service         # ⚙️ systemd 服务（Docker 容器）
```

---

## 🐳 Docker Compose 部署

### 服务说明

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| `neo4j` | `neo4j:5.26-community` | 7474, 7687 | 图数据库，启用 APOC 插件 |
| `chromadb` | `chromadb/chroma:latest` | 8300 | 向量数据库，持久化存储 |

### 常用命令

```bash
# 启动所有服务
docker compose up -d

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f neo4j
docker compose logs -f chromadb

# 停止所有服务
docker compose down

# 完全清理（包括数据）
docker compose down -v
```

### 数据持久化

数据通过 Docker Volume 映射到本地目录：

- Neo4j 数据：`./neo4j/data/`、`./neo4j/logs/`
- ChromaDB 数据：`./chroma/`

---

## ⚙️ systemd 服务部署

项目提供了两个 systemd 服务文件，适用于生产环境。

### 1. `neo4j-knowledge.service` — 基础设施服务

管理 Neo4j 和 ChromaDB 容器的启动/停止。

### 2. `knowledge-rag.service` — API 服务

FastAPI 应用服务，依赖 Docker 服务。

### 安装步骤

```bash
# 1. 确保虚拟环境已创建
cd ~/knowledge-rag-system
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. 复制 service 文件
sudo cp knowledge-rag.service /etc/systemd/system/
sudo cp neo4j-knowledge.service /etc/systemd/system/

# 3. 加载并启用服务
sudo systemctl daemon-reload
sudo systemctl enable neo4j-knowledge knowledge-rag

# 4. 启动服务
sudo systemctl start neo4j-knowledge    # 先启动数据库
sudo systemctl start knowledge-rag      # 再启动 API

# 5. 查看状态
sudo systemctl status neo4j-knowledge
sudo systemctl status knowledge-rag

# 6. 查看日志
journalctl -u knowledge-rag -f          # 实时 API 日志
journalctl -u neo4j-knowledge -f        # 实时数据库日志
```

### 服务管理

```bash
# 重启 API
sudo systemctl restart knowledge-rag

# 停止所有服务
sudo systemctl stop knowledge-rag neo4j-knowledge

# 禁用开机自启
sudo systemctl disable knowledge-rag neo4j-knowledge
```

> **注意**：API 日志同时写入 `logs/api.log` 和 `logs/api-error.log`。

---

## 📱 微信公众号文章入库

系统支持微信公众号文章一键入库，通过 `scrapling` 工具爬取文章内容。

### 使用方式

**方式一：Python 脚本**

```bash
source venv/bin/activate
python -m src.wechat_ingest "https://mp.weixin.qq.com/s/xxxxxx"
```

**方式二：入库流水线调用**

```python
from src.pipeline import IngestPipeline
pipeline = IngestPipeline()
result = pipeline.ingest_wechat_url("https://mp.weixin.qq.com/s/xxxxxx")
print(result)
# {'doc_id': 'wx_abc123', 'title': '...', 'chunk_count': 5, 'anchor_count': 12, 'status': 'success'}
```

### 入库流程

```
微信公众号 URL
  ↓
scrapling 爬取正文 → 生成 Markdown
  ↓
保存 MD 文件到 docs/ 目录
  ↓
自动分类 → 提取锚关键词 → Embedding → 相似度建边 → 入库
```

---

## 🕸️ 知识图谱架构

系统采用 **层级化知识图谱 v2.0** 设计，核心是 **锚关键词（AnchorKeyword）** 关联机制：

```
KnowledgeRoot（全局根节点）
  └─ Domain（7 大学科：Technology / Science / SocialScience / Arts / Business / Engineering / Medicine）
      └─ SubDomain（子领域：AI / WebDev / DevOps / Finance / Physics / ...）
          └─ Document（文档节点）
              └─ Chunk（文本切块）
                  └─ AnchorKeyword（锚关键词）⭐ 核心关联枢纽
                      └─ SEMANTICALLY_SIMILAR（语义相似度边）→ 跨文档/跨领域关联
```

### 核心机制：锚关键词关联

1. 文档入库时，LLM 自动提取 **10-25 个锚关键词**
2. 每个锚关键词存储 embedding 向量
3. 新关键词入库时，与已有关键词计算 **余弦相似度**
4. 相似度 > 阈值（默认 0.5）→ 创建 `SEMANTICALLY_SIMILAR` 关系
5. 通过锚关键词网络实现 **跨文档、跨领域的知识自动串联**

### Cypher 查询示例

```cypher
-- 查询锚关键词关联网络
MATCH path = (ak:AnchorKeyword {keyword: '量化交易'})-[:SEMANTICALLY_SIMILAR*1..3]-(related:AnchorKeyword)
RETURN path LIMIT 50

-- 发现跨领域知识桥
MATCH (ak1:AnchorKeyword)<-[:HAS_ANCHOR]-(:Chunk)<-[:HAS_CHUNK]-(d1:Document)-[:CONTAINS_DOC]->(sd1:SubDomain)
MATCH (ak2:AnchorKeyword)<-[:HAS_ANCHOR]-(:Chunk)<-[:HAS_CHUNK]-(d2:Document)-[:CONTAINS_DOC]->(sd2:SubDomain)
WHERE (ak1)-[:SEMANTICALLY_SIMILAR]->(ak2) AND sd1 <> sd2
RETURN sd1.name, ak1.keyword, ak2.keyword, sd2.name

-- 图谱统计
MATCH (n) RETURN labels(n) AS type, count(n) AS count ORDER BY count DESC
```

---

## 🔄 RAG 检索流程

```
用户查询 "什么是知识图谱？"
    │
    ├─→ 1. 实体抽取（LLM 识别查询中的实体/概念）
    │
    ├─→ 2. 多路检索（并行）
    │   ├─ 向量检索：ChromaDB 语义搜索 top_k*2
    │   ├─ 图谱检索：Neo4j 实体扩展 + 全文搜索
    │   └─ 关键词检索：jieba 分词 + BM25 匹配
    │
    ├─→ 3. 结果合并（加权融合，默认 0.5/0.3/0.2）
    │
    ├─→ 4. LLM 重排序（精排 top_k）
    │
    ├─→ 5. 构建 Prompt（上下文 + 查询）
    │
    └─→ 6. LLM 生成回答（引用来源文档）
```

---

## 📋 License

MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
