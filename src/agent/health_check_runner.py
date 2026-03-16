"""Cluster health check runner (BL-020).

Deterministic pipeline — tool execution order is fixed, severity thresholds are
rule-based Python. LLM is NOT used here; findings are derived directly from
structured MCP results so the report is reliable even when the LLM is slow.

Current coverage (v0.2.0 tools only):
  Section 1 — Cluster Overview     list-databases, list-collections
  Section 2 — Query Performance    find on system.profile
  Section 3 — Index Health         collection-indexes on top slow collections

Missing sections (added as P0 backlog items):
  BL-001  Server & connection health   (serverStatus)
  BL-002  Replication health           (replSetGetStatus)
  BL-003  Storage stats                (collStats)
"""

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.config_loader import AppConfig
from utils.mcp_client import MCPClient
from models.health_check_report import (
    HealthCheckReport, HealthSeverity, ReportSection, Recommendation, Signal,
    worst_severity,
)

logger = logging.getLogger(__name__)

REPORTS_DIR = Path("reports")

# Severity thresholds — will move to agent_config.yaml in BL-021
_THRESHOLDS = {
    "slow_query_count_warning": 5,
    "slow_query_count_critical": 20,
    "slow_query_ms_warning": 100,
    "slow_query_ms_critical": 500,
    "full_scan_examined_min": 1000,       # below this, don't flag as full scan
    "full_scan_selectivity_max": 0.01,    # docs_returned / docs_examined
}


