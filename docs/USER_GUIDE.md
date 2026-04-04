# 知识RAG系统使用说明书

> 🎯 面向使用者（野哥），中文编写，持续更新。

---

## 1. 系统简介

本地部署的 **RAG（Retrieval-Augmented Generation）+ Neo4j知识图谱** 检索增强系统。

**核心能力：**
- 📥 多源入库：微信文章、PDF、Markdown、网页URL
- 🔍 语义搜索：基于向量相似度的智能检索
- 🕸️ 知识图谱：Neo4j 存储层级化学科分类 + 锚关键词关联
- 💬 RAG对话：知识库增强的智能问答

**技术栈：**
| 组件 | 技术 | 端口 |
|------|------|------|
| 知识图谱 | Neo4j | 7687 (Bolt) / 7474 (浏览器) |
| 向量数据库 | ChromaDB | 8300 |
| Embedding | all-MiniLM-L6-v2 (本地) | - |
| LLM | GLM-5 (智谱API) | - |
| API | FastAPI + Uvicorn | 8100 |

---

## 2. 环境启动

### 2.1 Docker服务启动

```bash
cd ~/knowledge-rag-system
docker compose up -d

# 验证容器运行
docker ps  # 应看到 neo4j-knowledge 和 chromadb-knowledge
```

**Neo4j浏览器：** http://localhost:7474
- 用户名: `neo4j`
- 密码: `knowledge2026`

### 2.2 虚拟环境

```bash
cd ~/knowledge-rag-system
source venv/bin/activate
```

⚠️ **所有 Python 命令必须先激活虚拟环境！**

### 2.3 启动API服务

```bash
cd ~/knowledge-rag-system
source venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8100
```

- API文档: http://localhost:8100/docs
- 前端页面: http://localhost:8100

---

## 3. 入库操作

### 3.1 通过API入库

**入库微信文章链接：**
```bash
curl -X POST http://localhost:8100/api/v1/documents/url \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://mp.weixin.qq.com/s/xxx"}'
```

**上传本地文件：**
```bash
curl -X POST http://localhost:8100/api/v1/documents/upload \
  -F "file=@/path/to/doc.md"
```

### 3.2 通过CLI命令行入库

```bash
cd ~/knowledge-rag-system
source venv/bin/activate

# 本地文件（支持 .md / .pdf / .txt / .html）
python cli.py ingest --file /path/to/doc.md

# 网页URL
python cli.py ingest --url https://example.com

# 微信公众号文章
python cli.py ingest --wechat-url https://mp.weixin.qq.com/s/xxx

# 批量目录入库
python cli.py ingest --dir /path/to/docs/

# 自定义标签
python cli.py ingest --file doc.md --tags "AI,工具,语音"
```

### 3.3 Python代码入库

```python
from src.pipeline import IngestPipeline

p = IngestPipeline()
p.ingest_file("path/to/doc.md")
p.ingest_url("https://example.com")
p.ingest_wechat_url("https://mp.weixin.qq.com/s/xxx")
p.ingest_directory("/path/to/docs/")
```

---

## 4. 查询操作

### 4.1 API语义搜索

```bash
curl "http://localhost:8100/api/v1/search/semantic?query=微软TTS&top_k=5"
```

### 4.2 API RAG对话

```bash
curl -X POST http://localhost:8100/api/v1/chat/rag \
  -H 'Content-Type: application/json' \
  -d '{"question": "推荐一些开源AI语音合成工具"}'
```

### 4.3 CLI命令行查询

```bash
# 语义搜索
python cli.py search "微软TTS"
python cli.py search "AI自动科研" --top-k 5
python cli.py search "知识图谱Neo4j" --top-k 3

# 详细输出模式
python cli.py --verbose search "测试查询"
```

**搜索结果说明：**
- 📄 普通结果：显示标题、来源、匹配关键词、相关度分数、摘要
- 🔗 相关知识：通过锚关键词语义相似度发现的跨文档关联

---

## 5. 管理操作

### 5.1 查看系统统计

```bash
# CLI方式
python cli.py stats

# API方式
curl http://localhost:8100/api/v1/documents/stats
```

**输出内容：**
- 🗄️ 知识图谱: 文档数、Chunk数、实体数、概念数、标签数、锚关键词数、领域数、关系数
- 📦 向量库: 文档数、Chunk数

### 5.2 删除文档（级联清理）

```bash
# CLI方式（推荐，级联清理更完整）
python cli.py delete --doc-id wx_abc123

# API方式
curl -X DELETE http://localhost:8100/api/v1/documents/wx_abc123
```

