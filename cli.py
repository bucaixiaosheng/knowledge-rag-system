#!/usr/bin/env python3
"""
知识RAG系统 CLI 命令行工具

用法:
    python cli.py ingest --file /path/to/doc.md        # 本地文件入库
    python cli.py ingest --url https://example.com      # URL入库
    python cli.py ingest --wechat-url https://mp.weixin.qq.com/s/xxx  # 微信文章入库
    python cli.py ingest --dir /path/to/docs/           # 批量目录入库
    python cli.py search "微软TTS"                      # 语义搜索
    python cli.py delete --doc-id wx_abc123             # 删除文档（级联清理）
    python cli.py stats                                 # 系统统计
    python cli.py list-docs                             # 列出所有文档
"""
import argparse
import json
import os
import sys

# 确保能import src模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def cmd_ingest(args):
    """入库操作"""
    from src.pipeline import IngestPipeline

    pipeline = IngestPipeline()
    tags = [t.strip() for t in args.tags.split(",")] if args.tags else None

    if args.file:
        if not os.path.isfile(args.file):
            print(f"❌ 文件不存在: {args.file}")
            sys.exit(1)
        print(f"📥 入库文件: {args.file}")
        result = pipeline.ingest_file(args.file, tags=tags)
        _print_ingest_result(result)

    elif args.url:
        print(f"📥 入库URL: {args.url}")
        result = pipeline.ingest_url(args.url, tags=tags)
        _print_ingest_result(result)

    elif args.wechat_url:
        print(f"📥 入库微信文章: {args.wechat_url}")
        result = pipeline.ingest_wechat_url(args.wechat_url, tags=tags)
        _print_ingest_result(result)

    elif args.dir:
        if not os.path.isdir(args.dir):
            print(f"❌ 目录不存在: {args.dir}")
            sys.exit(1)
        print(f"📥 批量入库目录: {args.dir}")
        results = pipeline.ingest_directory(args.dir, recursive=True)
        success = sum(1 for r in results if r.get("status") == "success")
        skipped = sum(1 for r in results if r.get("status") == "skipped")
        errors = sum(1 for r in results if r.get("status") == "error")
        print(f"\n📊 批量入库完成: ✅ {success} 成功 | ⏭️ {skipped} 跳过 | ❌ {errors} 失败")
        for r in results:
            status_icon = "✅" if r["status"] == "success" else "⏭️" if r["status"] == "skipped" else "❌"
            print(f"  {status_icon} {r.get('doc_id', '?')}: {r.get('title', r.get('error', 'unknown'))}")

    else:
        print("❌ 请指定 --file, --url, --wechat-url 或 --dir")
        sys.exit(1)


def cmd_search(args):
    """语义搜索"""
    from src.pipeline import IngestPipeline

    pipeline = IngestPipeline()
    print(f"🔍 搜索: {args.query} (top_k={args.top_k})")
    try:
        results = pipeline.semantic_search(args.query, top_k=args.top_k)
    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        sys.exit(1)

    if not results:
        print("📭 未找到相关结果")
        return

    print(f"\n找到 {len(results)} 条相关结果:\n")
    for i, r in enumerate(results, 1):
        if r.get("type") == "related_knowledge":
            # 相似知识扩展
            print(f"  🔗 [{i}] 相关知识: {r.get('related_keyword', 'N/A')} (相似度: {r.get('similarity', 'N/A')})")
            for rd in r.get("related_docs", []):
                print(f"       └─ {rd.get('title', 'N/A')} ({rd.get('doc_id', '')})")
            continue

        title = r.get("title", "N/A")
        source = r.get("source", "")
        doc_id = r.get("doc_id", "")
        score = r.get("relevance_score") or r.get("keyword_score", "N/A")
        kw = r.get("matched_keyword", "")
        summary = r.get("summary", "") or r.get("content", "")
        if summary and len(summary) > 200:
            summary = summary[:200] + "..."

        print(f"  📄 [{i}] {title}")
        print(f"       来源: {source or doc_id}")
        if kw:
            print(f"       匹配关键词: {kw}")
        print(f"       相关度: {score}")
        if summary:
            print(f"       摘要: {summary}")
        print()