class HealthCheckRunner:
    """Runs a complete health check using current MCP tools and produces a report."""

    def __init__(self, config: AppConfig):
        self.config = config
        self._mcp: Optional[MCPClient] = None

    # ── public entry point ─────────────────────────────────────────────────────

    def run(self) -> HealthCheckReport:
        run_id = f"hc_{int(time.time())}"
        timestamp = datetime.utcnow()
        sections: List[ReportSection] = []
        slow_queries: List[Dict[str, Any]] = []

        with MCPClient(self.config.mongodb.monitored_cluster) as mcp:
            self._mcp = mcp

            # Fixed execution order — deterministic, no LLM tool selection
            sections.append(self._section_cluster_overview())
            perf_section, slow_queries = self._section_query_performance()
            sections.append(perf_section)
            top_colls = self._top_slow_collections(slow_queries, n=3)
            sections.append(self._section_index_health(top_colls, slow_queries))

            self._mcp = None

        recommendations = self._build_recommendations(slow_queries, sections)
        overall = worst_severity([s.severity for s in sections])

        report = HealthCheckReport(
            run_id=run_id,
            timestamp=timestamp,
            cluster_uri=self.config.mongodb.monitored_cluster,
            overall_severity=overall,
            sections=sections,
            recommendations=recommendations,
        )

        report.report_path = str(self._save_report(report))
        self._purge_old_reports()
        return report

    # ── Section 1: Cluster Overview ────────────────────────────────────────────

    @staticmethod
    def _parse_name_blocks(blocks: List[str]) -> List[str]:
        """Extract the name token from MCP 'Name: foo, ...' text blocks."""
        names = []
        for b in blocks:
            if b.startswith("Name:"):
                # MCP may return "Name: foo" or "Name: foo, Size: 123 bytes"
                raw = b[len("Name:"):].strip()
                names.append(raw.split(",")[0].strip())
        return names

    def _section_cluster_overview(self) -> ReportSection:
        db_blocks = self._mcp.call_tool("list-databases", {})
        all_dbs = self._parse_name_blocks(db_blocks)
        user_dbs = [d for d in all_dbs if d not in ("admin", "config", "local")]

        collections_by_db: Dict[str, List[str]] = {}
        for db in user_dbs:
            coll_blocks = self._mcp.call_tool("list-collections", {"database": db})
            colls = self._parse_name_blocks(coll_blocks)
            collections_by_db[db] = [c for c in colls if not c.startswith("system.")]

        total_colls = sum(len(v) for v in collections_by_db.values())

        findings = [
            f"{len(user_dbs)} user database(s), {total_colls} collection(s) total.",
        ]
        for db, colls in collections_by_db.items():
            findings.append(f"  {db}: {', '.join(colls) if colls else '(empty)'}")

        return ReportSection(
            name="Cluster Overview",
            severity=HealthSeverity.OK,
            signals=[
                Signal("database_count", len(user_dbs), "databases"),
                Signal("collection_count", total_colls, "collections"),
            ],
            findings=findings,
        )

    # ── Section 2: Query Performance ───────────────────────────────────────────

    def _section_query_performance(self) -> Tuple[ReportSection, List[Dict[str, Any]]]:
        threshold = self.config.agent.slow_query_threshold_ms
        limit = self.config.agent.max_queries_to_analyze

        # Query system.profile across monitored databases
        # TODO (BL-050): iterate all user databases rather than hard-coding testdb
        blocks = self._mcp.call_tool("find", {
            "database": "testdb",
            "collection": "system.profile",
            "filter": {
                "millis": {"$gte": threshold},
                "op": {"$nin": ["getmore", "killCursors"]},
            },
            "sort": {"ts": -1},
            "limit": limit,
        })

        slow_queries: List[Dict[str, Any]] = []
        for block in blocks[1:]:   # first block is a header
            try:
                doc = json.loads(block)
                ns = doc.get("ns", "")
                collection = ns.split(".", 1)[-1] if "." in ns else ns
                slow_queries.append({
                    "collection": collection,
                    "query": doc.get("query", doc.get("command", {})),
                    "execution_time_ms": doc.get("millis", 0),
                    "docs_examined": doc.get("docsExamined", 0),
                    "docs_returned": doc.get("nreturned", 0),
                    "operation": doc.get("op", "query"),
                })
            except (json.JSONDecodeError, AttributeError):
                continue

        count = len(slow_queries)
        max_ms = max((q["execution_time_ms"] for q in slow_queries), default=0)
        avg_ms = (sum(q["execution_time_ms"] for q in slow_queries) / count) if count else 0.0

        # Rule-based severity
        if count == 0:
            severity = HealthSeverity.OK
        elif count >= _THRESHOLDS["slow_query_count_critical"] or max_ms >= _THRESHOLDS["slow_query_ms_critical"]:
            severity = HealthSeverity.CRITICAL
        elif count >= _THRESHOLDS["slow_query_count_warning"] or max_ms >= _THRESHOLDS["slow_query_ms_warning"]:
            severity = HealthSeverity.WARNING
        else:
            severity = HealthSeverity.WARNING   # any slow queries → at least warning

        # Group by collection for findings
        by_coll: Dict[str, List[Dict]] = {}
        for q in slow_queries:
            by_coll.setdefault(q["collection"], []).append(q)

        findings: List[str] = []
        if count == 0:
            findings.append(f"No slow queries above {threshold}ms threshold — profiler is capturing data.")
        else:
            findings.append(
                f"{count} slow operation(s) found  (threshold: {threshold}ms, max: {max_ms}ms, avg: {avg_ms:.0f}ms)."
            )
            for coll, qs in sorted(by_coll.items(), key=lambda x: -len(x[1])):
                c_max = max(q["execution_time_ms"] for q in qs)
                c_avg = sum(q["execution_time_ms"] for q in qs) / len(qs)
                c_exam = max(q["docs_examined"] for q in qs)
                findings.append(
                    f"  {coll}: {len(qs)} op(s)  max {c_max}ms  avg {c_avg:.0f}ms  "
                    f"up to {c_exam:,} docs examined"
                )

        section = ReportSection(
            name="Query Performance",
            severity=severity,
            signals=[
                Signal("slow_query_count", count, "queries", _THRESHOLDS["slow_query_count_warning"]),
                Signal("max_execution_ms", max_ms, "ms", _THRESHOLDS["slow_query_ms_warning"]),
                Signal("avg_execution_ms", round(avg_ms, 1), "ms"),
            ],
            findings=findings,
        )
        return section, slow_queries

    # ── Section 3: Index Health ─────────────────────────────────────────────────

    def _section_index_health(
        self, collections: List[str], slow_queries: List[Dict[str, Any]]
    ) -> ReportSection:
        if not collections:
            return ReportSection(
                name="Index Health",
                severity=HealthSeverity.OK,
                signals=[Signal("collections_checked", 0, "collections")],
                findings=["No slow-query collections to analyse."],
            )

        index_data: Dict[str, List[str]] = {}
        for coll in collections:
            blocks = self._mcp.call_tool("collection-indexes", {
                "database": "testdb",
                "collection": coll,
            })
            index_data[coll] = [b for b in blocks if b.startswith("Field:")]

        # Collections where only the _id index exists
        under_indexed = [c for c, idx in index_data.items() if len(idx) <= 1]

        severity = HealthSeverity.CRITICAL if under_indexed else HealthSeverity.OK

        findings: List[str] = []
        for coll, indexes in index_data.items():
            findings.append(f"  {coll}: {len(indexes)} index(es)")
            for idx in indexes:
                findings.append(f"    {idx}")
        if under_indexed:
            findings.append(
                f"Under-indexed: {', '.join(under_indexed)} — "
                f"only _id index present despite appearing in slow query log."
            )

        return ReportSection(
            name="Index Health",
            severity=severity,
            signals=[
                Signal("collections_checked", len(collections), "collections"),
                Signal("under_indexed_collections", len(under_indexed), "collections", 0),
            ],
            findings=findings,
        )

    # ── helpers ────────────────────────────────────────────────────────────────

    def _top_slow_collections(self, slow_queries: List[Dict], n: int = 3) -> List[str]:
        counts: Dict[str, int] = {}
        for q in slow_queries:
            c = q["collection"]
            if c and not c.startswith("system."):
                counts[c] = counts.get(c, 0) + 1
        return [c for c, _ in sorted(counts.items(), key=lambda x: -x[1])[:n]]

    def _build_recommendations(
        self,
        slow_queries: List[Dict[str, Any]],
        sections: List[ReportSection],
    ) -> List[Recommendation]:
        recs: List[Recommendation] = []
        seen: set = set()

        for q in slow_queries:
            coll = q["collection"]
            if coll in seen or not coll or coll.startswith("system."):
                continue
            seen.add(coll)

            examined = q.get("docs_examined", 0)
            returned = q.get("docs_returned", 0)
            ms = q.get("execution_time_ms", 0)

            selectivity = returned / examined if examined else 1.0
            is_full_scan = (
                examined >= _THRESHOLDS["full_scan_examined_min"]
                and selectivity <= _THRESHOLDS["full_scan_selectivity_max"]
            )

            if not is_full_scan:
                continue

            query_obj = q.get("query", {})
            # MongoDB 8 profiler stores commands as {"find": "coll", "filter": {...}}
            # Extract field names from the actual filter sub-object
            if isinstance(query_obj, dict):
                filter_obj = query_obj.get("filter", query_obj.get("query", query_obj))
                filter_fields = [
                    f for f in (filter_obj.keys() if isinstance(filter_obj, dict) else [])
                    if not f.startswith("$") and f not in ("find", "filter", "limit", "sort")
                ]
            else:
                filter_fields = []

            if filter_fields:
                index_spec = ", ".join(f'"{f}": 1' for f in filter_fields[:2])
                action = f"db.{coll}.createIndex({{{index_spec}}})"
                confidence = "high"
            else:
                action = f"Identify query filter fields on {coll} and create a covering index"
                confidence = "medium"

            evidence = (
                f"{examined:,} docs examined, {returned} returned ({ms}ms) — "
                f"selectivity {selectivity:.4f}, likely full collection scan"
            )

            recs.append(Recommendation(
                priority="high",
                collection=coll,
                action=action,
                evidence=evidence,
                confidence=confidence,
            ))

        return recs

    # ── persistence ────────────────────────────────────────────────────────────

    def _save_report(self, report: HealthCheckReport) -> Path:
        REPORTS_DIR.mkdir(exist_ok=True)
        filename = f"health_{report.timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.json"
        path = REPORTS_DIR / filename
        path.write_text(json.dumps(report.to_dict(), indent=2, default=str))
        logger.info("Health check report saved: %s", path)
        return path

    def _purge_old_reports(self, days: int = 90) -> None:
        cutoff = datetime.utcnow() - timedelta(days=days)
        for f in REPORTS_DIR.glob("health_*.json"):
            if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                f.unlink()
                logger.info("Purged old report: %s", f)
