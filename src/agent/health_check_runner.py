"""Cluster health check runner (BL-020 through BL-009).

Deterministic pipeline — tool execution order is fixed, severity thresholds are
rule-based Python. LLM is NOT used here; findings are derived directly from
structured data so scheduled runs are reliable and fast.

Data access:
  §1–7  MCPClient → MongoDB MCP Server (--readOnly)
  §8    Direct PyMongo admin.command("serverStatus") via MongoDBManager
        (read-only admin command; not exposed by the MCP toolset)

MCP tool availability (confirmed via list_tools()):
  ✅ list-databases, list-collections, find, aggregate, count
  ✅ collection-storage-size, db-stats, collection-indexes
  ✅ serverStatus — obtained via direct PyMongo (BL-009)
  ⚠️  replSetGetStatus — NOT available via MCP.
       Workaround: local.system.replset → RS config; local.oplog.rs → oplog window.
       Per-member replication lag not obtainable.

Section order:
  1  Cluster Overview      list-databases, list-collections (MCP)
  2  Server Health         local.startup_log, db-stats (MCP / BL-001)
  3  Replication Health    local.system.replset, local.oplog.rs (MCP / BL-002)
  4  Storage & Capacity    collection-storage-size, count, db-stats (MCP / BL-003)
  5  Query Performance     find on system.profile (MCP)
  6  Index Health          collection-indexes on top slow collections (MCP)
  7  Index Usage           aggregate $indexStats (MCP / BL-004)
  8  Operations            admin.command("serverStatus") via direct PyMongo (BL-009)
"""

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.config_loader import AppConfig
from utils.mcp_client import MCPClient
from utils.mongodb_client import MongoDBManager
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
    "disk_used_pct_warning": 80,
    "disk_used_pct_critical": 90,
    "oplog_window_warning_hours": 24,
    "oplog_window_critical_hours": 4,
    "full_scan_examined_min": 1000,
    "full_scan_selectivity_max": 0.01,
    # §8 Operations (BL-009)
    "cache_hit_ratio_warning": 0.95,   # below 95 % → warning
    "cache_hit_ratio_critical": 0.80,  # below 80 % → critical
    "lock_wait_pct_warning": 5.0,      # lock wait > 5 % → warning
    "lock_wait_pct_critical": 20.0,    # lock wait > 20 % → critical
    "query_targeting_warning": 10.0,   # scanned-to-returned ratio > 10 → warning
    "query_targeting_critical": 100.0, # scanned-to-returned ratio > 100 → critical
    "memory_resident_warning_mb": 4096,   # RSS > 4 GB → warning (indicative)
    "memory_resident_critical_mb": 8192,  # RSS > 8 GB → critical (indicative)
}

_SYSTEM_DBS = {"admin", "config", "local"}


