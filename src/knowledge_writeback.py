"""
知识回存模块：将高质量RAG回答自动回存到知识图谱

职责：
  - assess_quality(): 评估答案质量(0-1)
  - extract_keywords_from_answer(): 用jieba提取关键词
  - should_writeback(): 根据阈值判断是否回存
  - check_duplicate(): 用embedding余弦相似度判断重复
  - writeback(): 完整回存流程
"""
import hashlib
import logging
import re
from datetime import datetime
from typing import Optional

import numpy as np

from src.config import WRITEBACK_THRESHOLD, WRITEBACK_DEDUP_THRESHOLD

logger = logging.getLogger(__name__)

# 模板化回答的前缀模式（非模板化得0.2分的反面）
TEMPLATE_PATTERNS = [
    r"^根据上下文",
    r"^根据提供的信息",
    r"^根据文档",
    r"^根据资料",
    r"^根据已有信息",
    r"^抱歉[，,]",
    r"^很抱歉",
    r"^我没有找到",
    r"^上下文中没有",
    r"^提供的上下文中没有",
]

# 具体事实关键词模式（数字、日期、专有名词）
FACT_PATTERNS = [
    r"\d{4}年",          # 2024年
    r"\d{1,2}月",        # 3月
    r"\d{1,2}日",        # 15日
    r"\d+\.?\d*%",       # 3.14%
    r"\d+\.?\d*亿",      # 1.5亿
    r"\d+\.?\d*万",      # 10万
    r"\d+\.?\d*元",      # 100元
    r"\d+美元",           # 100美元
    r"[\u4e00-\u9fff]{2,}(公司|集团|机构|大学|研究院)",  # 专有名词+机构
    r"(叫做|称为|名为|是指)",    # 定义性语句
]