**级联删除流程：**
1. 删除 ChromaDB 中的向量数据
2. 收集文档关联的所有 Chunk ID
3. 清理孤立的 AnchorKeyword（移除引用，chunk_ids为空则删除）
4. 删除所有 Chunk 节点
5. 删除 Document 节点
6. 清理孤立的 Tag 节点

### 5.3 列出所有文档

```bash
python cli.py list-docs
```

显示所有文档的 ID、标题、领域分类、Chunk数和类型。

---

## 6. 常用命令速查表

| 操作 | 命令 |
|------|------|
| **启动Docker** | `cd ~/knowledge-rag-system && docker compose up -d` |
| **激活虚拟环境** | `cd ~/knowledge-rag-system && source venv/bin/activate` |
| **启动API服务** | `uvicorn api.main:app --host 0.0.0.0 --port 8100` |
| **入库文件** | `python cli.py ingest --file /path/to/doc.md` |
| **入库URL** | `python cli.py ingest --url https://example.com` |
| **入库微信文章** | `python cli.py ingest --wechat-url https://mp.weixin.qq.com/s/xxx` |
| **批量目录入库** | `python cli.py ingest --dir /path/to/docs/` |
| **入库带标签** | `python cli.py ingest --file doc.md --tags "AI,工具"` |
| **语义搜索** | `python cli.py search "查询文本"` |
| **搜索限制数量** | `python cli.py search "查询" --top-k 5` |
| **删除文档** | `python cli.py delete --doc-id wx_abc123` |
| **系统统计** | `python cli.py stats` |
| **列出文档** | `python cli.py list-docs` |
| **详细输出** | `python cli.py --verbose search "测试"` |
| **Neo4j浏览器** | 浏览器打开 http://localhost:7474 (neo4j/knowledge2026) |
| **API文档** | 浏览器打开 http://localhost:8100/docs |
| **查看Docker日志** | `docker logs neo4j-knowledge` / `docker logs chromadb-knowledge` |

---

## 7. 故障排查

### Docker容器未启动

```bash
# 查看容器状态
docker ps -a

# 重启容器
cd ~/knowledge-rag-system
docker compose up -d

# 查看日志
docker logs neo4j-knowledge --tail 50
docker logs chromadb-knowledge --tail 50
```

### 端口冲突

```bash
# 查看端口占用
ss -tlnp | grep -E '7687|7474|8300|8100'

# 杀死占用进程
kill -9 <PID>
```

| 端口 | 服务 |
|------|------|
| 7687 | Neo4j Bolt |
| 7474 | Neo4j Browser |
| 8300 | ChromaDB |
| 8100 | API服务 |

### 入库失败

1. **确认虚拟环境已激活**：`which python` 应指向 `venv/bin/python`
2. **确认Docker运行**：`docker ps`
3. **查看日志**：`python cli.py --verbose ingest --file doc.md`
4. **微信文章抓取失败**：可能是网络问题或文章已删除，试试 `--url` 模式

### Neo4j连接失败

```bash
# 测试连接
./venv/bin/python -c "
from neo4j import GraphDatabase
d = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'knowledge2026'))
d.verify_connectivity()
print('Neo4j连接成功')
d.close()
"

# 检查Neo4j状态
docker exec neo4j-knowledge cypher-shell -u neo4j -p knowledge2026 "RETURN 1"
```

### ChromaDB连接失败

```bash
# 测试连接
curl http://localhost:8300/api/v1/heartbeat

# 重启ChromaDB
docker restart chromadb-knowledge
```

### 重新入库同一文档

系统自动去重。如果需要强制重新入库：
1. 先删除旧文档：`python cli.py delete --doc-id <doc_id>`
2. 重新入库：`python cli.py ingest --file doc.md`

---

## 8. 项目目录结构

```
~/knowledge-rag-system/
├── cli.py              # CLI命令行工具
├── api/                # FastAPI API服务
├── src/
│   ├── pipeline.py     # 入库流水线（核心）
│   ├── knowledge_graph.py  # Neo4j知识图谱操作
│   ├── vector_store.py # ChromaDB向量存储
│   ├── embedding.py    # Embedding引擎
│   ├── entity_extractor.py # LLM实体/关键词提取
│   ├── document_loader.py  # 文档加载器
│   ├── text_chunker.py # 文本切块
│   └── config.py       # 配置管理
├── docs/               # 文档存储目录
├── tests/              # 测试代码
├── docker-compose.yml  # Docker编排
├── .env                # 环境变量
├── requirements.txt    # Python依赖
└── venv/               # 虚拟环境
```

---

*最后更新: 2026-04-04*
