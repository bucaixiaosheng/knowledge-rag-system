"""
实体抽取模块：使用LLM从文本中提取实体、关系和丰富的锚关键词
"""
import json
import logging
import re
from openai import OpenAI
import json_repair
from src.config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL

logger = logging.getLogger(__name__)

# LLM调用超时秒数，防止进程hang住被SIGKILL
_LLM_TIMEOUT = 120


class EntityExtractor:
    """基于LLM的实体抽取"""

    EXTRACTION_PROMPT_TEMPLATE = """你是一个专业的知识图谱构建助手。请从以下文本中提取实体、关系和丰富的锚关键词。

要求：
1. 实体类型包括：人物、组织、地点、技术/软件、概念/术语、产品、事件
2. 关系类型包括：相关、属于、使用、位于、包含、创建、参与
3. 每个实体必须有明确的类型
4. 只提取文本中明确提到的内容
5. **锚关键词（anchor_keywords）是最重要的！必须提取10-20个，覆盖：技术名词、产品名、项目名、工具名、公司名、人名、框架名、协议名、核心概念**
   每个关键词要有importance权重（0.5-1.0）

请以JSON格式返回：
{{
  "entities": [{{"name": "实体名", "entity_type": "实体类型", "description": "简短描述"}}],
  "relations": [{{"source": "实体名1", "target": "实体名2", "relation_type": "关系类型", "properties": {{}}}}],
  "concepts": [{{"name": "概念名", "description": "概念描述", "category": "分类"}}],
  "anchor_keywords": [{{"keyword": "关键术语", "importance": 0.9}}],
  "tags": ["标签1", "标签2"],
  "summary": "文本摘要（50字以内）"
}}
只返回JSON，不要其他内容。

文本：
{text}
"""

    def __init__(self):
        self.client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        self.model = LLM_MODEL

    # 返回格式的空结果常量
    _EMPTY_RESULT = {
        "entities": [],
        "relations": [],
        "concepts": [],
        "anchor_keywords": [],
        "tags": [],
        "summary": "",
    }

    def _parse_json_robust(self, content: str, label: str = "") -> dict | list | None:
        """多级JSON解析策略：json.loads → json_repair → 优雅降级"""
        # 1. 提取JSON块（处理markdown代码块包裹）
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        content = content.strip()

        # 2. 找到最外层的 { 或 [ 并截取
        for opener, closer in [("{", "}"), ("[", "]")]:
            start = content.find(opener)
            if start >= 0:
                content = content[start:]
                break

        # 3. 标准解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 4. 快速regex修补（尾逗号等）
        try:
            fixed = re.sub(r',\s*}', '}', content)
            fixed = re.sub(r',\s*]', ']', fixed)
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # 5. json_repair 库（处理未终止字符串、截断JSON、特殊字符等）
        try:
            repaired = json_repair.loads(content)
            logger.info(f"[{label}] json_repair 修复成功")
            return repaired
        except Exception as e:
            logger.warning(f"[{label}] json_repair 也失败: {e}")

        # 6. 尝试暴力截断修复：从尾部逐步删除字符直到能解析
        for i in range(1, min(200, len(content))):
            try:
                return json.loads(content[:-i])
            except json.JSONDecodeError:
                continue

        logger.error(f"[{label}] 所有JSON修复策略均失败，优雅降级返回空结果")
        return None

    def extract(self, text: str) -> dict:
        """
        从文本中提取实体、关系、概念和锚关键词。

        Args:
            text: 输入文本

        Returns:
            dict: {
                entities: [{name, entity_type, description}],
                relations: [{source, target, relation_type, properties}],
                concepts: [{name, description, category}],
                anchor_keywords: [{keyword, importance}],
                tags: [str],
                summary: str
            }
        """
        prompt = self.EXTRACTION_PROMPT_TEMPLATE.format(text=text[:3000])
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=4000,
                timeout=_LLM_TIMEOUT,
            )
            content = resp.choices[0].message.content.strip()

            result = self._parse_json_robust(content, label="extract")
            if result is None or not isinstance(result, dict):
                logger.error("extract: JSON解析最终失败，返回空结果")
                return dict(self._EMPTY_RESULT)

            # 确保所有必要字段存在
            for key in self._EMPTY_RESULT:
                result.setdefault(key, self._EMPTY_RESULT[key])

            ak_count = len(result["anchor_keywords"])
            if ak_count < 5:
                logger.warning(f"锚关键词数量偏少 ({ak_count}个)，可能遗漏重要信息")
            logger.info(
                f"抽取完成: {len(result.get('entities', []))} 实体, "
                f"{len(result.get('concepts', []))} 概念, {ak_count} 锚关键词"
            )
            return result
        except Exception as e:
            logger.error(f"实体抽取失败: {e}")
            return dict(self._EMPTY_RESULT)

    def extract_anchor_keywords_only(self, content: str, doc_title: str) -> list[dict]:
        """
        单独提取锚关键词（10-25个），覆盖所有类型的实体名称。

        Args:
            content: 文档内容
            doc_title: 文档标题

        Returns:
            list[dict]: [{"keyword": "xxx", "importance": 0.9}]
        """
        prompt = f"""从以下文本中提取所有关键术语作为锚关键词。
要求：提取10-25个关键词，覆盖：技术名词、产品名、公司名、人名、框架名、协议名、概念术语、工具名。只提取文本中明确提到的内容。
文档标题：{doc_title}
文档内容：
{content[:4000]}
返回JSON数组：[{{"keyword": "xxx", "importance": 0.9}}]"""
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2000,
                timeout=_LLM_TIMEOUT,
            )
            c = resp.choices[0].message.content.strip()
            kws = self._parse_json_robust(c, label="anchor_keywords")
            if kws is None or not isinstance(kws, list):
                logger.error("anchor_keywords: JSON解析最终失败，返回空列表")
                return []
            logger.info(f"单独提取锚关键词: {len(kws)} 个")
            return kws
        except Exception as e:
            logger.error(f"锚关键词提取失败: {e}")
            return []
