"""
文本切块模块：递归切分，保留上下文
"""
import re
import logging
from typing import Generator

logger = logging.getLogger(__name__)


class TextChunker:
    """递归文本切块器"""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # 分隔符优先级（从大到小）
        self.separators = [
            "\n\n\n",   # 段落间空行
            "\n\n",     # 段落
            "\n",       # 行
            "。",       # 中文句号
            ".",        # 英文句号
            "！",       # 中文感叹号
            "？",       # 中文问号
            "；",       # 中文分号
            " ",        # 空格
            "",         # 字符级
        ]

    def chunk_text(
        self,
        text: str,
        doc_id: str = "",
        metadata: dict | None = None
    ) -> list[dict]:
        """
        切分文本

        返回: [{chunk_id, content, chunk_index, doc_id, metadata}]
        """
        if not text.strip():
            return []

        chunks = []
        raw_chunks = self._recursive_split(text)

        current_chunk = ""
        current_index = 0

        for i, part in enumerate(raw_chunks):
            part = part.strip()
            if not part:
                continue

            if len(current_chunk) + len(part) <= self.chunk_size:
                current_chunk += part if not current_chunk else " " + part
            else:
                if current_chunk:
                    chunk_id = f"{doc_id}_{current_index:04d}"
                    chunks.append({
                        "chunk_id": chunk_id,
                        "content": current_chunk.strip(),
                        "chunk_index": current_index,
                        "doc_id": doc_id,
                        "metadata": metadata or {},
                    })
                    current_index += 1

                # 处理超长片段：重叠切分
                if len(part) > self.chunk_size:
                    sub_chunks = self._split_long_text(part)
                    for sub in sub_chunks:
                        chunk_id = f"{doc_id}_{current_index:04d}"
                        chunks.append({
                            "chunk_id": chunk_id,
                            "content": sub.strip(),
                            "chunk_index": current_index,
                            "doc_id": doc_id,
                            "metadata": metadata or {},
                        })
                        current_index += 1
                    current_chunk = ""
                else:
                    current_chunk = part

        # 最后一个chunk
        if current_chunk.strip():
            chunk_id = f"{doc_id}_{current_index:04d}"
            chunks.append({
                "chunk_id": chunk_id,
                "content": current_chunk.strip(),
                "chunk_index": current_index,
                "doc_id": doc_id,
                "metadata": metadata or {},
            })

        logger.info(f"文档 {doc_id}: 切分为 {len(chunks)} 个chunk")
        return chunks

    def _recursive_split(self, text: str) -> list[str]:
        """递归切分"""
        for sep in self.separators:
            if sep == "":
                # 字符级切分
                parts = [text[i:i+self.chunk_size] for i in range(0, len(text), self.chunk_size)]
                return parts

            parts = text.split(sep)
            # 检查是否所有部分都够小
            if all(len(p.strip()) <= self.chunk_size for p in parts):
                return [p.strip() for p in parts if p.strip()]

        return [text]

    def _split_long_text(self, text: str) -> list[str]:
        """切分超长文本（带重叠）"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - self.chunk_overlap
        return chunks
