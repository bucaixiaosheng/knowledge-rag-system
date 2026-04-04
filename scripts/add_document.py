#!/usr/bin/env python3
"""
CLI工具：添加文档到知识库

用法:
  python scripts/add_document.py file.pdf
  python scripts/add_document.py --url https://example.com
  python scripts/add_document.py --dir ./docs/pdf
  python scripts/add_document.py --dir ./docs --tags "技术,文档"
  python scripts/add_document.py --delete doc_abc123
  python scripts/add_document.py --stats
"""
import argparse
import sys
import os
import logging

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("add_document")


def main():
    parser = argparse.ArgumentParser(
        prog="add_document",
        description="知识库文档管理CLI —— 支持文件、URL、目录入库及文档管理",
        epilog=(
            "示例:\n"
            "  %(prog)s report.pdf                  # 单文件入库\n"
            "  %(prog)s --url https://example.com   # URL入库\n"
            "  %(prog)s --dir ./docs/pdf --tags 技术 # 批量目录入库\n"
            "  %(prog)s --delete doc_abc123          # 删除文档\n"
            "  %(prog)s --stats                      # 查看统计\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "path",
        nargs="?",
        help="文件路径（支持 PDF/HTML/Markdown/纯文本）",
    )
    parser.add_argument(
        "--url",
        metavar="URL",
        help="从URL入库（抓取网页内容）",
    )
    parser.add_argument(
        "--dir",
        metavar="DIR",
        help="批量目录入库（递归扫描所有支持格式的文件）",
    )
    parser.add_argument(
        "--tags",
        metavar="TAGS",
        help="标签，逗号分隔（例如: 技术,文档,RAG）",
    )
    parser.add_argument(
        "--delete",
        metavar="DOC_ID",
        help="删除指定文档（通过 doc_id）",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="查看知识库统计信息",
    )

    args = parser.parse_args()

    # ---- 统计信息 ----
    if args.stats:
        _show_stats()
        return

    # ---- 删除文档 ----
    if args.delete:
        _delete_document(args.delete)
        return

    # ---- 解析标签 ----
    tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else None

    # ---- 延迟导入 pipeline ----
    from src.pipeline import IngestPipeline
    pipeline = IngestPipeline()

    # ---- URL 入库 ----
    if args.url:
        logger.info(f"从 URL 入库: {args.url}")
        result = pipeline.ingest_url(args.url, tags=tags)
        _print_result(result)
        return

    # ---- 目录批量入库 ----
    if args.dir:
        logger.info(f"批量目录入库: {args.dir}")
        results = pipeline.ingest_directory(args.dir)
        _print_batch_results(results)
        return

    # ---- 单文件入库 ----
    if args.path:
        file_path = os.path.abspath(args.path)
        if not os.path.isfile(file_path):
            print(f"❌ 文件不存在: {file_path}")
            sys.exit(1)
        logger.info(f"文件入库: {file_path}")
        result = pipeline.ingest_file(file_path, tags=tags)
        _print_result(result)
        return

    # 未提供任何操作参数
    parser.print_help()
    print("\n⚠️  请提供文件路径、--url、--dir、--delete 或 --stats 参数")


def _show_stats():
    """显示向量库和知识图谱统计信息"""
    print("=" * 50)
    print("  知识库统计信息")
    print("=" * 50)

    # 向量库
    try:
        from src.vector_store import VectorStore
        vs = VectorStore()
        doc_count = vs.get_doc_count()
        chunk_count = vs.get_chunk_count()
        print(f"\n📦 向量库 (ChromaDB)")
        print(f"   文档数: {doc_count}")
        print(f"   Chunk数: {chunk_count}")
    except Exception as e:
        print(f"\n📦 向量库 (ChromaDB)")
        print(f"   ❌ 连接失败: {e}")

    # 知识图谱
    try:
        from src.knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph()
        stats = kg.get_stats()
        print(f"\n🕸️  知识图谱 (Neo4j)")
        for k, v in stats.items():
            label = {
                "document_count": "文档节点",
                "entity_count": "实体节点",
                "concept_count": "概念节点",
                "tag_count": "标签节点",
                "relation_count": "关系边数",
            }.get(k, k)
            print(f"   {label}: {v}")
        kg.close()
    except Exception as e:
        print(f"\n🕸️  知识图谱 (Neo4j)")
        print(f"   ❌ 连接失败: {e}")

    print()


def _delete_document(doc_id: str):
    """删除指定文档"""
    from src.pipeline import IngestPipeline
    pipeline = IngestPipeline()
    pipeline.delete_document(doc_id)
    print(f"✅ 已删除文档: {doc_id}")


def _print_result(result: dict):
    """打印单条入库结果"""
    status = result.get("status", "unknown")
    if status == "success":
        print(f"✅ 入库成功!")
        print(f"   文档ID: {result.get('doc_id', 'N/A')}")
        print(f"   标题:   {result.get('title', 'N/A')}")
        print(f"   Chunk数: {result.get('chunk_count', 0)}")
        print(f"   锚关键词: {result.get('anchor_count', 0)}")
        print(f"   实体数: {result.get('entity_count', 0)}")
        print(f"   分类:   {result.get('domains', [])}")
    elif status == "skipped":
        print(f"⏭️  文档已存在，跳过: {result.get('doc_id', 'N/A')}")
        print(f"   原因:   {result.get('reason', 'already_exists')}")
    else:
        print(f"❌ 入库失败: {result.get('doc_id', 'N/A')}")
        print(f"   错误:   {result.get('error', 'unknown')}")


def _print_batch_results(results: list):
    """打印批量入库结果"""
    success = sum(1 for r in results if r.get("status") == "success")
    skipped = sum(1 for r in results if r.get("status") == "skipped")
    failed = sum(1 for r in results if r.get("status") not in ("success", "skipped"))

    print(f"\n{'=' * 50}")
    print(f"  批量入库完成")
    print(f"{'=' * 50}")
    print(f"  ✅ 成功: {success}")
    print(f"  ⏭️  跳过: {skipped}")
    print(f"  ❌ 失败: {failed}")
    print(f"  📄 总计: {len(results)}")

    if success > 0:
        print(f"\n成功入库的文档:")
        for r in results:
            if r.get("status") == "success":
                print(f"  ✅ {r.get('title', r.get('doc_id', '?'))} "
                      f"({r.get('chunk_count', 0)} chunks, "
                      f"{r.get('anchor_count', 0)} anchors)")

    if failed > 0:
        print(f"\n失败的文档:")
        for r in results:
            if r.get("status") not in ("success", "skipped"):
                print(f"  ❌ {r.get('doc_id', '?')}: {r.get('error', 'unknown')}")

    print()


if __name__ == "__main__":
    main()
