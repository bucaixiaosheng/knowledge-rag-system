"""
混合检索模块：向量 + 图谱 + BM25 关键词三路加权融合

核心流程：
1. 向量检索 — ChromaDB 语义搜索
2. 图谱增强检索 — Neo4j 锚关键词语义匹配 + 实体扩展
3. BM25 关键词检索 — rank_bm25 精确词频匹配
4. 加权合并排序 — 三路结果按权重融合
"""
import logging
from collections import defaultdict
from typing import Optional

import jieba
from rank_bm25 import BM25Okapi

from src.embedding import embedding_engine
from src.entity_extractor import EntityExtractor
from src.knowledge_graph import KnowledgeGraph
from src.vector_store import VectorStore

logger = logging.getLogger(__name__)

# 默认权重：向量 0.4，图谱 0.35，关键词 0.25
DEFAULT_VECTOR_WEIGHT = 0.4
DEFAULT_GRAPH_WEIGHT = 0.35
DEFAULT_KEYWORD_WEIGHT = 0.25


class HybridRetriever:
    """混合检索器：向量 + 图谱 + BM25 三路加权融合"""

    def __init__(
        self,
        vector_store: VectorStore,
        knowledge_graph: KnowledgeGraph,
        entity_extractor: Optional[EntityExtractor] = None,
    ):
        self.vector_store = vector_store
        self.kg = knowledge_graph
        self.extractor = entity_extractor or EntityExtractor()

        # BM25 索引（延迟构建，基于 ChromaDB 中的所有 chunk）
        self._bm25: Optional[BM25Okapi] = None
        self._bm25_corpus: list[str] = []      # tokenized corpus
        self._bm25_chunks: list[dict] = []     # 原始 chunk 元数据

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        vector_weight: float = DEFAULT_VECTOR_WEIGHT,
        graph_weight: float = DEFAULT_GRAPH_WEIGHT,
        keyword_weight: float = DEFAULT_KEYWORD_WEIGHT,
    ) -> list[dict]:
        """
        混合检索主方法：向量 + 图谱 + BM25 三路加权融合。

        Args:
            query: 查询文本
            top_k: 返回结果数
            vector_weight: 向量检索权重（默认 0.4）
            graph_weight: 图谱检索权重（默认 0.35）
            keyword_weight: BM25 关键词检索权重（默认 0.25）

        Returns:
            list[dict]: 每个 dict 包含 chunk_id, content, doc_id, score, source, metadata
        """
        logger.info(
            f"混合检索: query='{query[:50]}...', top_k={top_k}, "
            f"weights=(v={vector_weight}, g={graph_weight}, k={keyword_weight})"
        )

        # 1. 向量检索
        vector_results = self.vector_store.search(query, top_k=top_k * 2)
        for r in vector_results:
            r["source"] = "vector"
        logger.info(f"  向量检索: {len(vector_results)} 条")

        # 2. 图谱增强检索
        graph_results = self._graph_enhanced_search(query, top_k=top_k)
        logger.info(f"  图谱检索: {len(graph_results)} 条")

        # 3. BM25 关键词检索
        keyword_results = self._keyword_search(query, top_k=top_k)
        logger.info(f"  关键词检索: {len(keyword_results)} 条")

        # 4. 加权合并
        merged = self._merge_results(
            vector_results,
            graph_results,
            keyword_results,
            vector_weight,
            graph_weight,
            keyword_weight,
        )

        logger.info(f"  合并排序后: {len(merged[:top_k])} 条 (总 {len(merged)})")
        return merged[:top_k]

    # ------------------------------------------------------------------
    # 图谱增强检索
    # ------------------------------------------------------------------

    def _graph_enhanced_search(self, query: str, top_k: int = 10) -> list[dict]:
        """
        图谱增强检索：通过 knowledge_graph.search_by_semantic_query 获取锚关键词匹配结果。

        流程：
        1. 用查询文本生成 embedding
        2. 调用 kg.search_by_semantic_query 获取锚关键词关联的 chunk
        3. 标准化结果格式，统一包含 score 和 source 字段
        """
        try:
            query_embedding = embedding_engine.embed_query(query)
        except Exception as e:
            logger.error(f"图谱检索: embedding 生成失败: {e}")
            return []

        try:
            raw_results = self.kg.search_by_semantic_query(query, query_embedding, top_k=top_k)
        except Exception as e:
            logger.error(f"图谱检索: Neo4j 查询失败: {e}")
            return []

        results = []
        for item in raw_results:
            # search_by_semantic_query 可能返回两种结构：
            #   - chunk 级结果（含 chunk_id, content, doc_id, relevance_score）
            #   - related_knowledge 扩展结果（含 related_keyword, similarity, related_docs）
            if item.get("type") == "related_knowledge":
                # 扩展结果：为每个关联文档生成一条记录
                similarity = item.get("similarity", 0.0)
                for doc in item.get("related_docs", []):
                    if not doc.get("doc_id"):
                        continue
                    results.append({
                        "chunk_id": f"graph_related_{doc['doc_id']}",
                        "content": doc.get("title", ""),
                        "doc_id": doc["doc_id"],
                        "score": float(similarity),
                        "source": "graph_expansion",
                        "metadata": {
                            "title": doc.get("title", ""),
                            "related_keyword": item.get("related_keyword", ""),
                        },
                    })
            else:
                # chunk 级结果
                chunk_id = item.get("chunk_id", f"graph_{item.get('doc_id', 'unknown')}")
                score = item.get("relevance_score") or item.get("keyword_score", 0.0)
                results.append({
                    "chunk_id": chunk_id,
                    "content": item.get("content", "") or item.get("summary", ""),
                    "doc_id": item.get("doc_id", ""),
                    "score": float(score),
                    "source": "graph",
                    "metadata": {
                        "title": item.get("title", ""),
                        "matched_keyword": item.get("matched_keyword", ""),
                    },
                })

        return results

    # ------------------------------------------------------------------
    # BM25 关键词检索
    # ------------------------------------------------------------------

    def _keyword_search(self, query: str, top_k: int = 10) -> list[dict]:
        """
        BM25 关键词检索：使用 rank_bm25 对 chunk 语料库进行词频匹配。

        首次调用时自动从 ChromaDB 构建 BM25 索引，后续调用复用。
        """
        # 确保 BM25 索引已构建
        self._ensure_bm25_index()

        if self._bm25 is None or not self._bm25_chunks:
            logger.warning("BM25 索引为空，跳过关键词检索")
            return []

        # 对查询进行分词
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # BM25 打分
        scores = self._bm25.get_scores(query_tokens)

        # 取 top_k
        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        top_results = indexed_scores[:top_k]

        # 归一化分数到 [0, 1] 区间
        max_score = max(s for _, s in top_results) if top_results else 1.0
        if max_score <= 0:
            max_score = 1.0

        results = []
        for idx, score in top_results:
            if score <= 0:
                continue
            chunk = self._bm25_chunks[idx]
            results.append({
                "chunk_id": chunk.get("chunk_id", f"bm25_{idx}"),
                "content": chunk.get("content", ""),
                "doc_id": chunk.get("doc_id", ""),
                "score": round(score / max_score, 4),  # 归一化
                "source": "keyword",
                "metadata": chunk.get("metadata", {}),
            })

        return results

    # ------------------------------------------------------------------
    # 加权合并排序
    # ------------------------------------------------------------------

    def _merge_results(
        self,
        vector_results: list[dict],
        graph_results: list[dict],
        keyword_results: list[dict],
        vector_weight: float,
        graph_weight: float,
        keyword_weight: float,
    ) -> list[dict]:
        """
        加权合并三路检索结果。

        以 chunk_id 为唯一键，每条结果按其来源的权重加权累加分数，
        最后按综合分数降序排列。

        默认权重: vector=0.4, graph=0.35, keyword=0.25
        """
        # chunk_id -> 加权分数
        scores: dict[str, float] = defaultdict(float)
        # chunk_id -> 最完整的记录（优先使用有 content 的那个）
        content_map: dict[str, dict] = {}

        def _accumulate(items: list[dict], weight: float) -> None:
            for item in items:
                key = item.get("chunk_id")
                if not key:
                    continue
                scores[key] += item.get("score", 0.0) * weight
                # 保留信息最丰富的记录
                if key not in content_map:
                    content_map[key] = item
                else:
                    existing = content_map[key]
                    # 如果已有记录没有 content 而新记录有，则替换
                    if not existing.get("content") and item.get("content"):
                        content_map[key] = item

        _accumulate(vector_results, vector_weight)
        _accumulate(graph_results, graph_weight)
        _accumulate(keyword_results, keyword_weight)

        # 按综合分数降序排列
        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        merged = []
        for chunk_id, score in sorted_items:
            item = content_map[chunk_id].copy()
            item["score"] = round(score, 4)
            merged.append(item)

        return merged

    # ------------------------------------------------------------------
    # BM25 索引构建
    # ------------------------------------------------------------------

    def _ensure_bm25_index(self) -> None:
        """延迟构建 BM25 索引：从 ChromaDB 拉取所有 chunk 并建立倒排索引。"""
        if self._bm25 is not None:
            return

        logger.info("构建 BM25 索引...")

        try:
            # 从 ChromaDB 获取所有 chunk
            all_data = self.vector_store.collection.get(
                include=["documents", "metadatas"]
            )
        except Exception as e:
            logger.error(f"BM25 索引构建失败: 无法读取 ChromaDB: {e}")
            return

        if not all_data or not all_data.get("ids"):
            logger.warning("ChromaDB 中无数据，BM25 索引为空")
            return

        ids = all_data["ids"]
        documents = all_data.get("documents", [])
        metadatas = all_data.get("metadatas", [])

        # 构建语料库
        tokenized_corpus = []
        chunks = []

        for i, doc_id in enumerate(ids):
            content = documents[i] if i < len(documents) else ""
            meta = metadatas[i] if i < len(metadatas) else {}

            tokens = self._tokenize(content)
            tokenized_corpus.append(tokens)
            chunks.append({
                "chunk_id": doc_id,
                "content": content,
                "doc_id": meta.get("doc_id", ""),
                "metadata": meta,
            })

        if tokenized_corpus:
            self._bm25 = BM25Okapi(tokenized_corpus)
            self._bm25_corpus = tokenized_corpus
            self._bm25_chunks = chunks
            logger.info(f"BM25 索引构建完成: {len(chunks)} 个 chunk")
        else:
            logger.warning("BM25 语料库为空")

    def rebuild_bm25_index(self) -> int:
        """
        手动重建 BM25 索引（添加新文档后调用）。

        Returns:
            int: 索引中的 chunk 数量
        """
        self._bm25 = None
        self._ensure_bm25_index()
        return len(self._bm25_chunks)

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """
        中文分词：使用 jieba 分词，过滤停用词和单字符。
        """
        if not text:
            return []
        words = jieba.lcut(text)
        # 过滤：去除空白、单字符、纯数字、纯标点
        return [w.strip() for w in words if len(w.strip()) > 1 and not w.strip().isspace()]
