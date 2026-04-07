"""
文档入库流水线：爬取 → MD → 解析 → 分类 → 切块 → 提取锚关键词 → embedding → 相似度建边 → 入库
这是整个系统的核心！一条龙完成所有步骤。
"""
import logging
import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime

from urllib.parse import urlparse, parse_qs

from src.document_loader import DocumentLoader
from src.text_chunker import TextChunker
from src.vector_store import VectorStore
from src.knowledge_graph import KnowledgeGraph
from src.entity_extractor import EntityExtractor
from src.embedding import EmbeddingEngine
from src.knowledge_writeback import KnowledgeWriteback
from src.config import CHUNK_SIZE, CHUNK_OVERLAP, WRITEBACK_ENABLED
from src.rag_chat import RAGChat
from src.hybrid_retriever import HybridRetriever

logger = logging.getLogger(__name__)


def generate_wechat_doc_id(url: str) -> str:
    """为微信URL生成唯一且稳定的doc_id。

    策略：
    1. 短URL格式 /s/XXXXX → wx_XXXXX（直接使用路径中的唯一hash）
    2. 长URL格式（含sn参数）→ wx_{sn}
    3. 其他微信URL → wx_{SHA256(url)[:24]}
    4. 非微信URL → {SHA256(url)[:24]}（无wx_前缀）

    Args:
        url: 文档来源URL

    Returns:
        doc_id字符串，以wx_开头（微信URL）或无前缀（其他URL）
    """
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    is_wechat = "mp.weixin.qq.com" in host

    if not is_wechat:
        # 非微信URL：使用SHA256[:24]（96位，碰撞概率极低）
        return hashlib.sha256(url.encode()).hexdigest()[:24]

    # 微信URL处理
    path = parsed.path.rstrip("/")

    # 策略1: 短URL格式 /s/{hash}
    short_match = re.match(r"^/s/([A-Za-z0-9_-]+)$", path)
    if short_match:
        return f"wx_{short_match.group(1)}"

    # 策略2: 长URL格式，提取sn参数
    qs = parse_qs(parsed.query)
    sn_values = qs.get("sn", []) or qs.get("__sn", [])
    if sn_values and sn_values[0]:
        return f"wx_{sn_values[0]}"

    # 策略3: 其他微信URL，使用SHA256[:24]
    return f"wx_{hashlib.sha256(url.encode()).hexdigest()[:24]}"


