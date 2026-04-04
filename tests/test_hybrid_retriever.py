"""
测试混合检索模块（单元测试，不依赖外部服务）
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock 外部依赖，避免实际连接 ChromaDB / Neo4j
import unittest
from unittest.mock import MagicMock, patch


class TestHybridRetriever(unittest.TestCase):
    """HybridRetriever 单元测试"""

    def _make_retriever(self):
        """构造 HybridRetriever，注入 mock 依赖"""
        with patch("src.hybrid_retriever.VectorStore"), \
             patch("src.hybrid_retriever.KnowledgeGraph"), \
             patch("src.hybrid_retriever.EntityExtractor"), \
             patch("src.hybrid_retriever.embedding_engine"):
            from src.hybrid_retriever import HybridRetriever
            vs = MagicMock()
            kg = MagicMock()
            ext = MagicMock()
            retriever = HybridRetriever(vs, kg, ext)
            return retriever

    def test_merge_results_basic(self):
        """测试三路结果加权合并"""
        retriever = self._make_retriever()

        vector_results = [
            {"chunk_id": "c1", "content": "向量结果1", "doc_id": "d1", "score": 0.9},
            {"chunk_id": "c2", "content": "向量结果2", "doc_id": "d1", "score": 0.7},
            {"chunk_id": "c3", "content": "向量结果3", "doc_id": "d2", "score": 0.5},
        ]

        graph_results = [
            {"chunk_id": "c1", "content": "图谱命中c1", "doc_id": "d1", "score": 0.8, "source": "graph"},
            {"chunk_id": "c4", "content": "图谱独有结果", "doc_id": "d3", "score": 0.6, "source": "graph"},
        ]

        keyword_results = [
            {"chunk_id": "c2", "content": "关键词命中c2", "doc_id": "d1", "score": 0.85, "source": "keyword"},
            {"chunk_id": "c5", "content": "关键词独有结果", "doc_id": "d4", "score": 0.4, "source": "keyword"},
        ]

        merged = retriever._merge_results(
            vector_results, graph_results, keyword_results,
            vector_weight=0.4, graph_weight=0.35, keyword_weight=0.25,
        )

        # c1: 0.9*0.4 + 0.8*0.35 = 0.36 + 0.28 = 0.64
        # c2: 0.7*0.4 + 0.85*0.25 = 0.28 + 0.2125 = 0.4925
        # c3: 0.5*0.4 = 0.20
        # c4: 0.6*0.35 = 0.21
        # c5: 0.4*0.25 = 0.10

        self.assertEqual(len(merged), 5)
        # c1 应该排第一（最高分）
        self.assertEqual(merged[0]["chunk_id"], "c1")
        self.assertAlmostEqual(merged[0]["score"], 0.64, places=3)

        # c4 和 c2 排第二/第三
        self.assertIn(merged[1]["chunk_id"], ["c2", "c4"])

        # 每条结果都有 score 和 source 字段
        for item in merged:
            self.assertIn("score", item)
            self.assertIn("chunk_id", item)

    def test_retrieve_calls_three_paths(self):
        """测试 retrieve 方法正确调用三路检索"""
        retriever = self._make_retriever()

        # Mock 三路检索方法
        retriever.vector_store.search.return_value = [
            {"chunk_id": "v1", "content": "test", "doc_id": "d1", "score": 0.8, "metadata": {}},
        ]
        retriever._graph_enhanced_search = MagicMock(return_value=[])
        retriever._keyword_search = MagicMock(return_value=[])

        results = retriever.retrieve("测试查询", top_k=5)

        retriever.vector_store.search.assert_called_once_with("测试查询", top_k=10)
        retriever._graph_enhanced_search.assert_called_once_with("测试查询", top_k=5)
        retriever._keyword_search.assert_called_once_with("测试查询", top_k=5)

        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["chunk_id"], "v1")

    def test_retrieve_default_weights(self):
        """测试默认权重: vector=0.4, graph=0.35, keyword=0.25"""
        from src.hybrid_retriever import DEFAULT_VECTOR_WEIGHT, DEFAULT_GRAPH_WEIGHT, DEFAULT_KEYWORD_WEIGHT
        self.assertAlmostEqual(DEFAULT_VECTOR_WEIGHT, 0.4)
        self.assertAlmostEqual(DEFAULT_GRAPH_WEIGHT, 0.35)
        self.assertAlmostEqual(DEFAULT_KEYWORD_WEIGHT, 0.25)

    def test_tokenize_chinese(self):
        """测试中文分词"""
        from src.hybrid_retriever import HybridRetriever
        tokens = HybridRetriever._tokenize("知识图谱是一种图数据库技术")
        self.assertIsInstance(tokens, list)
        self.assertGreater(len(tokens), 0)
        # 单字符应被过滤
        for t in tokens:
            self.assertGreater(len(t), 1)

    def test_empty_query(self):
        """测试空查询"""
        retriever = self._make_retriever()
        retriever.vector_store.search.return_value = []
        retriever._graph_enhanced_search = MagicMock(return_value=[])
        retriever._keyword_search = MagicMock(return_value=[])

        results = retriever.retrieve("", top_k=5)
        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()