class HealthCheckRunner:
    """Runs a complete cluster health check using MCP tools and produces a report."""

    def __init__(
        self,
        config: AppConfig,
        cluster_uri: Optional[str] = None,
        cluster_name: str = "",
        save_report: bool = True,
    ):
        self.config = config
        self._cluster_uri = cluster_uri or config.mongodb.monitored_cluster
        self._cluster_name = cluster_name
        self._save_report_flag = save_report
        self._mcp: Optional[MCPClient] = None
        self._mongo: Optional[MongoDBManager] = None

    # ── public entry point ─────────────────────────────────────────────────────

    def run(self) -> HealthCheckReport:
        run_id = f"hc_{int(time.time())}"
        timestamp = datetime.utcnow()
        sections: List[ReportSection] = []
        slow_queries: List[Dict[str, Any]] = []

        # Direct PyMongo connection for §8 (serverStatus — not in MCP toolset)
        self._mongo = MongoDBManager(
            agent_store_uri=self.config.mongodb.agent_store,
            monitored_cluster_uri=self._cluster_uri,
        )

        # BL-021: baseline-aware severity — load prior runs from agent_memory
        from agent.baseline_manager import BaselineManager
        self._baseline = BaselineManager(
            self.config.mongodb.agent_store, self._cluster_uri
        )
        self._baseline.load()

        try:
            with MCPClient(self._cluster_uri) as mcp:
                self._mcp = mcp

                # Fetch user databases once — shared by sections 1, 3, 4, 7
                user_dbs = [d for d in self._mcp.list_databases() if d not in _SYSTEM_DBS]

                # Fixed, deterministic section order
                sections.append(self._section_cluster_overview(user_dbs))
                sections.append(self._section_server_health())                   # BL-001
                sections.append(self._section_replication_health())              # BL-002
                sections.append(self._section_storage_stats(user_dbs))          # BL-003
                perf_section, slow_queries = self._section_query_performance(user_dbs)
                sections.append(perf_section)
                top_colls = self._top_slow_collections(slow_queries, n=3)
                sections.append(self._section_index_health(top_colls))
                usage_section, unused_indexes = self._section_index_usage(user_dbs)  # BL-004
                sections.append(usage_section)

                self._mcp = None

            # §8 Operations — direct PyMongo serverStatus (BL-009)
            sections.append(self._section_operations())
        finally:
            self._mongo.close_connections()
            self._mongo = None

        recommendations = self._build_recommendations(slow_queries, sections, unused_indexes)
        overall = worst_severity([s.severity for s in sections])

        report = HealthCheckReport(
            run_id=run_id,
            timestamp=timestamp,
            cluster_uri=self._cluster_uri,
            cluster_name=self._cluster_name,
            overall_severity=overall,
            sections=sections,
            recommendations=recommendations,
        )

        # BL-034: LLM enrichment — cross-section reasoning on top of rule-based recs
        if self.config.agent.llm_recommendations:
            from agent.llm_recommender import LLMRecommender
            logger.info("BL-034: running LLM recommendation enrichment")
            report.recommendations = LLMRecommender(self.config).enrich(report)

        # BL-021: persist this run's metrics for future baseline comparisons
        self._baseline.record_from_report(report)

        if self._save_report_flag:
            report.report_path = str(self._save_report(report))
            self._purge_old_reports()
        return report

    # ── Section 1: Cluster Overview ────────────────────────────────────────────

    def _section_cluster_overview(self, user_dbs: List[str]) -> ReportSection:
        collections_by_db: Dict[str, List[str]] = {}
        for db in user_dbs:
            colls = self._mcp.list_collections(db)
            collections_by_db[db] = [c for c in colls if not c.startswith("system.")]

        total_colls = sum(len(v) for v in collections_by_db.values())
        findings = [f"{len(user_dbs)} user database(s), {total_colls} collection(s) total."]
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

    # ── Section 2: Server Health (BL-001) ─────────────────────────────────────

    def _section_server_health(self) -> ReportSection:
        """
        Available via MCP:   version, hostname, uptime (from local.startup_log)
                             disk used / total (from db-stats fsUsedSize/fsTotalSize)
        NOT available:       connections, memory (RSS), page faults, lock stats
                             — these require serverStatus which has no MCP equivalent.
        """
        # Version, hostname, uptime from startup_log
        version, hostname, uptime_hours = "unknown", "unknown", 0.0
        for doc in self._mcp.find("local", "startup_log", sort={"startTime": -1}, limit=1):
            version = doc.get("buildinfo", {}).get("version", "unknown")
            hostname = doc.get("hostname", "unknown")
            start_str = doc.get("startTime", "")
            if start_str:
                try:
                    start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    uptime_hours = round(
                        (datetime.now(timezone.utc) - start_dt).total_seconds() / 3600, 1
                    )
                except ValueError:
                    pass

        # Disk usage from db-stats (fsUsedSize / fsTotalSize is cluster-wide)
        stats = self._mcp.db_stats("admin")
        fs_used  = stats.get("fsUsedSize",  0)
        fs_total = stats.get("fsTotalSize", 0)
        disk_used_gb  = round(fs_used  / 1_073_741_824, 1)
        disk_total_gb = round(fs_total / 1_073_741_824, 1)
        disk_used_pct = round(fs_used / fs_total * 100, 1) if fs_total else 0.0

        # BL-021: baseline-aware disk severity (hard limit: > 95% always CRITICAL)
        severity, disk_note = self._baseline.assess(
            "disk_used_pct", disk_used_pct,
            static_warn=_THRESHOLDS["disk_used_pct_warning"],
            static_crit=_THRESHOLDS["disk_used_pct_critical"],
        )

        findings = [
            f"MongoDB {version}  ·  host: {hostname}  ·  uptime: {uptime_hours}h",
            f"Filesystem disk: {disk_used_gb} GB used of {disk_total_gb} GB ({disk_used_pct}%)",
            "Note: disk figures are from MongoDB's filesystem view (fsUsedSize) and may differ"
            " from OS tools on macOS/APFS due to purgeable space and snapshots."
            " Reliable on Linux production servers.",
        ]
        if self._baseline.is_cold_start:
            findings.append(f"Severity assessment: {self._baseline.cold_start_note()}")
        if severity != HealthSeverity.OK:
            label = ("CRITICAL: risk of mongod write failures."
                     if severity == HealthSeverity.CRITICAL else "WARNING: monitor closely.")
            note_str = f"  {disk_note}" if disk_note else ""
            findings.append(f"Filesystem disk at {disk_used_pct}% — {label}{note_str}")

        return ReportSection(
            name="Server Health",
            severity=severity,
            signals=[
                Signal("mongodb_version", version),
                Signal("uptime_hours", uptime_hours, "hours"),
                Signal("filesystem_disk_used_gb", disk_used_gb, "GB"),
                Signal("filesystem_disk_used_pct", disk_used_pct, "%", _THRESHOLDS["disk_used_pct_warning"]),
            ],
            findings=findings,
        )

    # ── Section 3: Replication Health (BL-002) ─────────────────────────────────

    def _section_replication_health(self) -> ReportSection:
        """
        Available via MCP:   RS config/members (local.system.replset)
                             oplog window in hours (local.oplog.rs first/last ts)
        NOT available:       member health states (PRIMARY/SECONDARY/DOWN)
                             per-member replication lag
                             — these require replSetGetStatus which has no MCP equivalent.
        """
        # RS config
        rs_config_docs = self._mcp.find("local", "system.replset", limit=1)
        is_replica_set = bool(rs_config_docs)
        rs_name = rs_config_docs[0].get("_id", "unknown") if rs_config_docs else None
        members = rs_config_docs[0].get("members", []) if rs_config_docs else []

        # Oplog window
        head_docs = self._mcp.find("local", "oplog.rs", sort={"ts": -1}, limit=1)
        tail_docs = self._mcp.find("local", "oplog.rs", sort={"ts": 1}, limit=1)

        def _ts_seconds(doc: Dict) -> Optional[int]:
            ts = doc.get("ts", {})
            if not isinstance(ts, dict) or "$timestamp" not in ts:
                return None
            inner = ts["$timestamp"]
            # Extended JSON v2: {"$timestamp": {"t": <seconds>, "i": <ordinal>}}
            if isinstance(inner, dict):
                return inner.get("t")
            # MCP packed form: {"$timestamp": "<uint64_string>"} — seconds in upper 32 bits
            if isinstance(inner, (str, int)):
                return int(inner) >> 32
            return None

        head_ts = _ts_seconds(head_docs[0]) if head_docs else None
        tail_ts = _ts_seconds(tail_docs[0]) if tail_docs else None
        oplog_window_hours = (
            round((head_ts - tail_ts) / 3600, 1) if head_ts and tail_ts else None
        )

        # Standalone — nothing to report
        if not is_replica_set and oplog_window_hours is None:
            return ReportSection(
                name="Replication Health",
                severity=HealthSeverity.OK,
                signals=[Signal("mode", "standalone")],
                findings=["Standalone instance — replication not configured."],
            )

        # BL-021: baseline-aware oplog severity (hard limit: < 2h always CRITICAL)
        severity = HealthSeverity.OK
        _oplog_note = ""
        if oplog_window_hours is not None:
            severity, _oplog_note = self._baseline.assess(
                "oplog_window_hours", oplog_window_hours,
                static_warn=_THRESHOLDS["oplog_window_warning_hours"],
                static_crit=_THRESHOLDS["oplog_window_critical_hours"],
                higher_is_worse=False,
            )

        findings: List[str] = []
        if is_replica_set:
            findings.append(f"Replica set: {rs_name}  ·  {len(members)} configured member(s)")
            for m in members:
                host = m.get("host", "?")
                pri  = m.get("priority", "?")
                hidden = "  [hidden]" if m.get("hidden") else ""
                findings.append(f"  {host}  priority={pri}{hidden}")
            findings.append(
                "Not available via MCP: member health states (PRIMARY/SECONDARY/DOWN), "
                "per-member replication lag — requires replSetGetStatus."
            )
        if oplog_window_hours is not None:
            note_str = f"  {_oplog_note}" if _oplog_note else ""
            findings.append(f"Oplog window: {oplog_window_hours}h{note_str}")
            if severity != HealthSeverity.OK:
                findings.append(
                    f"Oplog window ({oplog_window_hours}h) is below the "
                    f"{_THRESHOLDS['oplog_window_warning_hours']}h minimum — "
                    f"risk of replication failure after extended secondary downtime."
                )

        signals: List[Signal] = [Signal("replica_set_members", len(members), "members")]
        if oplog_window_hours is not None:
            signals.append(Signal("oplog_window_hours", oplog_window_hours, "hours",
                                  _THRESHOLDS["oplog_window_warning_hours"]))

        return ReportSection(
            name="Replication Health",
            severity=severity,
            signals=signals,
            findings=findings,
        )

    # ── Section 4: Storage & Capacity (BL-003) ─────────────────────────────────

    def _section_storage_stats(self, user_dbs: List[str]) -> ReportSection:
        """collection-storage-size + count + db-stats per database."""
        coll_stats: List[Dict[str, Any]] = []
        total_data_mb = 0.0
        total_index_mb = 0.0
        disk_used_pct = 0.0

        for db in user_dbs:
            db_stats = self._mcp.db_stats(db)
            total_data_mb  += db_stats.get("dataSize",  0) / 1_048_576
            total_index_mb += db_stats.get("indexSize", 0) / 1_048_576
            fs_used  = db_stats.get("fsUsedSize",  0)
            fs_total = db_stats.get("fsTotalSize", 0)
            if fs_total:
                disk_used_pct = round(fs_used / fs_total * 100, 1)

            user_colls = [c for c in self._mcp.list_collections(db) if not c.startswith("system.")]
            for coll in user_colls:
                size_mb = self._mcp.collection_storage_size(db, coll)
                doc_count = self._mcp.count(db, coll)
                avg_bytes = round(size_mb * 1_048_576 / doc_count) if doc_count else 0
                coll_stats.append({
                    "db": db, "collection": coll,
                    "size_mb": size_mb, "doc_count": doc_count, "avg_bytes": avg_bytes,
                })

        coll_stats.sort(key=lambda x: -x["size_mb"])

        # Severity based on MongoDB data size, not filesystem (filesystem is in Server Health)
        severity = HealthSeverity.OK

        findings = [
            f"MongoDB data: {total_data_mb:.1f} MB  ·  Indexes: {total_index_mb:.1f} MB"
            f"  ·  {len(coll_stats)} collection(s) analysed",
            "Collections by size (largest first):",
        ]
        for s in coll_stats[:5]:
            findings.append(
                f"  {s['db']}.{s['collection']}: {s['size_mb']} MB  "
                f"{s['doc_count']:,} docs  avg {s['avg_bytes']} bytes/doc"
            )

        return ReportSection(
            name="Storage & Capacity",
            severity=severity,
            signals=[
                Signal("mongodb_data_mb",  round(total_data_mb, 1),  "MB"),
                Signal("mongodb_index_mb", round(total_index_mb, 1), "MB"),
                Signal("collections_analysed", len(coll_stats), "collections"),
            ],
            findings=findings,
        )

    # ── Section 5: Query Performance ───────────────────────────────────────────

    def _section_query_performance(self, user_dbs: List[str]) -> Tuple[ReportSection, List[Dict[str, Any]]]:
        threshold = self.config.agent.slow_query_threshold_ms
        limit     = self.config.agent.max_queries_to_analyze

        slow_queries: List[Dict[str, Any]] = []
        for db in user_dbs:
            for doc in self._mcp.find(
                db, "system.profile",
                filter={"millis": {"$gte": threshold}, "op": {"$nin": ["getmore", "killCursors"]}},
                sort={"ts": -1},
                limit=limit,
            ):
                ns = doc.get("ns", "")
                db_name, collection = ns.split(".", 1) if "." in ns else (db, ns)
                cmd = doc.get("command", {}) if isinstance(doc.get("command"), dict) else {}
                slow_queries.append({
                    "db":               db_name,
                    "collection":       collection,
                    "query":            doc.get("query", cmd),
                    "execution_time_ms":    doc.get("millis", 0),
                    "docs_examined":        doc.get("docsExamined", 0),
                    "docs_returned":        doc.get("nreturned", 0),
                    "keys_examined":        doc.get("keysExamined", 0),
                    "has_sort_stage":       bool(doc.get("hasSortStage", False)),
                    "sort_spills":          int(doc.get("sortSpills", 0) or 0),
                    "sort_spill_bytes":     int(doc.get("sortSpillBytes", 0) or 0),
                    "plan_summary":         doc.get("planSummary", ""),
                    "planning_time_us":     int(doc.get("planningTimeMicros", 0) or 0),
                    "num_yield":            int(doc.get("numYield", 0) or 0),
                    "operation":            doc.get("op", "query"),
                    "sort_fields":          list(cmd.get("sort", {}).keys())
                                            if isinstance(cmd.get("sort"), dict) else [],
                })

        count  = len(slow_queries)
        max_ms = max((q["execution_time_ms"] for q in slow_queries), default=0)
        avg_ms = sum(q["execution_time_ms"] for q in slow_queries) / count if count else 0.0

        # Scan & sort aggregate metrics
        collscan_count    = sum(1 for q in slow_queries if "COLLSCAN" in q["plan_summary"])
        sort_stage_count  = sum(1 for q in slow_queries if q["has_sort_stage"])
        sort_spill_count  = sum(1 for q in slow_queries if q["sort_spills"] > 0)
        total_spill_bytes = sum(q["sort_spill_bytes"] for q in slow_queries)

        # BL-021: baseline-aware slow query severity
        if count == 0:
            severity = HealthSeverity.OK
            _count_note = ""
            _ms_note = ""
        else:
            count_sev, _count_note = self._baseline.assess(
                "slow_query_count", count,
                static_warn=_THRESHOLDS["slow_query_count_warning"],
                static_crit=_THRESHOLDS["slow_query_count_critical"],
            )
            ms_sev, _ms_note = self._baseline.assess(
                "max_execution_ms", float(max_ms),
                static_warn=_THRESHOLDS["slow_query_ms_warning"],
                static_crit=_THRESHOLDS["slow_query_ms_critical"],
            )
            severity = worst_severity([count_sev, ms_sev])
        # Sort spills are always at least WARNING — spilling to disk indicates memory pressure
        if sort_spill_count > 0:
            severity = worst_severity([severity, HealthSeverity.WARNING])

        by_coll: Dict[str, List[Dict]] = {}
        for q in slow_queries:
            by_coll.setdefault(q["collection"], []).append(q)

        findings: List[str] = []
        if count == 0:
            findings.append(f"No slow queries above {threshold}ms — profiler is active.")
        else:
            count_note_str = f"  {_count_note}" if _count_note else ""
            ms_note_str    = f"  {_ms_note}"    if _ms_note    else ""
            findings.append(
                f"{count} slow op(s){count_note_str}  ·  threshold: {threshold}ms  "
                f"·  max: {max_ms}ms{ms_note_str}  ·  avg: {avg_ms:.0f}ms"
            )
            findings.append(
                f"{collscan_count} of {count} op(s) used COLLSCAN (no index)  "
                f"·  {sort_stage_count} required in-memory sort stage"
                + (f"  ·  {sort_spill_count} sort(s) spilled to disk "
                   f"({total_spill_bytes / 1024:.0f} KB)" if sort_spill_count else "")
            )
            if sort_spill_count:
                findings.append(
                    f"  Sort spills detected — queries exceeded in-memory sort buffer. "
                    f"Add indexes that cover the sort field to eliminate in-memory sorting."
                )
            findings.append("")
            for coll, qs in sorted(by_coll.items(), key=lambda x: -len(x[1])):
                c_max    = max(q["execution_time_ms"] for q in qs)
                c_avg    = sum(q["execution_time_ms"] for q in qs) / len(qs)
                c_exam   = max(q["docs_examined"] for q in qs)
                c_ret    = max(q["docs_returned"] for q in qs) if any(q["docs_returned"] for q in qs) else 0
                c_keys   = max(q["keys_examined"] for q in qs)
                c_plans  = {q["plan_summary"] for q in qs if q["plan_summary"]}
                c_sorts  = sum(1 for q in qs if q["has_sort_stage"])
                # Targeting ratio: docs scanned per doc returned (lower = better)
                targeting = round(c_exam / c_ret, 1) if c_ret else float("inf")
                targeting_str = f"{targeting:,.0f}×" if targeting != float("inf") else "∞"
                plan_str = " / ".join(sorted(c_plans)) if c_plans else "unknown"
                sort_str = f"  sort stage: {c_sorts}/{len(qs)} op(s)" if c_sorts else ""
                findings.append(
                    f"  {coll}  [{len(qs)} op(s)  max {c_max}ms  avg {c_avg:.0f}ms]"
                )
                findings.append(
                    f"    plan: {plan_str}  ·  "
                    f"docs examined: {c_exam:,}  ·  keys examined: {c_keys:,}  ·  "
                    f"targeting ratio: {targeting_str}{sort_str}"
                )

        return ReportSection(
            name="Query Performance",
            severity=severity,
            signals=[
                Signal("slow_query_count",   count,            "queries", _THRESHOLDS["slow_query_count_warning"]),
                Signal("collscan_count",      collscan_count,   "queries", 0),
                Signal("sort_stage_count",    sort_stage_count, "queries", 0),
                Signal("sort_spill_count",    sort_spill_count, "queries", 0),
                Signal("max_execution_ms",    max_ms,           "ms",      _THRESHOLDS["slow_query_ms_warning"]),
                Signal("avg_execution_ms",    round(avg_ms, 1), "ms"),
            ],
            findings=findings,
        ), slow_queries

    # ── Section 6: Index Health ─────────────────────────────────────────────────

    def _section_index_health(self, collections: List[Dict[str, str]]) -> ReportSection:
        """collections: [{"db": "...", "collection": "..."}] from _top_slow_collections."""
        if not collections:
            return ReportSection(
                name="Missing Indexes",
                severity=HealthSeverity.OK,
                signals=[Signal("collections_checked", 0, "collections")],
                findings=["No slow-query collections to analyse."],
            )

        # index_data keyed by "db.collection" for display
        index_data: Dict[str, List[Dict]] = {}
        for item in collections:
            db, coll = item["db"], item["collection"]
            index_data[f"{db}.{coll}"] = self._mcp.collection_indexes(db, coll)

        under_indexed = [fq for fq, idx in index_data.items() if len(idx) <= 1]
        ok_count = len(collections) - len(under_indexed)
        severity = HealthSeverity.CRITICAL if under_indexed else HealthSeverity.OK

        findings: List[str] = []
        if under_indexed:
            findings.append(
                f"{len(under_indexed)} of {len(collections)} slow-query collection(s) have no "
                f"custom indexes — every field query causes a full collection scan."
            )
            for fq_coll in under_indexed:
                findings.append(
                    f'  Collection "{fq_coll}": only _id present — add indexes for queried fields.'
                )
            if ok_count:
                findings.append(f"{ok_count} collection(s) have adequate indexes.")
        else:
            findings.append(
                f"All {len(collections)} slow-query collection(s) have custom indexes in place."
            )

        return ReportSection(
            name="Missing Indexes",
            severity=severity,
            signals=[
                Signal("collections_checked",       len(collections),    "collections"),
                Signal("under_indexed_collections", len(under_indexed),  "collections", 0),
            ],
            findings=findings,
        )

    # ── Section 7: Index Usage (BL-004) ────────────────────────────────────────

    def _section_index_usage(self, user_dbs: List[str]) -> Tuple[ReportSection, List[Dict[str, Any]]]:
        """aggregate $indexStats — ops count per index since last mongod restart."""
        all_indexes: List[Dict[str, Any]] = []

        for db in user_dbs:
            user_colls = [c for c in self._mcp.list_collections(db) if not c.startswith("system.")]
            for coll in user_colls:
                docs = self._mcp.aggregate(db, coll, [{"$indexStats": {}}])
                for doc in docs:
                    ops_raw = doc.get("accesses", {}).get("ops", 0)
                    ops = ops_raw.get("low", 0) if isinstance(ops_raw, dict) else int(ops_raw)
                    since = str(doc.get("accesses", {}).get("since", ""))[:10]
                    name  = doc.get("name", "?")
                    all_indexes.append({
                        "db": db, "collection": coll,
                        "name": name,
                        "key":  doc.get("key", {}),
                        "ops":  ops,
                        "since": since,
                        "is_id": name == "_id_",
                    })

        unused = [i for i in all_indexes if i["ops"] == 0 and not i["is_id"]]
        used   = [i for i in all_indexes if i["ops"] > 0]
        custom = [i for i in all_indexes if not i["is_id"]]
        severity = HealthSeverity.WARNING if unused else HealthSeverity.OK

        findings: List[str] = []
        if unused:
            findings.append(
                f"{len(unused)} of {len(custom)} custom index(es) have never been used since "
                f"last restart — they add write overhead and storage cost with no read benefit."
            )
            _CAP = 10
            for idx in unused[:_CAP]:
                findings.append(
                    f'  {idx["db"]}.{idx["collection"]} → "{idx["name"]}"  since {idx["since"]}'
                )
            if len(unused) > _CAP:
                findings.append(f"  … and {len(unused) - _CAP} more unused index(es).")
            findings.append(
                "Review with the app team before dropping — confirm no seasonal or batch queries."
            )
        else:
            findings.append(
                f"All {len(custom)} custom index(es) across "
                f"{len({i['collection'] for i in all_indexes})} collection(s) are actively used."
            )

        if used:
            top = sorted(used, key=lambda x: -x["ops"])[:3]
            findings.append(
                "Most-used: " + ", ".join(
                    f'{i["collection"]}.{i["name"]} ({i["ops"]:,} ops)' for i in top
                )
            )

        return ReportSection(
            name="Unused Indexes",
            severity=severity,
            signals=[
                Signal("total_indexes",  len(all_indexes), "indexes"),
                Signal("unused_indexes", len(unused),      "indexes", 0),
                Signal("used_indexes",   len(used),        "indexes"),
            ],
            findings=findings,
        ), unused

    # ── Section 8: Operations / serverStatus (BL-009) ──────────────────────────

    def _section_operations(self) -> ReportSection:
        """Fetch serverStatus via direct PyMongo and derive operational health signals.

        Metrics captured:
          opcounters   → reads/sec, writes/sec, getmore rate (totals since start)
          mem          → resident MB, virtual MB
          extra_info   → user_time_us (CPU), page_faults
          wiredTiger   → cache hit ratio, cache bytes used/max, eviction pressure
          locks        → global lock wait percentage
          metrics      → cluster-level query targeting ratio, scanAndOrder count
        """
        if self._mongo is None:
            return ReportSection(
                name="Operations",
                severity=HealthSeverity.WARNING,
                signals=[],
                findings=["serverStatus unavailable — MongoDBManager not initialised."],
            )

        ss = self._mongo.get_server_status()
        if ss is None:
            return ReportSection(
                name="Operations",
                severity=HealthSeverity.WARNING,
                signals=[],
                findings=["serverStatus command failed or is unavailable on this deployment."],
            )

        findings: List[str] = []
        signals: List[Signal] = []
        severities: List[HealthSeverity] = [HealthSeverity.OK]

        # ── Throughput (opcounters) — kept in findings only, not as cards ──────────
        opcounters = ss.get("opcounters", {})
        reads       = int(opcounters.get("query",   0))
        writes      = int(opcounters.get("insert",  0)) + int(opcounters.get("update", 0)) + int(opcounters.get("delete", 0))
        getmores    = int(opcounters.get("getmore", 0))
        commands    = int(opcounters.get("command", 0))
        # Cumulative totals have no actionable threshold — surfaced as context, not cards
        findings.append(
            f"Throughput since restart: reads {reads:,}  writes {writes:,}"
            + (f"  getmores {getmores:,}" if getmores else "")
        )

        # ── Memory ─────────────────────────────────────────────────────────────
        mem = ss.get("mem", {})
        rss_mb  = int(mem.get("resident", 0))
        # virtual MB omitted — always large on 64-bit, never actionable
        signals.append(Signal("memory_resident_mb", rss_mb, "MB", _THRESHOLDS["memory_resident_warning_mb"]))
        findings.append(f"Memory: {rss_mb:,} MB resident RAM")
        if rss_mb >= _THRESHOLDS["memory_resident_critical_mb"]:
            severities.append(HealthSeverity.CRITICAL)
            findings.append(
                f"  Resident memory ({rss_mb:,} MB) exceeds critical threshold "
                f"({_THRESHOLDS['memory_resident_critical_mb']:,} MB) — review WiredTiger cache size and working set."
            )
        elif rss_mb >= _THRESHOLDS["memory_resident_warning_mb"]:
            severities.append(HealthSeverity.WARNING)
            findings.append(
                f"  Resident memory ({rss_mb:,} MB) is elevated — monitor for growth."
            )

        # ── Page faults ─────────────────────────────────────────────────────────
        # Cumulative since restart — any healthy server will have some.
        # Shown as info only; severity driven by baseline deviation, not raw count.
        extra = ss.get("extra_info", {})
        page_faults = int(extra.get("page_faults", 0))
        if page_faults > 0:
            signals.append(Signal("page_faults", page_faults, "faults (cumulative)"))
            findings.append(f"Page faults: {page_faults:,} since restart")

        # ── WiredTiger cache ────────────────────────────────────────────────────
        wt_cache = ss.get("wiredTiger", {}).get("cache", {})
        cache_used  = wt_cache.get("bytes currently in the cache",   0)
        cache_max   = wt_cache.get("maximum bytes configured",       0)
        pages_read  = wt_cache.get("pages read into cache",          0)
        pages_req   = wt_cache.get("pages requested from the cache", 0)

        cache_used_mb = round(cache_used / (1024 ** 2), 1) if cache_used else 0
        cache_max_mb  = round(cache_max  / (1024 ** 2), 1) if cache_max  else 0
        cache_util_pct = round(cache_used / cache_max * 100, 1) if cache_max else 0.0

        # Hit ratio: fraction of pages served from cache (vs read from disk)
        if pages_req > 0:
            hit_ratio = round(1.0 - pages_read / pages_req, 4)
        else:
            hit_ratio = 1.0

        # BL-021: baseline-aware cache hit ratio severity
        cache_hit_pct = round(hit_ratio * 100, 1)
        cache_sev, cache_note = self._baseline.assess(
            "cache_hit_ratio_pct", cache_hit_pct,
            static_warn=_THRESHOLDS["cache_hit_ratio_warning"] * 100,
            static_crit=_THRESHOLDS["cache_hit_ratio_critical"] * 100,
            higher_is_worse=False,
        )
        severities.append(cache_sev)
        # Single card: hit ratio (the metric that matters) + used/max as context in finding
        signals.append(Signal("wt_cache_hit_ratio", cache_hit_pct, "%",
                               _THRESHOLDS["cache_hit_ratio_warning"] * 100))
        cache_note_str = f"  {cache_note}" if cache_note else ""
        findings.append(
            f"WiredTiger cache: {cache_hit_pct:.1f}% hit ratio{cache_note_str}"
            f"  ·  {cache_used_mb} / {cache_max_mb} MB used ({cache_util_pct}%)"
        )
        if cache_sev == HealthSeverity.CRITICAL:
            findings.append(
                f"  Cache hit ratio is critically low ({cache_hit_pct:.1f}%) — "
                f"data is being read from disk on most requests. Increase wiredTigerCacheSizeGB or reduce working set."
            )
        elif cache_sev == HealthSeverity.WARNING:
            findings.append(
                f"  Cache hit ratio ({cache_hit_pct:.1f}%) is below the {_THRESHOLDS['cache_hit_ratio_warning'] * 100:.0f}% "
                f"warning threshold — consider increasing WiredTiger cache."
            )

        # ── Global lock wait % ──────────────────────────────────────────────────
        locks = ss.get("locks", {}).get("Global", {})
        acquire_wait  = sum(locks.get("acquireWaitCount", {}).values())
        acquire_total = sum(locks.get("acquireCount",     {}).values())
        lock_wait_pct = round(acquire_wait / acquire_total * 100, 2) if acquire_total else 0.0

        # BL-021: baseline-aware lock wait severity
        lock_sev, lock_note = self._baseline.assess(
            "lock_wait_pct", lock_wait_pct,
            static_warn=_THRESHOLDS["lock_wait_pct_warning"],
            static_crit=_THRESHOLDS["lock_wait_pct_critical"],
        )
        severities.append(lock_sev)
        signals.append(Signal("lock_wait_pct", lock_wait_pct, "%",
                               _THRESHOLDS["lock_wait_pct_warning"]))
        lock_note_str = f"  {lock_note}" if lock_note else ""
        findings.append(f"Global lock wait: {lock_wait_pct:.2f}% of acquisitions waited{lock_note_str}")
        if lock_sev == HealthSeverity.CRITICAL:
            findings.append(
                f"  Lock contention is critically high ({lock_wait_pct:.1f}%) — "
                f"investigate long-running operations or high write concurrency."
            )
        elif lock_sev == HealthSeverity.WARNING:
            findings.append(
                f"  Lock wait percentage ({lock_wait_pct:.1f}%) exceeds warning threshold "
                f"({_THRESHOLDS['lock_wait_pct_warning']}%) — watch for concurrency issues."
            )

        # ── Cluster-level query targeting ratio ────────────────────────────────
        qe = ss.get("metrics", {}).get("queryExecutor", {})
        scanned     = int(qe.get("scanned",        0))
        scanned_obj = int(qe.get("scannedObjects",  0))
        scan_and_order = int(ss.get("metrics", {}).get("operation", {}).get("scanAndOrder", 0))

        total_scanned = scanned + scanned_obj
        if total_scanned > 0 and reads > 0:
            targeting_ratio = round(total_scanned / reads, 1)
        else:
            targeting_ratio = 0.0

        # Raw scanned key/object counts omitted as cards — the ratio is what matters
        # BL-021: baseline-aware targeting ratio severity
        target_sev, target_note = self._baseline.assess(
            "cluster_targeting_ratio", targeting_ratio,
            static_warn=_THRESHOLDS["query_targeting_warning"],
            static_crit=_THRESHOLDS["query_targeting_critical"],
        )
        severities.append(target_sev)
        signals.append(Signal("cluster_targeting_ratio", targeting_ratio, "docs scanned per read",
                               _THRESHOLDS["query_targeting_warning"]))
        target_note_str = f"  {target_note}" if target_note else ""
        findings.append(
            f"Index efficiency (cluster): {targeting_ratio:,.1f}× docs scanned per read{target_note_str}"
            + (f"  ·  {scan_and_order:,} in-memory sort(s)" if scan_and_order else "")
        )
        if target_sev == HealthSeverity.CRITICAL:
            findings.append(
                f"  Cluster targeting ratio is critically high ({targeting_ratio:,.0f}×) — "
                f"many queries are doing full collection scans. Review index coverage."
            )
        elif target_sev == HealthSeverity.WARNING:
            findings.append(
                f"  Cluster targeting ratio ({targeting_ratio:,.1f}×) exceeds warning threshold "
                f"({_THRESHOLDS['query_targeting_warning']}×) — check for missing or unused indexes."
            )

        return ReportSection(
            name="Operations",
            severity=worst_severity(severities),
            signals=signals,
            findings=findings,
        )

    # ── helpers ────────────────────────────────────────────────────────────────

    def _top_slow_collections(self, slow_queries: List[Dict], n: int = 3) -> List[Dict[str, str]]:
        """Return top-N collections by slow query count as [{"db": ..., "collection": ...}]."""
        counts: Dict[tuple, int] = {}
        for q in slow_queries:
            c = q["collection"]
            if c and not c.startswith("system."):
                key = (q.get("db", ""), c)
                counts[key] = counts.get(key, 0) + 1
        top = sorted(counts.items(), key=lambda x: -x[1])[:n]
        return [{"db": db, "collection": coll} for (db, coll), _ in top]

    # Fields that appear in the profiler command document but are NOT filter fields
    _SKIP_FIELDS = frozenset({
        "find", "filter", "limit", "sort", "skip", "projection",
        "aggregate", "pipeline", "cursor", "collation",
        "readConcern", "writeConcern", "lsid", "txnNumber", "$db",
        "allowDiskUse", "batchSize", "singleBatch", "returnKey",
        "showRecordId", "hint", "comment", "maxTimeMS",
    })

    @staticmethod
    def _extract_filter_fields(query_obj: Any) -> List[str]:
        """Return non-operator field names from a profiler command/query dict."""
        if not isinstance(query_obj, dict):
            return []
        # Profiler wraps find queries as {find:..., filter:{...}, ...}
        filter_obj = query_obj.get("filter", query_obj.get("query", query_obj))
        if not isinstance(filter_obj, dict):
            return []
        return [
            f for f in filter_obj
            if not f.startswith("$") and f not in HealthCheckRunner._SKIP_FIELDS
        ]

    def _build_recommendations(
        self,
        slow_queries: List[Dict[str, Any]],
        sections: List[ReportSection],
        unused_indexes: List[Dict[str, Any]],
    ) -> List[Recommendation]:
        recs: List[Recommendation] = []

        # ── HIGH: create missing indexes for slow full-scan collections ──────────
        # Group all slow queries by collection so we can pick the best representative
        # (prefer queries that have extractable filter fields — aggregate $indexStats
        #  calls appear as op=command with no filter and must be skipped)
        by_coll: Dict[str, List[Dict]] = {}
        for q in slow_queries:
            coll = q["collection"]
            if coll and not coll.startswith("system."):
                by_coll.setdefault(coll, []).append(q)

        for coll, qs in by_coll.items():
            # Pick the worst full-scan query (most docs examined) that has filter fields;
            # fall back to worst overall if none have extractable fields.
            full_scan_qs = [
                q for q in qs
                if (q.get("docs_examined", 0) >= _THRESHOLDS["full_scan_examined_min"]
                    and (q.get("docs_returned", 0) / q["docs_examined"]
                         if q.get("docs_examined") else 1.0)
                    <= _THRESHOLDS["full_scan_selectivity_max"])
            ]
            if not full_scan_qs:
                continue  # no full-scan evidence for this collection

            # Prefer a query with extractable filter fields
            best = None
            best_fields: List[str] = []
            for q in sorted(full_scan_qs, key=lambda x: -x.get("docs_examined", 0)):
                fields = self._extract_filter_fields(q.get("query", {}))
                if fields:
                    best        = q
                    best_fields = fields
                    break
            if best is None:
                best = max(full_scan_qs, key=lambda x: x.get("docs_examined", 0))

            examined    = best.get("docs_examined", 0)
            returned    = best.get("docs_returned", 0)
            ms          = best.get("execution_time_ms", 0)
            selectivity = returned / examined if examined else 1.0
            sort_fields = best.get("sort_fields", [])
            has_sort    = best.get("has_sort_stage", False)

            db_label = best.get("db", "")
            fq_coll  = f"{db_label}.{coll}" if db_label else coll

            # Build index spec: filter fields (ESR: equality first) then sort field
            if best_fields or sort_fields:
                # Include up to 2 filter fields then up to 1 sort field (ESR pattern)
                index_parts = {f: 1 for f in best_fields[:2]}
                if sort_fields:
                    sf = sort_fields[0]
                    if sf not in index_parts:
                        index_parts[sf] = 1  # direction preserved from sort if needed
                index_spec = ", ".join(f'"{k}": 1' for k in index_parts)
                action = f"db.{coll}.createIndex({{{index_spec}}})"
                if has_sort and sort_fields:
                    action += f"  // covers filter + eliminates in-memory sort on {sort_fields[0]}"
                confidence = "high" if best_fields else "medium"
            else:
                action     = (
                    f"db.{coll}.createIndex({{\"<field>\": 1}})  "
                    f"— inspect query patterns to identify filter fields"
                )
                confidence = "medium"

            sort_note = (
                f"; has_sort_stage=true (sort on {sort_fields[0]} done in memory)"
                if has_sort and sort_fields else
                f"; has_sort_stage=true" if has_sort else ""
            )
            recs.append(Recommendation(
                priority="high",
                collection=fq_coll,
                action=action,
                evidence=(
                    f"{examined:,} docs examined, {returned} returned ({ms}ms) — "
                    f"targeting ratio {examined / returned:.0f}× · COLLSCAN{sort_note}" if returned else f"targeting ratio ∞× (0 docs returned) · COLLSCAN{sort_note}"
                ),
                confidence=confidence,
            ))

        # ── MEDIUM: drop unused indexes (structured data from _section_index_usage) ──
        for idx in unused_indexes:
            db_name    = idx["db"]
            coll_name  = idx["collection"]
            index_name = idx["name"]
            since      = idx.get("since", "last restart") or "last restart"
            recs.append(Recommendation(
                priority="medium",
                collection=f"{db_name}.{coll_name}",
                action=f'db.{coll_name}.dropIndex("{index_name}")',
                evidence=(
                    f'Index "{index_name}" on {db_name}.{coll_name} has 0 accesses since {since} — '
                    f"consuming write overhead and storage with no read benefit"
                ),
                confidence="medium",
            ))

        return recs

    # ── persistence ────────────────────────────────────────────────────────────

    def _save_report(self, report: HealthCheckReport) -> Path:
        from utils.html_reporter import render_html
        from utils.markdown_reporter import render_markdown

        REPORTS_DIR.mkdir(exist_ok=True)
        stem = f"health_{report.timestamp.strftime('%Y-%m-%d_%H-%M-%S')}"

        json_path = REPORTS_DIR / f"{stem}.json"
        json_path.write_text(json.dumps(report.to_dict(), indent=2, default=str))
        logger.info("Health check report saved: %s", json_path)

        # Set report_path before rendering HTML/Markdown so the footer is correct
        report.report_path = str(json_path)

        html_path = REPORTS_DIR / f"{stem}.html"
        html_path.write_text(render_html(report), encoding="utf-8")
        logger.info("HTML report saved: %s", html_path)

        md_path = REPORTS_DIR / f"{stem}.md"
        md_path.write_text(render_markdown(report), encoding="utf-8")
        logger.info("Markdown report saved: %s", md_path)

        return json_path

    def _purge_old_reports(self, days: int = 90) -> None:
        cutoff = datetime.utcnow() - timedelta(days=days)
        for pattern in ("health_*.json", "health_*.html"):
            for f in REPORTS_DIR.glob(pattern):
                if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                    f.unlink()
                    logger.info("Purged old report: %s", f)
