"""
定时任务模块：自动爬取和增量更新
- 每天凌晨2点扫描docs目录入库
- 每小时爬取urls.txt中的URL
- 已处理URL记录在urls_processed.txt
"""
import logging
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from src.pipeline import IngestPipeline

logger = logging.getLogger(__name__)


class TaskScheduler:
    """定时任务调度器"""

    def __init__(self, pipeline: IngestPipeline | None = None):
        self.pipeline = pipeline or IngestPipeline()
        self.scheduler = BackgroundScheduler()
        self._project_root = Path(__file__).parent.parent
        self._setup_jobs()

    def _setup_jobs(self):
        """注册定时任务"""
        # 每天凌晨2点扫描docs目录入库
        self.scheduler.add_job(
            self._scan_docs_directory,
            trigger="cron",
            hour=2,
            minute=0,
            id="scan_docs",
            name="扫描docs目录入库",
            replace_existing=True,
        )
        logger.info("已注册定时任务: scan_docs (每天凌晨2:00)")

        # 每小时爬取urls.txt中的URL
        self.scheduler.add_job(
            self._crawl_urls,
            trigger="interval",
            hours=1,
            id="crawl_urls",
            name="爬取URL列表",
            replace_existing=True,
        )
        logger.info("已注册定时任务: crawl_urls (每小时)")

    def _scan_docs_directory(self):
        """扫描docs目录，增量入库"""
        logger.info("开始扫描docs目录...")
        docs_root = self._project_root / "docs"

        total_new = 0
        total_skip = 0

        for subdir in ["pdf", "html", "markdown"]:
            dir_path = docs_root / subdir
            if dir_path.exists():
                try:
                    results = self.pipeline.ingest_directory(str(dir_path))
                    new_count = sum(1 for r in results if r.get("status") == "success")
                    skip_count = sum(1 for r in results if r.get("status") == "skipped")
                    total_new += new_count
                    total_skip += skip_count
                    logger.info(f"  {subdir}/: 新增 {new_count}, 跳过 {skip_count}")
                except Exception as e:
                    logger.error(f"  扫描 {subdir}/ 失败: {e}")

        logger.info(f"docs目录扫描完成: 新增 {total_new}, 跳过 {total_skip}")

    def _crawl_urls(self):
        """爬取urls.txt中尚未处理的URL"""
        urls_file = self._project_root / "docs" / "urls.txt"
        if not urls_file.exists():
            logger.debug("urls.txt 不存在，跳过URL爬取")
            return

        # 读取待处理URL列表
        with open(urls_file, "r", encoding="utf-8") as f:
            all_urls = [
                line.strip()
                for line in f
                if line.strip() and not line.startswith("#")
            ]

        if not all_urls:
            logger.debug("urls.txt 为空，跳过")
            return

        # 读取已处理URL集合
        processed_file = self._project_root / "docs" / "urls_processed.txt"
        processed: set[str] = set()
        if processed_file.exists():
            processed = set(
                line.strip()
                for line in processed_file.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )

        new_urls = [u for u in all_urls if u not in processed]
        if not new_urls:
            logger.debug("没有新URL需要处理")
            return

        logger.info(f"发现 {len(new_urls)} 个新URL待处理")

        for url in new_urls:
            try:
                result = self.pipeline.ingest_url(url)
                if result.get("status") in ("success", "skipped"):
                    processed.add(url)
                    logger.info(f"URL入库成功: {url}")
                else:
                    logger.warning(f"URL入库异常: {url} -> {result}")
            except Exception as e:
                logger.error(f"URL入库失败: {url}: {e}")

        # 更新已处理列表
        processed_file.write_text("\n".join(sorted(processed)) + "\n", encoding="utf-8")
        logger.info(f"urls_processed.txt 已更新 ({len(processed)} 条记录)")

    # ---- 生命周期 ----

    def start(self):
        """启动调度器"""
        self.scheduler.start()
        logger.info("✅ 定时任务调度器已启动")

    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown(wait=False)
        logger.info("定时任务调度器已停止")

    def get_jobs(self) -> list[dict]:
        """获取所有已注册的任务信息"""
        jobs = []
        for job in self.scheduler.get_jobs():
            try:
                nrt = str(job.next_run_time) if job.next_run_time else None
            except AttributeError:
                nrt = None
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": nrt,
                "trigger": str(job.trigger),
            })
        return jobs


# ---- CLI入口：直接运行可启动调度器 ----
if __name__ == "__main__":
    import argparse
    import time
    import signal
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="知识库定时任务调度器")
    parser.add_argument(
        "--once", action="store_true",
        help="只执行一次扫描，不启动常驻调度",
    )
    parser.add_argument(
        "--scan", action="store_true",
        help="立即执行docs目录扫描",
    )
    parser.add_argument(
        "--crawl", action="store_true",
        help="立即执行URL爬取",
    )
    args = parser.parse_args()

    scheduler = TaskScheduler()

    if args.scan:
        scheduler._scan_docs_directory()
        sys.exit(0)

    if args.crawl:
        scheduler._crawl_urls()
        sys.exit(0)

    if args.once:
        scheduler._scan_docs_directory()
        scheduler._crawl_urls()
        sys.exit(0)

    # 常驻模式
    scheduler.start()

    def _shutdown(signum, frame):
        logger.info("收到退出信号，正在停止...")
        scheduler.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info("调度器运行中，按 Ctrl+C 退出")
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()
