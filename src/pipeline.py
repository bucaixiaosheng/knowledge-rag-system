"""
文档入库流水线：爬取 → MD → 解析 → 分类 → 切块 → 提取锚关键词 → embedding → 相似度建边 → 入库
这是整个系统的核心！一条龙完成所有步骤。
"""
import logging
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime

from src.document_loader import DocumentLoader
from src.text_chunker import TextChunker
from src.vector_store import VectorStore
from src.knowledge_graph import KnowledgeGraph
from src.entity_extractor import EntityExtractor
from src.embedding import EmbeddingEngine
from src.config import CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)


class IngestPipeline:
    """文档入库流水线（v2.0：完整知识图谱入库）"""

    def __init__(self):
        self.loader = DocumentLoader()
        self.chunker = TextChunker(CHUNK_SIZE, CHUNK_OVERLAP)
        self.vector_store = VectorStore()
        self.kg = KnowledgeGraph()
        self.extractor = EntityExtractor()
        self.emb_engine = EmbeddingEngine()

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def ingest_file(self, file_path: str, tags: list[str] | None = None) -> dict:
        """单文件入库（完整流程）"""
        doc = self.loader.load_file(file_path)
        return self._ingest_doc(doc, tags)

    def ingest_url(self, url: str, tags: list[str] | None = None) -> dict:
        """URL入库"""
        doc = self.loader.load_url(url)
        return self._ingest_doc(doc, tags)

    def ingest_directory(self, dir_path: str, recursive: bool = True) -> list[dict]:
        """批量目录入库"""
        docs = self.loader.load_directory(dir_path, recursive)
        results = []
        for doc in docs:
            try:
                result = self._ingest_doc(doc)
                results.append(result)
            except Exception as e:
                logger.error(f"入库失败 {doc['doc_id']}: {e}")
                results.append({"doc_id": doc["doc_id"], "status": "error", "error": str(e)})
        return results

    def ingest_wechat_url(self, url: str) -> dict:
        """微信公众号文章一键入库"""
        # Step 1: 用 scrapling 爬取
        venv_python = os.path.expanduser(
            "~/.openclaw/skills/scrapling-article-fetch/venv/bin/python"
        )
        script = os.path.expanduser(
            "~/.openclaw/skills/scrapling-article-fetch/scripts/scrapling_fetch.py"
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json_path = f.name

        subprocess.run(
            [venv_python, script, "--json", url, "50000"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Step 2: 解析 JSON，提取 markdown
        with open(json_path) as f:
            data = json.load(f)

        # 清理临时文件
        try:
            os.unlink(json_path)
        except OSError:
            pass

        title = data.get("title", "Unknown")
        md_content = data.get("markdown", "")

        # Step 3: 保存 MD 文件
        safe_title = "".join(c for c in title[:50] if c.isalnum() or c in " _-").strip()
        md_filename = f"{safe_title}.md"
        md_path = os.path.join(
            os.path.expanduser("~/knowledge-rag-system/docs/"), md_filename
        )
        os.makedirs(os.path.dirname(md_path), exist_ok=True)
        with open(md_path, "w") as f:
            f.write(
                f"# {title}\n\n"
                f"> 来源: {url}\n> 爬取时间: {datetime.now().isoformat()}\n\n"
                f"{md_content}"
            )
        logger.info(f"微信文章已保存: {md_path}")

        # Step 4: 走完整入库流程
        return self._ingest_doc({
            "doc_id": f"wx_{hashlib.md5(url.encode()).hexdigest()[:12]}",
            "title": title,
            "source": url,
            "doc_type": "wechat_article",
            "content": md_content,
            "metadata": {"url": url, "platform": "wechat"},
        })

    # ------------------------------------------------------------------
    # 内部完整入库逻辑（v2.0）
    # ------------------------------------------------------------------

    def _ingest_doc(self, doc: dict, tags: list[str] | None = None) -> dict:
        """
        内部入库逻辑（v2.0 完整流程）。
        流程：去重检查 → 切块 → 向量化 → LLM 提取 → 文档节点 → 分类 →
              锚关键词 → Chunk 节点 → 锚关键词 embedding → 相似度建边 → 跨领域关联
        """
        doc_id = doc["doc_id"]

        # ── 去重检查 ──────────────────────────────────────────────
        if self.kg.document_exists(doc_id):
            logger.info(f"文档已存在，跳过: {doc_id}")
            return {"doc_id": doc_id, "status": "skipped", "reason": "already_exists"}

        # ── Step 1: 切块 ──────────────────────────────────────────
        chunks = self.chunker.chunk_text(
            text=doc["content"],
            doc_id=doc_id,
            metadata={"title": doc["title"], "source": doc["source"]},
        )
        if not chunks:
            return {"doc_id": doc_id, "status": "error", "error": "no_chunks"}

        # ── Step 2: 向量化并存入 ChromaDB ──────────────────────────
        self.vector_store.add_chunks(chunks)

        # ── Step 3: LLM 提取实体、概念、锚关键词 ────────────────────
        summary_text = doc["content"][:3000]
        extracted = self.extractor.extract(summary_text)
        entities = extracted.get("entities", [])
        concepts = extracted.get("concepts", [])
        anchor_keywords = extracted.get("anchor_keywords", [])

        # ── Step 4: 创建文档节点 ──────────────────────────────────
        now = datetime.utcnow().isoformat()
        self.kg.create_document({
            "doc_id": doc_id,
            "title": doc["title"],
            "source": doc["source"],
            "doc_type": doc.get("doc_type", "unknown"),
            "content_summary": extracted.get("summary", doc["content"][:200]),
            "created_at": now,
            "updated_at": now,
            "chunk_count": len(chunks),
            "metadata": str(doc.get("metadata", {})),
        })

        # ── Step 5: 自动分类到学科领域 ─────────────────────────────
        domains = self.kg.classify_document(
            doc["title"], doc["content"], doc_id
        )
        self.kg.link_document_to_domain(doc_id, domains)

        # ── Step 6: 创建实体和概念节点 ─────────────────────────────
        if entities:
            self.kg.create_entities(entities, doc_id)
        if concepts:
            self.kg.create_concepts(concepts, doc_id)
        relations = extracted.get("relations", [])
        if relations:
            self.kg.create_relations(relations)
        doc_tags = tags or extracted.get("tags", [])
        if doc_tags:
            self.kg.add_tags(doc_tags, doc_id)

        # ── Step 7: 创建 Chunk 节点 + 锚关键词节点 ──────────────────
        all_anchor_keywords: list[dict] = []
        for chunk in chunks:
            # 创建 Chunk 节点
            self.kg.create_chunk_node(chunk)

            # 提取锚关键词：优先用整篇文档提取的，不够则按 chunk 补充
            if not anchor_keywords:
                chunk_anchors = self.extractor.extract_anchor_keywords_only(
                    chunk["content"], doc["title"]
                )
            else:
                chunk_anchors = anchor_keywords  # 全文档级别的关键词

            # 创建锚关键词节点
            self.kg.create_anchor_keywords(chunk_anchors, chunk["chunk_id"], doc_id)
            all_anchor_keywords.extend(chunk_anchors)

        # ── Step 8: 计算锚关键词 embedding + 相似度建边 ──────────────
        # 去重
        seen: set[str] = set()
        unique_anchors: list[dict] = []
        for ak in all_anchor_keywords:
            kw = ak.get("keyword", "")
            if kw and kw not in seen:
                seen.add(kw)
                unique_anchors.append(ak)

        if unique_anchors:
            # 批量计算 embedding
            kw_texts = [ak["keyword"] for ak in unique_anchors]
            embeddings = self.emb_engine.embed_texts(kw_texts)

            # 更新 embedding 引用
            for ak, emb in zip(unique_anchors, embeddings):
                self.kg.update_anchor_embeddings(ak["keyword"], emb)

            # 计算相似度并建边
            self.kg.build_anchor_similarity_edges(threshold=0.5)

        # ── Step 9: 发现跨领域关联 ──────────────────────────────────
        self.kg.discover_cross_domain_links()

        logger.info(
            f"✅ 入库完成: {doc_id} | chunks: {len(chunks)} | "
            f"anchors: {len(unique_anchors)} | entities: {len(entities)} | "
            f"domains: {domains}"
        )

        return {
            "doc_id": doc_id,
            "title": doc["title"],
            "chunk_count": len(chunks),
            "anchor_count": len(unique_anchors),
            "entity_count": len(entities),
            "domains": domains,
            "status": "success",
        }

    # ------------------------------------------------------------------
    # 语义查询入口
    # ------------------------------------------------------------------

    def semantic_search(self, query: str, top_k: int = 10) -> list[dict]:
        """语义查询入口（查询流程）"""
        query_embedding = self.emb_engine.embed_query(query)
        return self.kg.search_by_semantic_query(query, query_embedding, top_k)

    # ------------------------------------------------------------------
    # 删除文档
    # ------------------------------------------------------------------

    def delete_document(self, doc_id: str) -> None:
        """删除文档"""
        self.vector_store.delete_by_doc(doc_id)
        self.kg.delete_document(doc_id)
        logger.info(f"文档已删除: {doc_id}")