class IngestPipeline:
    """文档入库流水线（v2.0：完整知识图谱入库）"""

    def __init__(self):
        self.loader = DocumentLoader()
        self.chunker = TextChunker(CHUNK_SIZE, CHUNK_OVERLAP)
        self.vector_store = VectorStore()
        self.kg = KnowledgeGraph()
        self.extractor = EntityExtractor()
        self.emb_engine = EmbeddingEngine()
        self.hybrid_retriever = HybridRetriever(self.vector_store, self.kg, self.extractor)

    @staticmethod
    def _validate_extracted_title(title: str) -> bool:
        """验证从markdown提取的标题是否合法。

        检查项：
        1. 标题长度 ≤ 50字符
        2. 不含正文标点模式（连续逗号+句号等）
        3. 不含换行符
        4. 不是以口语化词汇开头且超长（如"其实我一直想搞点短视频副业来着..."）

        Returns:
            True表示标题合法，False表示可疑（应走HTML fallback）
        """
        if not title or title == "Unknown":
            return False

        # 检查1: 长度超过50字符
        if len(title) > 50:
            logger.debug(f"标题验证失败: 长度{len(title)}超过50字符 - {title!r}")
            return False

        # 检查2: 包含换行符
        if "\n" in title or "\r" in title:
            logger.debug(f"标题验证失败: 包含换行符 - {title!r}")
            return False

        # 检查3: 正文标点模式（连续逗号/句号/顿号/分号，如 "，，" "。。" "，。"）
        if re.search(r"[，。、；：]{2,}", title) or re.search(r"[,.;:]{2,}", title):
            logger.debug(f"标题验证失败: 含连续标点模式 - {title!r}")
            return False

        # 检查4: 口语化开头 + 偏长文本（>20字）
        colloquial_starts = (
            "其实", "最近", "之前", "说实话", "说真的",
            "不过", "但是", "然而", "今天", "昨天", "刚才",
        )
        if title.startswith(colloquial_starts) and len(title) > 20:
            logger.debug(f"标题验证失败: 口语化开头且偏长 - {title!r}")
            return False

        # 检查5: section header模式（如 "一、" "二、" "1." "01." "（一）" 等）
        # 这类标题是文章正文的章节标题，不是文章标题
        section_patterns = [
            r'^[一二三四五六七八九十百]+、',       # 一、二、三、...
            r'^\d+[.、．]\s*',                   # 1. 2. 3、...
            r'^\d{2}\s',                         # 01 02 03 ...
            r'^[（(][一二三四五六七八九十]+[）)]',   # （一）（二）...
        ]
        for pat in section_patterns:
            if re.match(pat, title):
                logger.debug(f"标题验证失败: section header模式 - {title!r}")
                return False

        return True

    def ingest_file(self, file_path: str, tags: list[str] | None = None, force: bool = False) -> dict:
        """单文件入库（完整流程）"""
        doc = self.loader.load_file(file_path)
        return self._ingest_doc(doc, tags, force=force)

    def ingest_url(self, url: str, tags: list[str] | None = None, force: bool = False) -> dict:
        """URL入库"""
        doc = self.loader.load_url(url)
        return self._ingest_doc(doc, tags, force=force)

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

    def ingest_wechat_url(self, url: str, tags: list[str] | None = None, force: bool = False) -> dict:
        """微信公众号文章一键入库"""
        doc_id = generate_wechat_doc_id(url)

        # --force: 先删除旧数据
        if force and self.kg.document_exists(doc_id):
            logger.info(f"[force] 删除旧文档: {doc_id}")
            self.delete_document(doc_id)
            print(f"🔄 [force] 已删除旧文档: {doc_id}")

        venv_python = os.path.expanduser(
            "~/.openclaw/skills/scrapling-article-fetch/venv/bin/python"
        )
        script = os.path.expanduser(
            "~/.openclaw/skills/scrapling-article-fetch/scripts/scrapling_fetch.py"
        )

        if not os.path.isfile(venv_python) or not os.path.isfile(script):
            logger.warning("scrapling工具未安装，使用通用URL加载")
            return self.ingest_url(url, tags=tags, force=force)

        try:
            # scrapling_fetch.py 直接输出markdown到stdout
            result = subprocess.run(
                [venv_python, script, url, "50000"],
                capture_output=True, text=True, timeout=60,
            )
            md_content = result.stdout
            if not md_content or len(md_content) < 100:
                raise ValueError(f"scrapling返回内容太短: {len(md_content) if md_content else 0} bytes")
            # 从markdown提取标题（改进版：前20行 + 正则fallback + HTML fallback + URL fallback）
            title = "Unknown"
            # 1. 检查前20行，匹配 # 和 ## 开头的行
            for line in md_content.split("\n")[:20]:
                line = line.strip()
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
                if line.startswith("## "):
                    title = line[3:].strip()
                    break
            # 验证步骤1提取的标题
            if title != "Unknown" and not IngestPipeline._validate_extracted_title(title):
                logger.warning(f"标题验证失败(步骤1-markdown标题)，将回退到HTML fallback: {title!r}")
                title = "Unknown"
            # 2. 正则fallback：匹配 "01标题" / "02标题" 模式
            if title == "Unknown":
                for line in md_content.split("\n")[:20]:
                    line = line.strip()
                    m = re.match(r"^\d{1,2}(.+)", line)
                    if m and len(m.group(1).strip()) > 2:
                        title = m.group(1).strip()
                        break
            # 验证步骤2提取的标题
            if title != "Unknown" and not IngestPipeline._validate_extracted_title(title):
                logger.warning(f"标题验证失败(步骤2-正则fallback)，将回退到HTML fallback: {title!r}")
                title = "Unknown"
            # 3. HTML fallback：从页面元数据获取标题（og:title > title > msg_title）
            if title == "Unknown":
                try:
                    import urllib.request
                    req = urllib.request.Request(
                        url,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                    )
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        html = resp.read(131072).decode("utf-8", errors="ignore")
                    # 优先级：og:title > <title> > msg_title
                    html_title = None
                    m_og = re.search(r'og:title.*?content="([^"]+)"', html, re.IGNORECASE)
                    if m_og and len(m_og.group(1).strip()) > 2:
                        html_title = m_og.group(1).strip()
                    if not html_title:
                        m_title = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
                        if m_title and len(m_title.group(1).strip()) > 2:
                            html_title = m_title.group(1).strip()
                    if not html_title:
                        m_msg = re.search(r'var\s+msg_title\s*=\s*["\x27]([^"\x27]+)["\x27]', html)
                        if m_msg and len(m_msg.group(1).strip()) > 2:
                            html_title = m_msg.group(1).strip()
                    if html_title:
                        # 清理微信标题后缀
                        for sep in [" - ", " – ", " — ", "_"]:
                            if sep in html_title:
                                html_title = html_title.split(sep)[0]
                        if len(html_title) > 2:
                            title = html_title
                except Exception as e:
                    logger.warning(f"HTML标题提取失败: {e}")
            # 4. URL fallback：从URL最后一部分或域名提取（最后手段，通常说明爬取失败）
            if title == "Unknown":
                try:
                    parsed = urlparse(url)
                    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
                    if path_parts:
                        title = path_parts[-1].replace("-", " ").replace("_", " ")
                    else:
                        title = parsed.netloc
                except Exception:
                    title = "Unknown"
        except Exception as e:
            logger.error(f"scrapling爬取失败: {e}，回退到通用加载")
            return self.ingest_url(url, tags=tags, force=force)

        # ===== 爬取结果验证 =====
        # 检查title是否是URL参数（说明爬取失败）
        parsed_url = urlparse(url)
        url_path_hash = parsed_url.path.strip("/").split("/")[-1] if parsed_url.path else ""
        title_is_url_garbage = (
            title.replace(" ", "") == url_path_hash.replace("-", "")
            or title == "Unknown"
        )
        content_too_short = len(md_content.strip()) < 200

        if title_is_url_garbage or content_too_short:
            logger.error(
                f"scrapling爬取结果无效: title={title!r}, "
                f"content_len={len(md_content)}, "
                f"title_is_url_garbage={title_is_url_garbage}"
            )
            return {
                "doc_id": doc_id,
                "status": "error",
                "error": f"crawl_invalid: title={title!r}, content_len={len(md_content)}",
            }

        # Step 3: 保存MD文件到docs目录
        # 清理md_content中的图片标签噪音
        lines = md_content.split("\n")
        cleaned_lines = []
        for line in lines:
            # 删除包含 mmbiz.qpic.cn 的图片标签行
            if "mmbiz.qpic.cn" in line and re.search(r"!\[.*?\]\(.*?\)", line):
                continue
            # 删除纯图片行（只有 ![](...) 没有其他文字的行）
            stripped = line.strip()
            if re.fullmatch(r"!?\[.*?\]\(.*?\)", stripped):
                continue
            cleaned_lines.append(line)
        md_content = "\n".join(cleaned_lines)
        # 将连续3+空行压缩为1个空行
        md_content = re.sub(r"\n{3,}", "\n\n", md_content)

        safe_title = "".join(
            c for c in title[:50] if c.isalnum() or c in " _-"
        ).strip() or "wechat_article"
        md_filename = f"{safe_title}.md"
        docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
        os.makedirs(docs_dir, exist_ok=True)
        md_path = os.path.join(docs_dir, md_filename)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(
                f"# {title}\n\n> 来源: {url}\n> 爬取时间: {datetime.now().isoformat()}\n\n{md_content}"
            )
        logger.info(f"微信文章已保存: {md_path}")

        # Step 4: 走完整入库流程（使用新的ID生成函数）
        return self._ingest_doc(
            {
                "doc_id": generate_wechat_doc_id(url),
                "title": title,
                "source": url,
                "doc_type": "wechat_article",
                "content": md_content,
                "metadata": {"url": url, "platform": "wechat"},
            },
            tags=tags,
        )

    def _ingest_doc(self, doc: dict, tags: list[str] | None = None, force: bool = False) -> dict:
        """内部入库逻辑（v2.0完整流程，带force和原子性）"""
        doc_id = doc["doc_id"]

        # --force: 先删除旧数据
        if force and self.kg.document_exists(doc_id):
            logger.info(f"[force] 删除旧文档: {doc_id}")
            self.delete_document(doc_id)

        # 去重检查
        if self.kg.document_exists(doc_id):
            logger.info(f"文档已存在，跳过: {doc_id}")
            return {"doc_id": doc_id, "status": "skipped", "reason": "already_exists"}

        # Step 1: 切块
        chunks = self.chunker.chunk_text(
            text=doc["content"],
            doc_id=doc_id,
            metadata={"title": doc["title"], "source": doc["source"]},
        )
        if not chunks:
            return {"doc_id": doc_id, "status": "error", "error": "no_chunks"}

        # === Steps 2-9: 带原子性的入库流程 ===
        # 如果中间步骤失败，尝试回滚已写入的数据
        try:
            # Step 2: 向量化并存入ChromaDB
            self.vector_store.add_chunks(chunks)

            # Step 3: LLM提取实体、概念、锚关键词
            summary = doc["content"][:3000]
            extracted = self.extractor.extract(summary)
            entities = extracted.get("entities", [])
            concepts = extracted.get("concepts", [])
            anchor_keywords = extracted.get("anchor_keywords", [])

            # Step 4: 创建文档节点
            now = datetime.utcnow().isoformat()
            self.kg.create_document({
                "doc_id": doc_id,
                "title": doc["title"],
                "source": doc["source"],
                "doc_type": doc["doc_type"],
                "summary": extracted.get("summary", doc["content"][:200]),
                "created_at": now,
                "updated_at": now,
                "chunk_count": len(chunks),
                "metadata": str(doc.get("metadata", {})),
            })

            # Step 5: 自动分类到学科领域
            domains = self.kg.classify_document(doc["title"], doc["content"], doc_id)
            self.kg.link_document_to_domain(doc_id, domains)

            # Step 6: 创建实体和概念节点
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

            # Step 7: 创建Chunk节点 + 锚关键词节点（核心！）
            # 如果全文档级别的锚关键词不够，批量提取一次（替代逐chunk调用）
            # 带重试机制：LLM内容过滤可能间歇性失败，最多重试2次
            if not anchor_keywords:
                max_retries = 2
                for attempt in range(1, max_retries + 1):
                    batch_anchors = self.extractor.extract_anchor_keywords_batch(chunks, doc["title"])
                    if batch_anchors:
                        break
                    if attempt < max_retries:
                        logger.warning(f"批量锚关键词提取返回空结果，第{attempt}次重试...")
                    else:
                        logger.warning(f"批量锚关键词提取{max_retries}次尝试均返回空结果")
            else:
                batch_anchors = anchor_keywords

            all_anchor_keywords = []
            for chunk in chunks:
                # 创建Chunk节点
                self.kg.create_chunk_node(chunk)
                # 使用批量提取的锚关键词
                self.kg.create_anchor_keywords(batch_anchors, chunk["chunk_id"], doc_id)

                # 记录关键词演化事件
                for kw in batch_anchors:
                    try:
                        self.kg.record_keyword_evolution(
                            keyword=kw.get("keyword", ""),
                            doc_id=doc_id,
                            chunk_id=chunk["chunk_id"],
                            action="appeared",
                        )
                    except Exception as e:
                        logger.warning(f"记录关键词演化事件失败: {e}")

                all_anchor_keywords.extend(batch_anchors)

            # Step 8: 计算锚关键词embedding + 相似度建边
            seen = set()
            unique_anchors = []
            for ak in all_anchor_keywords:
                if ak["keyword"] not in seen:
                    seen.add(ak["keyword"])
                    unique_anchors.append(ak)

            if unique_anchors:
                kw_texts = [ak["keyword"] for ak in unique_anchors]
                embeddings = self.emb_engine.embed_texts(kw_texts)
                for ak, emb in zip(unique_anchors, embeddings):
                    self.kg.update_anchor_embeddings(ak["keyword"], emb)
                self.kg.build_anchor_similarity_edges(threshold=0.5)

            # Step 9: 发现跨领域关联
            self.kg.discover_cross_domain_links()

        except Exception as e:
            # 入库失败，尝试回滚已写入的数据
            logger.error(f"入库过程中失败，尝试回滚 {doc_id}: {e}")
            try:
                self.delete_document(doc_id)
                logger.info(f"回滚成功: 已删除 {doc_id} 的所有数据")
            except Exception as rollback_err:
                logger.error(f"回滚失败! 需要手动清理 {doc_id}: {rollback_err}")
            return {"doc_id": doc_id, "status": "error", "error": str(e)}

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

    def semantic_search(self, query: str, top_k: int = 10) -> list[dict]:
        """语义查询入口（HybridRetriever 三路融合检索，文档级去重）"""
        raw_results = self.hybrid_retriever.retrieve(query, top_k=top_k * 3)

        # 文档级去重：每个doc_id只保留最高分的一条，确保结果多样性
        seen_docs = {}
        for r in raw_results:
            doc_id = r.get("doc_id", "")
            if not doc_id:
                continue
            if doc_id not in seen_docs or r.get("score", 0) > seen_docs[doc_id].get("score", 0):
                seen_docs[doc_id] = r

        # 图譔回补：部分文档可能只有图谱数据（未入ChromaDB），
        # 在融合排序中被向量结果挤掉。回补图谱独有的文档，确保不遗漏。
        # 回补分数使用与HybridRetriever一致的图谱权重（0.35）缩放。
        if len(seen_docs) < top_k:
            try:
                query_embedding = self.emb_engine.embed_query(query)
                graph_results = self.kg.search_by_semantic_query(query, query_embedding, top_k=top_k * 2)
                graph_fallback = []
                for item in graph_results:
                    if item.get("type") == "related_knowledge":
                        continue  # 跳过扩展知识，只处理chunk结果
                    doc_id = item.get("doc_id", "")
                    if doc_id and doc_id not in seen_docs:
                        raw_score = float(item.get("relevance_score") or item.get("keyword_score", 0))
                        graph_fallback.append({
                            "chunk_id": item.get("chunk_id", f"graph_{doc_id}"),
                            "content": item.get("content", "") or item.get("summary", ""),
                            "doc_id": doc_id,
                            "score": round(raw_score * 0.35, 4),  # 与HybridRetriever图谱权重一致
                            "source": "graph",
                            "metadata": {
                                "title": item.get("title", ""),
                                "matched_keyword": item.get("matched_keyword", ""),
                            },
                        })
                # 按score降序取前N个回补
                graph_fallback.sort(key=lambda x: x["score"], reverse=True)
                for fb in graph_fallback:
                    if len(seen_docs) >= top_k:
                        break
                    seen_docs[fb["doc_id"]] = fb
            except Exception as e:
                logger.warning(f"图譔回补失败（不影响主流程）: {e}")

        # 按score降序排列后截取top_k
        results = sorted(seen_docs.values(), key=lambda x: x.get("score", 0), reverse=True)
        return results[:top_k]

    def delete_document(self, doc_id: str) -> dict:
        """删除文档（级联清理：向量库 + 知识图谱）"""
        deleted_chunks = 0
        deleted_doc = False

        # Step 1: 先删除ChromaDB中的向量数据
        try:
            self.vector_store.delete_by_doc(doc_id)
            deleted_chunks = True
        except Exception as e:
            logger.warning(f"向量库删除失败: {e}")

        # Step 2: 再删除Neo4j中的图谱数据（Chunk + AnchorKeyword + Document）
        try:
            self.kg.delete_document(doc_id)
            deleted_doc = True
        except Exception as e:
            logger.error(f"图谱删除失败: {e}")
            raise

        result = {
            "doc_id": doc_id,
            "status": "deleted",
            "vector_store_cleaned": deleted_chunks,
            "graph_cleaned": deleted_doc,
        }
        logger.info(f"文档已删除: {result}")
        return result

    def create_rag_chat(self, retriever=None, reranker=None) -> RAGChat:
        """构建RAGChat实例，如果WRITEBACK_ENABLED=True则注入KnowledgeWriteback

        Args:
            retriever: 混合检索器实例（可选，默认使用HybridRetriever）
            reranker: 重排序器实例（可选）

        Returns:
            RAGChat实例
        """
        writeback_engine = None
        if WRITEBACK_ENABLED:
            try:
                writeback_engine = KnowledgeWriteback(self.kg, self.emb_engine)
                logger.info("知识回存引擎已注入RAGChat")
            except Exception as e:
                logger.warning(f"知识回存引擎初始化失败(不影响使用): {e}")

        return RAGChat(
            retriever=retriever,
            reranker=reranker,
            writeback_engine=writeback_engine,
        )
