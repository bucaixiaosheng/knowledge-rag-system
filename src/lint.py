"""
知识库健康检查模块（Lint）
检查项：孤立AnchorKeyword、无领域归属文档、锚关键词重叠异常、跨领域关联缺失
"""
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class LintResult:
    """单项检查结果"""

    check_name: str
    severity: str  # "high" / "medium" / "low"
    issues: list[dict] = field(default_factory=list)  # [{"description", "node_id", "details"}]
    fix_applied: int = 0
    fix_failed: int = 0

    @property
    def passed(self) -> bool:
        return len(self.issues) == 0


@dataclass
class LintReport:
    """全部检查汇总报告"""

    total_checks: int = 0
    passed: int = 0
    warnings: int = 0  # severity == "low" or "medium" 且有问题
    errors: int = 0  # severity == "high" 且有问题
    results: list[LintResult] = field(default_factory=list)
    summary: str = ""

    def to_text(self) -> str:
        """生成人类可读的格式化报告文本"""
        lines = []
        lines.append("=" * 60)
        lines.append("📋 知识库健康检查报告 (Lint Report)")
        lines.append("=" * 60)
        lines.append("")

        for r in self.results:
            icon = "✅" if r.passed else ("🔴" if r.severity == "high" else "🟡" if r.severity == "medium" else "🟢")
            lines.append(f"{icon} [{r.severity.upper()}] {r.check_name}")
            if r.passed:
                lines.append("   → 通过，无问题")
            else:
                lines.append(f"   → 发现 {len(r.issues)} 个问题")
                for issue in r.issues:
                    lines.append(f"     • {issue.get('description', '')}")
                    node_id = issue.get("node_id", "")
                    if node_id:
                        lines.append(f"       节点: {node_id}")
                    details = issue.get("details", "")
                    if details:
                        lines.append(f"       详情: {details}")
            if r.fix_applied > 0:
                lines.append(f"   🔧 已修复: {r.fix_applied} 个")
            if r.fix_failed > 0:
                lines.append(f"   ⚠️ 修复失败: {r.fix_failed} 个")
            lines.append("")

        lines.append("-" * 60)
        lines.append(f"📊 总计: {self.total_checks} 项检查 | ✅ {self.passed} 通过 | 🟡 {self.warnings} 警告 | 🔴 {self.errors} 错误")
        if self.summary:
            lines.append(f"📝 摘要: {self.summary}")
        lines.append("=" * 60)

        return "\n".join(lines)