def cmd_delete(args):
    """删除文档"""
    from src.pipeline import IngestPipeline

    pipeline = IngestPipeline()
    print(f"🗑️  删除文档: {args.doc_id}")
    try:
        result = pipeline.delete_document(args.doc_id)
        print(f"✅ 删除完成: {json.dumps(result, ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"❌ 删除失败: {e}")
        sys.exit(1)


def cmd_stats(args):
    """系统统计"""
    from src.knowledge_graph import KnowledgeGraph
    from src.vector_store import VectorStore

    print("📊 系统统计信息\n")

    # 知识图谱统计
    try:
        kg = KnowledgeGraph()
        kg_stats = kg.get_stats()
        kg.close()
        print("🗄️  知识图谱 (Neo4j):")
        print(f"  文档数:       {kg_stats.get('document_count', 0)}")
        print(f"  Chunk数:      {kg_stats.get('chunk_count', 0)}")
        print(f"  实体数:       {kg_stats.get('entity_count', 0)}")
        print(f"  概念数:       {kg_stats.get('concept_count', 0)}")
        print(f"  标签数:       {kg_stats.get('tag_count', 0)}")
        print(f"  锚关键词数:   {kg_stats.get('anchor_keyword_count', 0)}")
        print(f"  领域数:       {kg_stats.get('domain_count', 0)}")
        print(f"  子领域数:     {kg_stats.get('subdomain_count', 0)}")
        print(f"  关系数:       {kg_stats.get('relation_count', 0)}")
    except Exception as e:
        print(f"  ❌ Neo4j连接失败: {e}")

    print()

    # 向量库统计
    try:
        vs = VectorStore()
        print("📦 向量库 (ChromaDB):")
        print(f"  文档数:  {vs.get_doc_count()}")
        print(f"  Chunk数: {vs.get_chunk_count()}")
    except Exception as e:
        print(f"  ❌ ChromaDB连接失败: {e}")


def cmd_list_docs(args):
    """列出所有文档"""
    from src.knowledge_graph import KnowledgeGraph

    try:
        kg = KnowledgeGraph()
        query = """
        MATCH (d:Document)
        OPTIONAL MATCH (sd:SubDomain)-[:CONTAINS_DOC]->(d)
        RETURN d.doc_id AS doc_id, d.title AS title, d.source AS source,
               d.doc_type AS doc_type, d.chunk_count AS chunk_count,
               d.created_at AS created_at, d.domain_tags AS domain_tags,
               sd.name AS primary_domain
        ORDER BY d.created_at DESC
        """
        with kg.driver.session() as session:
            results = [dict(r) for r in session.run(query)]
        kg.close()

        if not results:
            print("📭 暂无文档")
            return

        print(f"📚 文档列表 (共 {len(results)} 篇):\n")
        print(f"{'序号':<4} {'Doc ID':<20} {'标题':<30} {'领域':<12} {'Chunk数':<8} {'类型'}")
        print("-" * 100)
        for i, r in enumerate(results, 1):
            title = str(r.get("title") or "N/A")[:28]
            doc_id = str(r.get("doc_id") or "")[:18]
            dt = r.get("domain_tags") or r.get("primary_domain") or ""
            if isinstance(dt, list):
                domain = ", ".join(dt)[:10]
            else:
                domain = str(dt)[:10]
            chunks = r.get("chunk_count") or 0
            doc_type = str(r.get("doc_type") or "")
            print(f"{i:<4} {doc_id:<20} {title:<30} {domain:<12} {chunks:<8} {doc_type}")

    except Exception as e:
        print(f"❌ 获取文档列表失败: {e}")
        sys.exit(1)


def _print_ingest_result(result: dict):
    """格式化输出入库结果"""
    status = result.get("status", "unknown")
    if status == "success":
        print(f"✅ 入库成功!")
        print(f"  Doc ID:     {result.get('doc_id', '')}")
        print(f"  标题:       {result.get('title', '')}")
        print(f"  Chunk数:    {result.get('chunk_count', 0)}")
        print(f"  锚关键词:   {result.get('anchor_count', 0)}")
        print(f"  实体数:     {result.get('entity_count', 0)}")
        print(f"  领域分类:   {', '.join(result.get('domains', []))}")
    elif status == "skipped":
        print(f"⏭️  文档已存在: {result.get('doc_id', '')}")
    else:
        print(f"❌ 入库失败: {result.get('error', result.get('reason', 'unknown'))}")


def main():
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="知识RAG系统命令行工具",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.set_defaults(func=None)

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # ---- ingest ----
    ingest_parser = subparsers.add_parser("ingest", help="文档入库")
    ingest_group = ingest_parser.add_mutually_exclusive_group(required=True)
    ingest_group.add_argument("--file", "-f", help="本地文件路径 (.md/.pdf/.txt/.html)")
    ingest_group.add_argument("--url", "-u", help="网页URL")
    ingest_group.add_argument("--wechat-url", "-w", help="微信公众号文章URL")
    ingest_group.add_argument("--dir", "-d", help="批量入库目录")
    ingest_parser.add_argument("--tags", "-t", help='自定义标签，逗号分隔 (如 "AI,工具")')
    ingest_parser.set_defaults(func=cmd_ingest)

    # ---- search ----
    search_parser = subparsers.add_parser("search", help="语义搜索")
    search_parser.add_argument("query", help="搜索查询文本")
    search_parser.add_argument("--top-k", "-k", type=int, default=5, help="返回结果数 (默认5)")
    search_parser.set_defaults(func=cmd_search)

    # ---- delete ----
    delete_parser = subparsers.add_parser("delete", help="删除文档")
    delete_parser.add_argument("--doc-id", required=True, help="文档ID")
    delete_parser.set_defaults(func=cmd_delete)

    # ---- stats ----
    stats_parser = subparsers.add_parser("stats", help="系统统计")
    stats_parser.set_defaults(func=cmd_stats)

    # ---- list-docs ----
    list_parser = subparsers.add_parser("list-docs", help="列出所有文档")
    list_parser.set_defaults(func=cmd_list_docs)

    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG, format="%(name)s - %(levelname)s - %(message)s")
    else:
        import logging
        logging.basicConfig(level=logging.WARNING)

    if args.func:
        try:
            args.func(args)
        except KeyboardInterrupt:
            print("\n⛔ 操作已中断")
            sys.exit(130)
        except Exception as e:
            print(f"\n❌ 未预期错误: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
