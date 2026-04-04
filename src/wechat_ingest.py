"""
微信公众号一键入库脚本
用法：python src/wechat_ingest.py <url>
      python src/wechat_ingest.py <url> --tags "标签1,标签2"
流程：scrapling爬取 → 生成MD → 自动分类 → 提取锚关键词 → 相似度建边 → 入库
"""
import argparse
import logging
import sys
import os

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline import IngestPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def ingest_wechat(url: str, tags: list[str] | None = None) -> dict:
    """微信公众号文章一键入库"""
    pipeline = IngestPipeline()
    logger.info(f"开始处理微信文章: {url}")

    result = pipeline.ingest_wechat_url(url, tags=tags)

    if result.get("status") == "success":
        logger.info("✅ 入库成功！")
        logger.info(f"   文档ID: {result.get('doc_id')}")
        logger.info(f"   标题:   {result.get('title')}")
        logger.info(f"   切块:   {result.get('chunk_count', 0)} 个")
        logger.info(f"   锚关键词: {result.get('anchor_count', 0)} 个")
        logger.info(f"   分类:   {result.get('domains', [])}")
    elif result.get("status") == "skipped":
        logger.info(f"⏭️ 文档已存在，跳过: {result.get('doc_id')}")
    else:
        logger.warning(f"入库结果: {result}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="微信公众号文章一键入库工具",
        epilog="示例: python src/wechat_ingest.py https://mp.weixin.qq.com/s/xxxxx",
    )
    parser.add_argument(
        "url",
        help="微信公众号文章URL (mp.weixin.qq.com)",
    )
    parser.add_argument(
        "--tags", "-t",
        default=None,
        help="自定义标签，逗号分隔 (例如: 'AI,深度学习')",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细日志",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 解析标签
    tags = None
    if args.tags:
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    # 验证URL格式
    url = args.url.strip()
    if not url.startswith(("http://", "https://")):
        parser.error(f"无效的URL: {url}")

    # 执行入库
    result = ingest_wechat(url, tags=tags)

    # 退出码
    sys.exit(0 if result.get("status") in ("success", "skipped") else 1)


if __name__ == "__main__":
    main()
