"""
向量存储模块：ChromaDB操作封装
"""
import logging
from chromadb import HttpClient as ChromaClient
from chromadb.config import Settings
from src.config import CHROMA_HOST, CHROMA_PORT, CHROMA_COLLECTION
from src.embedding import embedding_engine

logger = logging.getLogger(__name__)


class VectorStore:
    """ChromaDB向量存储"""

    def __init__(self):
        self.client = ChromaClient(
            host=CHROMA_HOST,
            port=CHROMA_PORT,
            settings=Settings(anonymized_telemetry=False)
        )
        # 获取或创建collection
        self.collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"ChromaDB连接成功, collection: {CHROMA_COLLECTION}")

    def add_chunks(self, chunks: list[dict]) -> int:
        """
        添加文档chunk到向量库
        chunks: [{chunk_id, content, doc_id, metadata, embedding?}]
        返回添加数量
        """
        if not chunks:
            return 0

        # 生成embedding
        texts = [c["content"] for c in chunks]
        embeddings = embedding_engine.embed_texts(texts)

        ids = [c["chunk_id"] for c in chunks]
        documents = texts
        metadatas = [
            {
                "doc_id": c["doc_id"],
                "chunk_index": c["chunk_index"],
                **(c.get("metadata") or {}),
            }
            for c in chunks
        ]

        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        logger.info(f"向量库添加 {len(chunks)} 个chunk")
        return len(chunks)

    def search(
        self,
        query: str,
        top_k: int = 10,
        filter_doc_id: str | None = None,
        filter_metadata: dict | None = None,
    ) -> list[dict]:
        """
        向量相似度搜索
        返回: [{chunk_id, content, doc_id, score, metadata}]
        """
        query_embedding = embedding_engine.embed_query(query)

        where_filter = {}
        if filter_doc_id:
            where_filter["doc_id"] = filter_doc_id
        if filter_metadata:
            where_filter.update(filter_metadata)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter or None,
            include=["documents", "metadatas", "distances"],
        )

        items = []
        for i in range(len(results["ids"][0])):
            items.append({
                "chunk_id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "doc_id": results["metadatas"][0][i].get("doc_id", ""),
                "score": 1 - results["distances"][0][i],  # 转为相似度
                "metadata": results["metadatas"][0][i],
            })

        return items

    def delete_by_doc(self, doc_id: str) -> int:
        """删除某文档的所有chunk"""
        self.collection.delete(
            where={"doc_id": doc_id}
        )
        logger.info(f"向量库删除文档 {doc_id} 的所有chunk")

    def get_doc_count(self) -> int:
        """获取总文档数（去重）"""
        all_meta = self.collection.get(include=["metadatas"])
        doc_ids = set(m["doc_id"] for m in all_meta["metadatas"])
        return len(doc_ids)

    def get_chunk_count(self) -> int:
        """获取总chunk数"""
        return self.collection.count()
