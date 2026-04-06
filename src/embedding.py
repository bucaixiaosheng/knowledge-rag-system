"""
Embedding模块：使用本地模型生成向量
"""
import logging
from sentence_transformers import SentenceTransformer
from src.config import EMBEDDING_DEVICE, resolve_local_model_path

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """本地Embedding引擎"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        model_path = resolve_local_model_path()
        logger.info(f"加载Embedding模型, 路径: {model_path}")
        self.model = SentenceTransformer(model_path, device=EMBEDDING_DEVICE)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self._initialized = True
        logger.info(f"Embedding模型加载完成, 维度: {self.dimension}")

    def embed_texts(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """批量文本向量化"""
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        """单条查询向量化"""
        embedding = self.model.encode(
            text,
            normalize_embeddings=True,
        )
        return embedding.tolist()


# 全局单例
embedding_engine = EmbeddingEngine()