class KnowledgeWriteback:
    """知识回存引擎

    将高质量的RAG回答自动回存到知识图谱，形成DerivedKnowledge节点。

    使用示例::

        kg = KnowledgeGraph()
        emb = EmbeddingEngine()
        wb = KnowledgeWriteback(kg, emb)

        result = wb.writeback(
            query="什么是RAG？",
            answer="RAG是检索增强生成技术...",
            sources=[{"doc_id": "xxx", "title": "xxx"}],
            context_chunks=[{"chunk_id": "yyy", ...}],
        )
    """

    def __init__(self, knowledge_graph, embedding_engine):
        """
        Args:
            knowledge_graph: KnowledgeGraph 实例
            embedding_engine: EmbeddingEngine 实例
        """
        self.kg = knowledge_graph
        self.emb_engine = embedding_engine

    def assess_quality(self, query: str, answer: str, sources: list[dict]) -> float:
        """评估答案质量(0-1)

        评分规则:
          - 答案长度>100字: +0.2
          - 多来源引用(>=2): +0.3
          - 包含具体事实关键词: +0.3
          - 非模板化回答: +0.2

        Args:
            query: 用户查询
            answer: LLM生成的回答
            sources: 引用来源列表

        Returns:
            质量分数 (0.0 ~ 1.0)
        """
        score = 0.0

        # 1. 答案长度 > 100字 → +0.2
        if len(answer) > 100:
            score += 0.2
            logger.debug(f"质量评估: 答案长度{len(answer)}>100字, +0.2")

        # 2. 多来源引用(>=2) → +0.3
        if sources and len(sources) >= 2:
            score += 0.3
            logger.debug(f"质量评估: {len(sources)}个来源引用>=2, +0.3")

        # 3. 包含具体事实关键词 → +0.3
        fact_match_count = 0
        for pattern in FACT_PATTERNS:
            if re.search(pattern, answer):
                fact_match_count += 1
        if fact_match_count >= 1:
            score += 0.3
            logger.debug(f"质量评估: 匹配{fact_match_count}个事实模式, +0.3")

        # 4. 非模板化回答 → +0.2
        is_template = False
        for pattern in TEMPLATE_PATTERNS:
            if re.search(pattern, answer):
                is_template = True
                break
        if not is_template:
            score += 0.2
            logger.debug(f"质量评估: 非模板化回答, +0.2")

        score = min(score, 1.0)
        logger.info(f"答案质量评估: {score:.2f} (长度={len(answer)}, 来源={len(sources) if sources else 0})")
        return score

    def extract_keywords_from_answer(self, answer: str) -> list[str]:
        """用jieba提取关键词

        Args:
            answer: LLM生成的回答

        Returns:
            关键词列表（去重后，最多10个）
        """
        try:
            import jieba
            import jieba.analyse
        except ImportError:
            logger.warning("jieba未安装，使用简单分词回退")
            # 简单回退：按空格和标点分词，取长度>2的词
            words = re.findall(r"[\u4e00-\u9fff]{2,}", answer)
            return list(set(words))[:10]

        keywords = jieba.analyse.extract_tags(answer, topK=10, withWeight=False)
        return keywords

    def should_writeback(self, quality_score: float) -> bool:
        """根据阈值判断是否回存

        Args:
            quality_score: 答案质量分数

        Returns:
            是否应该回存
        """
        threshold = WRITEBACK_THRESHOLD
        result = quality_score >= threshold
        logger.info(f"回存判断: quality={quality_score:.2f} >= threshold={threshold} → {result}")
        return result

    def check_duplicate(self, query_embedding: list[float]) -> bool:
        """用embedding余弦相似度判断是否重复

        Args:
            query_embedding: 查询文本的embedding向量

        Returns:
            True=已存在重复（不应回存），False=不重复（可以回存）
        """
        threshold = WRITEBACK_DEDUP_THRESHOLD

        # 检索已有的DerivedKnowledge
        existing = self.kg.search_derived_knowledge(query_embedding, top_k=5)
        if not existing:
            return False

        # 获取已有DK的embedding进行相似度比较
        # 由于DK节点的embedding可能存储在ChromaDB中，
        # 这里通过问题的embedding做粗筛
        existing_questions = [dk.get("question", "") for dk in existing if dk.get("question")]
        if not existing_questions:
            return False

        # 计算已有问题的embedding
        existing_embeddings = self.emb_engine.embed_texts(existing_questions)
        query_emb = np.array(query_embedding)

        for emb in existing_embeddings:
            existing_emb = np.array(emb)
            # cosine similarity（embed_texts已normalize）
            sim = float(np.dot(query_emb, existing_emb))
            if sim > threshold:
                logger.info(f"发现重复知识: similarity={sim:.4f} > threshold={threshold}")
                return True

        return False

    def writeback(
        self,
        query: str,
        answer: str,
        sources: list[dict],
        context_chunks: list[dict],
    ) -> dict:
        """完整回存流程

        流程: 评估质量 → 提取关键词 → 去重检查 → 生成dk_id → 创建节点 → 关联来源

        Args:
            query: 用户查询
            answer: LLM生成的回答
            sources: 引用来源列表 [{doc_id, title, score}]
            context_chunks: 检索结果chunk列表 [{chunk_id, content, doc_id, ...}]

        Returns:
            {status: "written"|"skipped", dk_id?, reason?}
        """
        # Step 1: 评估答案质量
        quality_score = self.assess_quality(query, answer, sources)

        # Step 2: 判断是否达到回存阈值
        if not self.should_writeback(quality_score):
            return {
                "status": "skipped",
                "reason": f"quality_score({quality_score:.2f}) < threshold({WRITEBACK_THRESHOLD})",
                "quality_score": quality_score,
            }

        # Step 3: 去重检查
        query_embedding = self.emb_engine.embed_query(query)
        if self.check_duplicate(query_embedding):
            return {
                "status": "skipped",
                "reason": "duplicate_detected",
                "quality_score": quality_score,
            }

        # Step 4: 提取关键词
        keywords = self.extract_keywords_from_answer(answer)

        # Step 5: 生成dk_id (md5 of query+answer)
        dk_id = hashlib.md5(f"{query}:{answer[:200]}".encode("utf-8")).hexdigest()[:16]

        # Step 6: 提取来源信息
        source_doc_ids = list(set(
            s.get("doc_id", "") for s in sources if s.get("doc_id")
        ))
        source_chunk_ids = list(set(
            c.get("chunk_id", "") for c in context_chunks if c.get("chunk_id")
        ))

        # 确定领域（取第一个来源的domain或默认空）
        domain = ""
        if context_chunks:
            metadata = context_chunks[0].get("metadata", {})
            if isinstance(metadata, dict):
                domain = metadata.get("domain", "")

        # Step 7: 创建DerivedKnowledge节点
        now = datetime.utcnow().isoformat()
        dk_data = {
            "dk_id": dk_id,
            "question": query,
            "answer": answer,
            "quality_score": quality_score,
            "source_doc_ids": source_doc_ids,
            "source_chunk_ids": source_chunk_ids,
            "keywords": keywords,
            "domain": domain,
            "created_at": now,
        }
        self.kg.create_derived_knowledge(dk_data)

        # Step 8: 关联来源
        self.kg.link_derived_to_sources(dk_id, source_doc_ids, source_chunk_ids)

        # Step 9: 关联锚关键词
        if keywords:
            self.kg.link_derived_to_anchors(dk_id, keywords)

        # Step 10: 关联领域
        if domain:
            self.kg.link_derived_to_domain(dk_id, domain)

        logger.info(
            f"知识回存成功: {dk_id} | quality={quality_score:.2f} | "
            f"keywords={len(keywords)} | docs={len(source_doc_ids)} | chunks={len(source_chunk_ids)}"
        )

        return {
            "status": "written",
            "dk_id": dk_id,
            "quality_score": quality_score,
            "keywords": keywords,
        }
