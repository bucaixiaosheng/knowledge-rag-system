"""
RAG对话模块：完整RAG流程（检索 → 重排 → 构建Prompt → LLM生成）

职责：
  - chat():  完整RAG流程，返回 {answer, sources, context_count}
  - clear_history(): 清空对话历史
  - 多轮历史管理：最多保留10轮（20条消息）
  - 上下文严格来自检索结果，禁止编造
"""
import logging
from typing import Optional

from openai import OpenAI

from src.config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SYSTEM_PROMPT — 基于检索结果回答，不编造
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """你是一个专业的知识助手。请根据提供的上下文信息回答用户的问题。

规则：
1. 只基于提供的上下文回答，不要编造信息
2. 如果上下文中没有相关信息，明确告知用户
3. 引用来源时标注文档标题
4. 回答要简洁准确

上下文信息：
{context}"""

# 对话历史最大轮数（1轮 = 1 user + 1 assistant = 2条消息）
MAX_HISTORY_ROUNDS = 10
MAX_HISTORY_MESSAGES = MAX_HISTORY_ROUNDS * 2  # 20 条消息


class RAGChat:
    """RAG对话引擎

    完整 RAG 流程：
      用户查询 → 多路检索 → 重排序 → 构建 Prompt → LLM 生成回答

    使用示例::

        retriever = HybridRetriever(vector_store, knowledge_graph, entity_extractor)
        rag = RAGChat(retriever)

        result = rag.chat("什么是RAG？")
        print(result["answer"])
        print(result["sources"])
        print(result["context_count"])

        rag.clear_history()  # 清空历史
    """

    def __init__(self, retriever=None, reranker=None, writeback_engine=None):
        """
        Args:
            retriever: 混合检索器实例（HybridRetriever 或兼容接口）。
                       必须提供 ``retrieve(query, top_k)`` 方法，
                       返回 ``[{chunk_id, content, doc_id, score, source, metadata}]``。
            reranker:  重排序器实例（Reranker 或兼容接口）。
                       必须提供 ``rerank(query, results, top_k)`` 方法。
                       若为 None，则使用内置的简单重排序（按原始 score 降序）。
        """
        self.retriever = retriever
        self.reranker = reranker
        self.writeback_engine = writeback_engine
        self.llm = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        self.history: list[dict] = []  # 对话历史 [{role, content}, ...]

    # ------------------------------------------------------------------
    # 核心方法
    # ------------------------------------------------------------------

    def chat(self, query: str, top_k: int = 5) -> dict:
        """完整 RAG 对话流程

        流程：检索 → 重排 → 构建 Prompt → LLM 生成

        Args:
            query: 用户查询文本
            top_k: 最终返回给 LLM 的上下文条数

        Returns:
            {
                "answer": str,        # LLM 生成的回答
                "sources": list[dict],# 引用来源 [{doc_id, title, score}]
                "context_count": int  # 使用的上下文条数
            }
        """
        # ---- Step 1: 检索 ----
        results = self._retrieve(query, top_k=top_k * 2)
        logger.info("检索返回 %d 条结果", len(results))

        # ---- Step 2: 重排序 ----
        results = self._rerank(query, results, top_k=top_k)
        logger.info("重排序后保留 %d 条结果", len(results))

        # ---- Step 3: 构建上下文 ----
        context_parts: list[str] = []
        sources: list[dict] = []

        for i, item in enumerate(results):
            title = item.get("metadata", {}).get("title", item.get("doc_id", ""))
            context_parts.append(f"[{i + 1}] 来源: {title}\n{item['content']}")
            sources.append({
                "doc_id": item.get("doc_id", ""),
                "title": title,
                "score": item.get("score", 0),
            })

        context = "\n\n".join(context_parts)

        # ---- Step 4: 构建 Prompt + 多轮历史 ----
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
        ]
        messages.extend(self.history)
        messages.append({"role": "user", "content": query})

        # ---- Step 5: LLM 生成 ----
        answer = self._generate(messages)

        # ---- Step 6: 更新历史 ----
        self.history.append({"role": "user", "content": query})
        self.history.append({"role": "assistant", "content": answer})

        # 保持历史在 MAX_HISTORY_MESSAGES 以内（保留最近的消息）
        if len(self.history) > MAX_HISTORY_MESSAGES:
            self.history = self.history[-MAX_HISTORY_MESSAGES:]

        # ---- Step 7: 知识回存（非阻塞） ----
        if self.writeback_engine:
            try:
                wb_result = self.writeback_engine.writeback(query, answer, sources, results)
                if wb_result.get("status") == "written":
                    logger.info(f"知识回存成功: {wb_result['dk_id']}")
            except Exception as e:
                logger.warning(f"知识回存失败(不影响回答): {e}")

        return {
            "answer": answer,
            "sources": sources,
            "context_count": len(results),
        }

    def clear_history(self) -> None:
        """清空对话历史"""
        self.history = []
        logger.info("对话历史已清空")

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _retrieve(self, query: str, top_k: int = 10) -> list[dict]:
        """执行检索（多路混合检索）

        如果 retriever 不可用，返回空列表（LLM 会回答"没有找到相关信息"）。
        """
        if self.retriever is None:
            logger.warning("检索器未设置，无法执行检索")
            return []

        try:
            return self.retriever.retrieve(query, top_k=top_k)
        except Exception as e:
            logger.error("检索失败: %s", e)
            return []

    def _rerank(self, query: str, results: list[dict], top_k: int = 5) -> list[dict]:
        """对检索结果重排序

        优先使用外部 reranker（LLM 精排），否则按原始 score 降序排列。
        """
        if not results:
            return []

        if len(results) <= top_k:
            return results

        if self.reranker is not None:
            try:
                return self.reranker.rerank(query, results, top_k=top_k)
            except Exception as e:
                logger.warning("重排序失败，使用原始排序: %s", e)

        # 兜底：按 score 降序
        return sorted(results, key=lambda x: x.get("score", 0), reverse=True)[:top_k]

    def _generate(self, messages: list[dict]) -> str:
        """调用 LLM 生成回答"""
        try:
            resp = self.llm.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=0.3,
                max_tokens=2000,
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.error("LLM 生成失败: %s", e)
            return f"抱歉，生成回答时出错：{e}"

    # ------------------------------------------------------------------
    # 辅助属性
    # ------------------------------------------------------------------

    @property
    def history_length(self) -> int:
        """当前历史消息数"""
        return len(self.history)

    @property
    def history_rounds(self) -> int:
        """当前历史轮数"""
        return len(self.history) // 2

    def __repr__(self) -> str:
        return (
            f"RAGChat(retriever={self.retriever!r}, "
            f"history_rounds={self.history_rounds}/{MAX_HISTORY_ROUNDS})"
        )