class KnowledgeLint:
    """知识库健康检查器"""

    def __init__(self, kg):
        """
        构造函数

        Args:
            kg: KnowledgeGraph 实例
        """
        self.kg = kg

    def run_all_checks(self, fix: bool = False) -> LintReport:
        """
        执行所有检查

        Args:
            fix: 是否自动修复可修复的问题

        Returns:
            LintReport 汇总报告
        """
        check_methods = [
            self.check_orphan_anchor_keywords,
            self.check_documents_without_domain,
            self.check_anchor_overlap_anomaly,
            self.check_missing_cross_domain_links,
        ]

        results = []
        for check_fn in check_methods:
            try:
                result = check_fn(fix=fix)
            except Exception as e:
                logger.error(f"检查 {check_fn.__name__} 执行失败: {e}")
                result = LintResult(
                    check_name=check_fn.__name__,
                    severity="high",
                    issues=[{
                        "description": f"检查执行异常",
                        "node_id": "",
                        "details": str(e),
                    }],
                )
            results.append(result)

        # 汇总统计
        passed = sum(1 for r in results if r.passed)
        errors = sum(1 for r in results if not r.passed and r.severity == "high")
        warnings = sum(1 for r in results if not r.passed and r.severity in ("medium", "low"))

        summary_parts = []
        if errors > 0:
            summary_parts.append(f"{errors} 个高优先级问题需要处理")
        if warnings > 0:
            summary_parts.append(f"{warnings} 个低优先级警告")
        if passed == len(results):
            summary_parts.append("所有检查通过，知识库健康状态良好")

        summary = "；".join(summary_parts) if summary_parts else "无异常"

        report = LintReport(
            total_checks=len(results),
            passed=passed,
            warnings=warnings,
            errors=errors,
            results=results,
            summary=summary,
        )
        return report

    def check_orphan_anchor_keywords(self, fix: bool = False) -> LintResult:
        """
        检查孤立AnchorKeyword：chunk_ids为空列表或size为0的节点
        fix=True 时删除孤立节点

        Returns:
            LintResult
        """
        result = LintResult(
            check_name="孤立AnchorKeyword检查",
            severity="high",
        )

        query = """
        MATCH (ak:AnchorKeyword)
        WHERE ak.chunk_ids = [] OR size(ak.chunk_ids) = 0
           OR ak.chunk_ids IS NULL
        RETURN ak.keyword AS keyword, ak.occurrence_count AS count
        """
        with self.kg.driver.session() as session:
            records = [dict(r) for r in session.run(query)]

        for r in records:
            result.issues.append({
                "description": f"孤立AnchorKeyword: '{r['keyword']}'",
                "node_id": r["keyword"],
                "details": f"无关联Chunk, occurrence_count={r.get('count', 0)}",
            })

        if fix and result.issues:
            keywords_to_delete = [r["keyword"] for r in records]
            try:
                with self.kg.driver.session() as session:
                    del_result = session.run(
                        """
                        UNWIND $keywords AS kw
                        MATCH (ak:AnchorKeyword {keyword: kw})
                        DETACH DELETE ak
                        RETURN count(*) AS deleted
                        """,
                        keywords=keywords_to_delete,
                    )
                    deleted = del_result.single()
                    result.fix_applied = deleted["deleted"] if deleted else 0
                logger.info(f"清理孤立AnchorKeyword: {result.fix_applied} 个")
            except Exception as e:
                result.fix_failed = len(keywords_to_delete)
                logger.error(f"清理孤立AnchorKeyword失败: {e}")

        return result

    def check_documents_without_domain(self, fix: bool = False) -> LintResult:
        """
        检查无领域归属的Document：无 CONTAINS_DOC 关系的文档
        fix=True 时仅报告，不自动分类（分类操作太重）

        Returns:
            LintResult
        """
        result = LintResult(
            check_name="无领域归属文档检查",
            severity="medium",
        )

        query = """
        MATCH (d:Document)
        WHERE NOT (:SubDomain)-[:CONTAINS_DOC]->(d)
        RETURN d.doc_id AS doc_id, d.title AS title
        """
        with self.kg.driver.session() as session:
            records = [dict(r) for r in session.run(query)]

        for r in records:
            result.issues.append({
                "description": f"无领域归属文档: '{r.get('title', 'N/A')}'",
                "node_id": r.get("doc_id", ""),
                "details": "文档未关联到任何SubDomain，建议手动分类或重新入库",
            })

        # fix=True 时仅记录，不自动分类
        if fix and result.issues:
            logger.info(f"发现 {len(result.issues)} 个无领域归属文档，仅报告不自动分类")

        return result

    def check_anchor_overlap_anomaly(self, fix: bool = False) -> LintResult:
        """
        检查锚关键词重叠异常：doc_ids列表重叠度>80%的AnchorKeyword对
        两个关键词关联的文档几乎一样，可能是同义词没合并

        Returns:
            LintResult
        """
        result = LintResult(
            check_name="锚关键词重叠异常检查",
            severity="medium",
        )

        # 获取所有 AnchorKeyword 及其 doc_ids
        query = """
        MATCH (ak:AnchorKeyword)
        WHERE ak.doc_ids IS NOT NULL AND size(ak.doc_ids) > 1
        RETURN ak.keyword AS keyword, ak.doc_ids AS doc_ids
        """
        with self.kg.driver.session() as session:
            records = [dict(r) for r in session.run(query)]

        # 两两比较 doc_ids 重叠度
        seen_pairs = set()
        for i in range(len(records)):
            for j in range(i + 1, len(records)):
                kw1, docs1 = records[i]["keyword"], set(records[i]["doc_ids"])
                kw2, docs2 = records[j]["keyword"], set(records[j]["doc_ids"])

                pair_key = tuple(sorted([kw1, kw2]))
                if pair_key in seen_pairs:
                    continue

                if not docs1 or not docs2:
                    continue

                intersection = docs1 & docs2
                smaller_size = min(len(docs1), len(docs2))
                if smaller_size == 0:
                    continue

                overlap_ratio = len(intersection) / smaller_size
                if overlap_ratio > 0.8:
                    seen_pairs.add(pair_key)
                    result.issues.append({
                        "description": f"锚关键词重叠异常: '{kw1}' ↔ '{kw2}'",
                        "node_id": f"{kw1}|{kw2}",
                        "details": (
                            f"重叠率: {overlap_ratio:.1%}, "
                            f"'{kw1}' 有 {len(docs1)} 个文档, "
                            f"'{kw2}' 有 {len(docs2)} 个文档, "
                            f"共同 {len(intersection)} 个 — 可能是同义词，建议合并"
                        ),
                    })

        # 此项检查不支持自动修复
        if fix and result.issues:
            logger.info(f"发现 {len(result.issues)} 对重叠锚关键词，需人工确认是否合并")

        return result

    def check_missing_cross_domain_links(self, fix: bool = False) -> LintResult:
        """
        检查缺失的跨领域关联：应有但缺失的 OVERLAPS_WITH 关系
        fix=True 时调用 kg.discover_cross_domain_links() 自动发现并创建

        Returns:
            LintResult
        """
        result = LintResult(
            check_name="跨领域关联缺失检查",
            severity="low",
        )

        # 检查哪些 SubDomain 对有共享锚关键词但没有 OVERLAPS_WITH 关系
        query = """
        MATCH (sd1:SubDomain)<-[:CONTAINS_DOC|ALSO_IN_DOMAIN]-(d1:Document)
              -[:HAS_CHUNK]->(c1:Chunk)-[:HAS_ANCHOR]->(ak:AnchorKeyword)
        MATCH (sd2:SubDomain)<-[:CONTAINS_DOC|ALSO_IN_DOMAIN]-(d2:Document)
              -[:HAS_CHUNK]->(c2:Chunk)-[:HAS_ANCHOR]->(ak)
        WHERE sd1 <> sd2
        WITH sd1, sd2, count(DISTINCT ak) AS shared_anchors
        WHERE shared_anchors >= 2
        WITH sd1, sd2, shared_anchors
        WHERE NOT (sd1)-[:OVERLAPS_WITH]->(sd2)
        RETURN sd1.name AS sd1_name, sd2.name AS sd2_name, shared_anchors
        """
        with self.kg.driver.session() as session:
            records = [dict(r) for r in session.run(query)]

        for r in records:
            result.issues.append({
                "description": f"缺失跨领域关联: {r['sd1_name']} ↔ {r['sd2_name']}",
                "node_id": f"{r['sd1_name']}|{r['sd2_name']}",
                "details": f"共享 {r['shared_anchors']} 个锚关键词，建议创建 OVERLAPS_WITH 关系",
            })

        if fix and result.issues:
            try:
                self.kg.discover_cross_domain_links()
                result.fix_applied = len(result.issues)
                logger.info(f"已自动创建 {len(result.issues)} 条跨领域关联")
            except Exception as e:
                result.fix_failed = len(result.issues)
                logger.error(f"自动创建跨领域关联失败: {e}")

        return result
