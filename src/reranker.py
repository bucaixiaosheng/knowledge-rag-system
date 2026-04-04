"""
重排序模块：用LLM对检索结果进行精排
"""
import json
import logging
from openai import OpenAI
from src.config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL

logger = logging.getLogger(__name__)


class Reranker:
    """基于LLM的重排序"""

    RERANK_PROMPT = """请根据查询问题，对以下文档片段进行相关性评分（0-10分）。

查询：{query}

文档片段：
{chunks}

请以JSON数组格式返回评分结果：
[{{"index": 0, "score": 8, "reason": "直接回答了问题"}}, ...]

只返回JSON数组。"""

    def __init__(self):
        self.client = OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
        )
        self.model = LLM_MODEL

    def rerank(self, query: str, results: list[dict], top_k: int = 5) -> list[dict]:
        """
        基于LLM对检索结果进行精排（0-10分评分）。
        - 取 top-15 结果送入 LLM 评分
        - 按 rerank_score 降序排序
        - 异常时返回原始 top_k 结果（不中断调用链）
        - 每条结果含 rerank_score 字段
        """
        if not results:
            return []

        if len(results) <= top_k:
            # 结果数不足，直接补 rerank_score 并返回
            for item in results:
                item.setdefault("rerank_score", item.get("score", 0))
            return results

        # 准备片段（取前15条送LLM评分）
        chunks_text = ""
        for i, item in enumerate(results[:15]):
            chunks_text += f"\n[{i}] {item['content'][:300]}\n"

        prompt = self.RERANK_PROMPT.format(query=query, chunks=chunks_text)

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=1000,
            )
            content = resp.choices[0].message.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]

            scores = json.loads(content)
            score_map = {s["index"]: s["score"] for s in scores}

            for i, item in enumerate(results[:15]):
                if i in score_map:
                    item["rerank_score"] = score_map[i]
                else:
                    item["rerank_score"] = 0

            # 按 rerank_score 降序排序
            results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
            return results[:top_k]

        except Exception as e:
            logger.error(f"重排序失败: {e}")
            # 异常时返回原始 top_k 结果
            return results[:top_k]
