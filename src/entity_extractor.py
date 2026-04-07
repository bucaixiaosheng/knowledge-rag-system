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

# [deprecated] 旧常量，保留用于向后兼容
BATCH_MAX_CHARS = 30000

# 每批合并的最大字符数
BATCH_CHUNK_SIZE = 15000
# 单个chunk超过此字符数时，独占一个batch
SINGLE_CHUNK_THRESHOLD = 5000


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

    def extract_anchor_keywords_batch(self, chunks: list[dict], doc_title: str) -> list[dict]:
        """
        分批合并策略提取锚关键词：将chunk按字符数分组合并，每组合并为一次LLM调用。

        分组规则：
        - 每批累积字符数不超过 BATCH_CHUNK_SIZE (15000)
        - 单个chunk超过 SINGLE_CHUNK_THRESHOLD (5000) 时独占一个batch
        - 合并所有batch结果后去重，取最高importance

        Args:
            chunks: list[dict]，每个 dict 含 content 字段
            doc_title: 文档标题

        Returns:
            list[dict]: [{"keyword": "xxx", "importance": 0.9}]
        """
        try:
            if not chunks:
                return []

            # === 分组算法 ===
            batches: list[list[dict]] = []
            current_batch: list[dict] = []
            current_batch_chars = 0

            for chunk in chunks:
                content = chunk.get("content", "")
                # a. 空内容跳过
                if not content or not content.strip():
                    continue
                chunk_len = len(content)

                # b. 大chunk独占batch
                if chunk_len > SINGLE_CHUNK_THRESHOLD:
                    if current_batch:
                        batches.append(current_batch)
                        current_batch = []
                        current_batch_chars = 0
                    batches.append([chunk])
                    logger.debug(
                        f"大chunk独占batch: {chunk_len} 字符 > SINGLE_CHUNK_THRESHOLD={SINGLE_CHUNK_THRESHOLD}"
                    )
                    continue

                # c. 普通chunk：检查是否需要封存当前batch
                if current_batch_chars + chunk_len >= BATCH_CHUNK_SIZE:
                    if current_batch:
                        batches.append(current_batch)
                    current_batch = [chunk]
                    current_batch_chars = chunk_len
                else:
                    current_batch.append(chunk)
                    current_batch_chars += chunk_len

            # 封存最后一个batch
            if current_batch:
                batches.append(current_batch)

            total_batches = len(batches)
            total_chunks = sum(len(b) for b in batches)
            logger.info(
                f"分批合并: {total_chunks} 个有效chunk分为 {total_batches} 批"
            )

            if not batches:
                return []

            # === 逐batch LLM调用 ===
            all_results: list[dict] = []
            for batch_idx, batch in enumerate(batches, 1):
                batch_chars = sum(len(c.get("content", "")) for c in batch)
                combined = "\n\n---CHUNK_BOUNDARY---\n\n".join(
                    c["content"] for c in batch if c.get("content")
                )
                logger.info(
                    f"批次 {batch_idx}/{total_batches}: "
                    f"{len(batch)} 个chunk, {batch_chars} 字符"
                )

                prompt = f"""从以下多段文本中提取所有关键术语作为锚关键词。
这些文本来自同一份文档（标题：{doc_title}），被分为多个段落（用 ---CHUNK_BOUNDARY--- 分隔）。
请综合所有段落的内容，提取10-25个关键词，覆盖：技术名词、产品名、公司名、人名、框架名、协议名、概念术语、工具名。只提取文本中明确提到的内容。

文本内容：
{combined}

返回JSON数组：[{{"keyword": "xxx", "importance": 0.9}}]"""

                try:
                    resp = self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.1,
                        max_tokens=2000,
                        timeout=_LLM_TIMEOUT,
                    )
                    c = resp.choices[0].message.content or ""
                    c = c.strip()
                    logger.info(
                        f"批次 {batch_idx}/{total_batches}: "
                        f"LLM返回内容长度={len(c)} 字符"
                    )
                    kws = self._parse_json_robust(c, label=f"anchor_keywords_batch_{batch_idx}")

                    # 检测空返回 / 非法结果
                    if kws is None or not isinstance(kws, list) or len(kws) == 0:
                        raw_preview = c[:200] if c else "<空>"
                        logger.warning(
                            f"批次 {batch_idx}/{total_batches}: "
                            f"LLM返回为空或解析失败 (type={type(kws).__name__}), "
                            f"原始内容前200字符: {raw_preview}"
                        )

                        # === Fallback: 用简化prompt重试 ===
                        logger.info(
                            f"批次 {batch_idx}/{total_batches}: "
                            f"开始fallback重试（截取前3000字符）"
                        )
                        try:
                            fallback_prompt = (
                                f"从以下文本摘要中提取5-15个关键术语。"
                                f"只返回JSON数组：[{{\"keyword\": \"xxx\", \"importance\": 0.9}}]。"
                                f"文本摘要：{combined[:3000]}"
                            )
                            fb_resp = self.client.chat.completions.create(
                                model=self.model,
                                messages=[{"role": "user", "content": fallback_prompt}],
                                temperature=0.1,
                                max_tokens=1000,
                                timeout=_LLM_TIMEOUT,
                            )
                            fb_content = fb_resp.choices[0].message.content or ""
                            fb_content = fb_content.strip()
                            logger.info(
                                f"批次 {batch_idx}/{total_batches} fallback: "
                                f"返回内容长度={len(fb_content)} 字符"
                            )
                            fb_kws = self._parse_json_robust(
                                fb_content, label=f"anchor_keywords_batch_{batch_idx}_fallback"
                            )
                            if fb_kws and isinstance(fb_kws, list) and len(fb_kws) > 0:
                                all_results.extend(fb_kws)
                                logger.info(
                                    f"批次 {batch_idx}/{total_batches} fallback: "
                                    f"成功提取 {len(fb_kws)} 个关键词"
                                )
                            else:
                                logger.warning(
                                    f"批次 {batch_idx}/{total_batches} fallback: "
                                    f"仍未提取到关键词，跳过该批次"
                                )
                        except Exception as fb_err:
                            logger.warning(
                                f"批次 {batch_idx}/{total_batches} fallback: "
                                f"重试LLM调用失败: {fb_err}"
                            )
                    else:
                        # 正常路径：LLM返回有效关键词列表
                        all_results.extend(kws)
                        logger.info(
                            f"批次 {batch_idx}/{total_batches}: 提取 {len(kws)} 个关键词"
                        )
                except Exception as e:
                    logger.error(f"批次 {batch_idx}/{total_batches}: LLM调用失败: {e}")

            # === 合并去重 ===
            seen: dict[str, float] = {}
            for kw in all_results:
                keyword = kw.get("keyword", "").strip()
                if keyword:
                    importance = kw.get("importance", 0.5)
                    if keyword in seen:
                        seen[keyword] = max(seen[keyword], importance)
                    else:
                        seen[keyword] = importance

            result = [{"keyword": k, "importance": v} for k, v in seen.items()]
            logger.info(
                f"分批提取完成: 合并前 {len(all_results)} 个 → 去重后 {len(result)} 个锚关键词"
            )
            return result

        except Exception as e:
            logger.error(f"分批锚关键词提取失败: {e}")
            return []

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
