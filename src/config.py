"""
配置管理模块
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(Path(__file__).parent.parent / ".env")

# Neo4j配置
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "knowledge2026")

# ChromaDB配置
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8300"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "knowledge_docs")

# Embedding配置
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")
EMBEDDING_MODEL_PATH = os.getenv("EMBEDDING_MODEL_PATH", "")

# 启用离线模式，优先使用本地缓存
os.environ['TRANSFORMERS_OFFLINE'] = '1'


def resolve_local_model_path() -> str:
    """
    解析本地 embedding 模型路径，优先级：
    1) .env 中的 EMBEDDING_MODEL_PATH 环境变量
    2) 自动检测 ~/.cache/huggingface/hub/ 下的模型快照
    3) 兜底使用原始 model name（向后兼容）
    """
    import logging
    _logger = logging.getLogger(__name__)

    # 优先级1：用户显式指定路径
    if EMBEDDING_MODEL_PATH:
        path = Path(EMBEDDING_MODEL_PATH).expanduser()
        if path.is_dir():
            _logger.info(f"使用显式指定的本地模型路径: {path}")
            return str(path)
        _logger.warning(f"EMBEDDING_MODEL_PATH 指定的路径不存在: {path}，尝试自动检测")

    # 优先级2：自动检测 huggingface hub 缓存
    model_name = EMBEDDING_MODEL.replace("/", "--")
    hub_cache = Path.home() / ".cache" / "huggingface" / "hub" / f"models--{model_name}"
    refs_main = hub_cache / "refs" / "main"
    if hub_cache.is_dir():
        try:
            if refs_main.is_file():
                snapshot_hash = refs_main.read_text().strip()
                snapshot_path = hub_cache / "snapshots" / snapshot_hash
                if snapshot_path.is_dir():
                    _logger.info(f"自动检测到本地模型快照: {snapshot_path}")
                    return str(snapshot_path)
        except Exception as e:
            _logger.warning(f"读取模型快照引用失败: {e}")

    # 优先级3：兜底使用原始 model name
    _logger.info(f"未找到本地模型缓存，使用原始模型名称: {EMBEDDING_MODEL}")
    return EMBEDDING_MODEL

# LLM配置
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/coding/paas/v4")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "glm-5")

# 文档处理
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))

# API配置
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8100"))

# 知识回存配置
WRITEBACK_ENABLED = os.getenv('WRITEBACK_ENABLED', 'true').lower() == 'true'
WRITEBACK_THRESHOLD = float(os.getenv('WRITEBACK_THRESHOLD', '0.7'))
WRITEBACK_DEDUP_THRESHOLD = float(os.getenv('WRITEBACK_DEDUP_THRESHOLD', '0.95'))

# 路径
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
LOGS_DIR = PROJECT_ROOT / "logs"
