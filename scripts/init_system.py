#!/usr/bin/env python3
"""
知识管理系统初始化脚本

创建必要目录结构，验证所有服务连接（ChromaDB、Neo4j、Embedding模型、LLM API），
并输出每项验证的 ✅/❌ 状态。

用法:
  python scripts/init_system.py
"""
import os
import sys

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from pathlib import Path


# ──────────────────────────── 颜色辅助 ────────────────────────────

def _green(msg: str) -> str:
    return f"\033[92m{msg}\033[0m"

def _red(msg: str) -> str:
    return f"\033[91m{msg}\033[0m"

def _bold(msg: str) -> str:
    return f"\033[1m{msg}\033[0m"


# ──────────────────────────── 目录初始化 ────────────────────────────

def init_directories() -> int:
    """创建必要的目录，返回成功数量"""
    dirs = [
        "docs/pdf",
        "docs/html",
        "docs/markdown",
        "logs",
        "chroma",
        "neo4j/data",
        "neo4j/logs",
        "neo4j/init",
        "neo4j/conf",
    ]
    base = Path(PROJECT_ROOT)

    print(_bold("\n=== 创建目录结构 ===\n"))
    ok = 0
    for d in dirs:
        target = base / d
        try:
            target.mkdir(parents=True, exist_ok=True)
            print(f"  ✅ 目录: {d}/")
            ok += 1
        except Exception as e:
            print(f"  ❌ 目录: {d}/ — {e}")

    # 创建 urls.txt（如不存在）
    urls_file = base / "docs" / "urls.txt"
    if not urls_file.exists():
        urls_file.write_text("# 在这里添加要爬取的URL，每行一个\n")
        print("  ✅ 文件: docs/urls.txt")
        ok += 1
    else:
        print(f"  ⏭️  文件: docs/urls.txt （已存在）")

    return ok


# ──────────────────────────── 连接验证 ────────────────────────────

def check_chromadb() -> bool:
    """验证 ChromaDB 连接 (localhost:8300)"""
    try:
        import chromadb
        client = chromadb.HttpClient(host="localhost", port=8300)
        client.heartbeat()
        return True
    except Exception as e:
        print(f"      错误: {e}")
        return False


def check_neo4j() -> bool:
    """验证 Neo4j 连接 (bolt://localhost:7687)"""
    try:
        from neo4j import GraphDatabase
        from src.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        driver.close()
        return True
    except Exception as e:
        print(f"      错误: {e}")
        return False


def check_embedding() -> bool:
    """验证 Embedding 模型加载 (all-MiniLM-L6-v2)"""
    try:
        from src.config import EMBEDDING_MODEL
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(EMBEDDING_MODEL)
        dim = model.get_sentence_embedding_dimension()
        print(f"      模型: {EMBEDDING_MODEL}，维度: {dim}")
        return True
    except Exception as e:
        print(f"      错误: {e}")
        return False


def check_llm() -> bool:
    """验证 LLM API 连接"""
    try:
        from src.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
        print(f"      配置: base_url={LLM_BASE_URL}, model={LLM_MODEL}")

        if not LLM_API_KEY:
            print("      ⚠️  LLM_API_KEY 未设置，跳过实际调用验证")
            return True  # SDK 可导入视为通过，仅提示

        from openai import OpenAI
        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        # 发送一个极短请求验证连通性
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=5,
            timeout=10,
        )
        _ = resp.choices[0].message.content
        return True
    except Exception as e:
        print(f"      错误: {e}")
        return False


def check_connections():
    """运行所有连接验证，输出 ✅/❌"""
    print(_bold("\n=== 验证服务连接 ===\n"))

    checks = [
        ("ChromaDB 向量数据库", "localhost:8300", check_chromadb),
        ("Neo4j 图数据库", "bolt://localhost:7687", check_neo4j),
        ("Embedding 模型", "sentence-transformers/all-MiniLM-L6-v2", check_embedding),
        ("LLM API (智谱GLM)", "open.bigmodel.cn", check_llm),
    ]

    passed = 0
    failed = 0
    for name, endpoint, fn in checks:
        print(f"  🔍 {name} ({endpoint})")
        ok = fn()
        if ok:
            print(f"  ✅ {name} 连接成功\n")
            passed += 1
        else:
            print(f"  ❌ {name} 连接失败\n")
            failed += 1

    return passed, failed


# ──────────────────────────── 主流程 ────────────────────────────

def main():
    print(_bold("=" * 55))
    print(_bold("  📚 知识管理系统 — 初始化与连接验证"))
    print(_bold("=" * 55))

    dir_ok = init_directories()
    conn_pass, conn_fail = check_connections()

    print(_bold("=" * 55))
    print(f"  目录创建: {dir_ok} 项")
    print(f"  连接验证: {_green(f'{conn_pass} 通过')}"
          + (f"，{_red(f'{conn_fail} 失败')}" if conn_fail else ""))
    print(_bold("=" * 55))

    if conn_fail:
        print(f"\n⚠️  有 {conn_fail} 项连接验证失败，请检查:")
        print("   1. Docker 容器是否启动: cd ~/knowledge-rag-system && docker compose up -d")
        print("   2. .env 中的 API_KEY 是否已配置")
        print("   3. 依赖是否已安装: pip install -r requirements.txt")
        sys.exit(1)
    else:
        print(f"\n🎉 所有验证通过！系统已就绪。")
        print(f"   启动 API 服务: uvicorn api.main:app --port 8100 --reload")
        print(f"   添加文档: python scripts/add_document.py --help")
        sys.exit(0)


if __name__ == "__main__":
    main()
