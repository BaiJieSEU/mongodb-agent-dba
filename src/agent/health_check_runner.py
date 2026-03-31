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

# Severity thresholds — defaults only; live values loaded from agent_config.yaml (BL-021).
# Keep this dict in sync with ThresholdsConfig in config_loader.py.
_THRESHOLDS_DEFAULTS = {
    "slow_query_pct_warning": 5.0,
    "slow_query_pct_critical": 20.0,
    "slow_query_ms_warning": 100,
    "slow_query_ms_critical": 500,
    "disk_used_pct_warning": 80,
    "disk_used_pct_critical": 90,
    "oplog_window_warning_hours": 24,
    "oplog_window_critical_hours": 4,
    "full_scan_examined_min": 1000,
    "full_scan_selectivity_max": 0.01,
    "cache_hit_ratio_warning": 0.95,
    "cache_hit_ratio_critical": 0.80,
    "lock_wait_pct_warning": 5.0,
    "lock_wait_pct_critical": 20.0,
    "query_targeting_warning": 10.0,
    "query_targeting_critical": 100.0,
    "replication_lag_warning_sec": 10,
    "replication_lag_critical_sec": 60,
    "long_running_op_warning_sec": 5,
    "long_running_op_critical_sec": 60,
    "plan_cache_hit_rate_warning": 80.0,
    "plan_cache_hit_rate_critical": 50.0,
    "backup_interval_hours": 24.0,
    "memory_resident_warning_mb": 4096,
    "memory_resident_critical_mb": 8192,
    "connections_warning": 500,
    "tickets_warning": 10,
    "lock_queue_warning": 10,
    "cpu_user_pct_warning": 80.0,
    "cpu_iowait_pct_warning": 10.0,
    "disk_write_latency_warning_ms": 10.0,
    "system_memory_used_pct_warning": 90.0,
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
        # BL-021: thresholds from agent_config.yaml, falling back to hard-coded defaults
        self._thresholds: Dict[str, Any] = {
            **_THRESHOLDS_DEFAULTS,
            **config.thresholds.model_dump(),
        }

    # ── public entry point ─────────────────────────────────────────────────────

    def run(self) -> HealthCheckReport:
        _run_start = time.time()
        run_id = f"hc_{int(_run_start)}"
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

        # OM client — optional; None if keys not configured or OM unreachable
        self._om = None
        om_cfg = self.config.ops_manager
        if om_cfg.url and om_cfg.group_id and om_cfg.public_key and om_cfg.private_key:
            from utils.om_client import OMClient
            self._om = OMClient(
                om_cfg.url, om_cfg.group_id, om_cfg.public_key, om_cfg.private_key
            )

        # Shared state written by one section and read by another
        self._oplog_window_hours: Optional[float] = None  # set by §3, read by §Backup
        self._low_cardinality_fields: Dict[str, Any] = {}  # set by BL-101, read by _build_recommendations

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
                # BL-101: cardinality pre-compute (inside MCP block — uses self._mcp.aggregate)
                self._precompute_cardinality(slow_queries)

                self._mcp = None

            # §8 Operations — direct PyMongo serverStatus (BL-009)
            sections.append(self._section_operations())
            # §9 Backup & Recovery (BL-106/107)
            sections.append(self._section_backup_recovery())
            # §10 Connections & Concurrency — OM API (BL-013)
            sections.append(self._section_connections())
            # §11 Infrastructure — OM API (BL-015)
            sections.append(self._section_infrastructure())
        finally:
            self._mongo.close_connections()
            self._mongo = None

        recommendations = self._build_recommendations(slow_queries, sections, unused_indexes)
        overall = worst_severity([s.severity for s in sections])

        # BL-087: agent version + optional OM version in report header
        from main_agentic import __version__ as _agent_version
        _om_version = self._om.get_version() if self._om else ""

        report = HealthCheckReport(
            run_id=run_id,
            timestamp=timestamp,
            cluster_uri=self._cluster_uri,
            cluster_name=self._cluster_name,
            overall_severity=overall,
            sections=sections,
            recommendations=recommendations,
            agent_version=_agent_version,
            om_version=_om_version or "",
        )

        # BL-084 + health summary: LLM enrichment — signal tooltips + natural language summary
        # (BL-034 recommendation enrichment removed: rule-based recommendations are sufficient)
        if self.config.agent.llm_recommendations:
            from agent.llm_recommender import LLMRecommender
            llm_rec = LLMRecommender(self.config)
            logger.info("BL-084: running LLM signal tooltip enrichment")
            llm_rec.enrich_signal_tooltips(report)
            logger.info("Generating LLM health summary")
            report.health_summary = llm_rec.generate_health_summary(report)

        # BL-114: attach trend arrows to tracked signals (after baseline load, before save)
        self._attach_trends(report)

        # BL-021: persist this run's metrics for future baseline comparisons
        # BL-122: also persist health score for sparkline history
        from utils.html_reporter import _health_score
        current_score = _health_score(report)
        self._baseline.record_from_report(report, score=current_score)
        # Attach score history to report so fleet renderer can draw sparkline
        report.score_history = self._baseline.score_history()
        # Wall-clock run time
        report.elapsed_seconds = round(time.time() - _run_start, 1)

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

        findings = []
        for db, colls in collections_by_db.items():
            coll_list = ", ".join(colls) if colls else "(empty)"
            findings.append(f"{db}: {coll_list}")

        return ReportSection(
            name="Cluster Overview",
            severity=HealthSeverity.OK,
            signals=[
                Signal("database_count", len(user_dbs)),
                Signal("collection_count", total_colls),
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
            static_warn=self._thresholds["disk_used_pct_warning"],
            static_crit=self._thresholds["disk_used_pct_critical"],
        )

        findings = [
            f"Host: {hostname}",
            f"Disk figures are from MongoDB's filesystem view (fsUsedSize) — may differ"
            " from OS tools on macOS/APFS. Reliable on Linux production servers.",
        ]
        if self._baseline.is_cold_start:
            findings.append(f"Baseline: {self._baseline.cold_start_note()}")
        if severity != HealthSeverity.OK:
            label = ("CRITICAL: risk of mongod write failures."
                     if severity == HealthSeverity.CRITICAL else "WARNING: monitor closely.")
            note_str = f"  {disk_note}" if disk_note else ""
            findings.append(f"Disk at {disk_used_pct}% of {disk_total_gb} GB — {label}{note_str}")

        return ReportSection(
            name="Server Health",
            severity=severity,
            signals=[
                Signal("mongodb_version", version),
                Signal("uptime_hours", uptime_hours, "hours"),
                Signal("filesystem_disk_used_gb", disk_used_gb, "GB"),
                Signal("filesystem_disk_used_pct", disk_used_pct, "%", self._thresholds["disk_used_pct_warning"]),
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
                static_warn=self._thresholds["oplog_window_warning_hours"],
                static_crit=self._thresholds["oplog_window_critical_hours"],
                higher_is_worse=False,
            )

        # BL-094: replSetGetStatus — per-member health, state, and replication lag
        # Available via direct PyMongo (clusterMonitor role); not available via MCP.
        rs_status = self._mongo.get_rs_status() if self._mongo else None
        rs_status_members: List[Dict] = rs_status.get("members", []) if rs_status else []

        members_up   = sum(1 for m in rs_status_members if int(m.get("health", 0)) == 1)
        members_down = sum(1 for m in rs_status_members if int(m.get("health", 0)) == 0)

        # Compute per-secondary lag (primary optimeDate – secondary optimeDate)
        primary_optime = None
        for m in rs_status_members:
            if m.get("stateStr") == "PRIMARY":
                primary_optime = m.get("optimeDate")
                break

        lag_per_member: List[tuple] = []  # (name, lag_sec)
        for m in rs_status_members:
            if m.get("stateStr") not in ("PRIMARY", "ARBITER") and int(m.get("health", 0)) == 1:
                member_optime = m.get("optimeDate")
                if primary_optime and member_optime:
                    lag_sec = max(0.0, (primary_optime - member_optime).total_seconds())
                    lag_per_member.append((m.get("name", "?"), lag_sec))

        max_lag_sec = max((lag for _, lag in lag_per_member), default=0.0)

        # Severity: merge lag + oplog severity
        lag_sev = HealthSeverity.OK
        if max_lag_sec >= self._thresholds["replication_lag_critical_sec"]:
            lag_sev = HealthSeverity.CRITICAL
        elif max_lag_sec >= self._thresholds["replication_lag_warning_sec"]:
            lag_sev = HealthSeverity.WARNING
        if members_down > 0:
            lag_sev = worst_severity([lag_sev, HealthSeverity.WARNING])
        severity = worst_severity([severity, lag_sev])

        # Enrich with OM member states (still used for typeName if OM configured)
        om_host_map: Dict[str, Dict] = {}
        if self._om is not None:
            try:
                for h in self._om.get_hosts():
                    hn = h.get("hostname", "")
                    if hn:
                        om_host_map[hn] = h
            except Exception as exc:
                logger.warning("OM replication enrichment failed: %s", exc)

        findings: List[str] = []
        if is_replica_set:
            findings.append(f"Replica set: {rs_name}  ·  {len(members)} configured member(s)")
            if rs_status_members:
                for m in rs_status_members:
                    name  = m.get("name", "?")
                    state = m.get("stateStr", "UNKNOWN")
                    health_flag = "✓" if int(m.get("health", 0)) == 1 else "✗ DOWN"
                    lag_entry = next((lag for n, lag in lag_per_member if n == name), None)
                    lag_str = f"  lag {lag_entry:.1f}s" if lag_entry is not None else ""
                    findings.append(f"  {name}  [{state}]  {health_flag}{lag_str}")
            else:
                for m in members:
                    host = m.get("host", "?")
                    pri  = m.get("priority", "?")
                    hidden = "  [hidden]" if m.get("hidden") else ""
                    hn_only = host.split(":")[0]
                    om_host = om_host_map.get(hn_only, {})
                    type_name = om_host.get("typeName", "")
                    state_str = f"  [{type_name}]" if type_name else ""
                    findings.append(f"  {host}  priority={pri}{hidden}{state_str}")
                findings.append(
                    "Member states not available — set OM_API_PUBLIC_KEY / OM_API_PRIVATE_KEY "
                    "or grant clusterMonitor role to see PRIMARY/SECONDARY/DOWN per member."
                )

            if members_down > 0:
                findings.append(
                    f"  {members_down} member(s) reported as DOWN — cluster may be degraded."
                )
            if lag_per_member:
                lag_fmt = self._fmt_duration(max_lag_sec)
                warn_fmt = self._fmt_duration(self._thresholds["replication_lag_warning_sec"])
                crit_fmt = self._fmt_duration(self._thresholds["replication_lag_critical_sec"])
                if max_lag_sec >= self._thresholds["replication_lag_critical_sec"]:
                    findings.append(
                        f"  Max replication lag ({lag_fmt}) exceeds critical threshold "
                        f"({crit_fmt}) — secondary(ies) at risk of oplog gap."
                    )
                elif max_lag_sec >= self._thresholds["replication_lag_warning_sec"]:
                    findings.append(
                        f"  Replication lag ({lag_fmt}) exceeds warning threshold ({warn_fmt})."
                    )

        if oplog_window_hours is not None:
            note_str = f"  {_oplog_note}" if _oplog_note else ""
            findings.append(f"Oplog window: {oplog_window_hours}h{note_str}")
            if severity != HealthSeverity.OK:
                findings.append(
                    f"Oplog window ({oplog_window_hours}h) is below the "
                    f"{self._thresholds['oplog_window_warning_hours']}h minimum — "
                    f"risk of replication failure after extended secondary downtime."
                )

        signals: List[Signal] = [Signal("replica_set_members", len(members))]
        if oplog_window_hours is not None:
            signals.append(Signal("oplog_window_hours", oplog_window_hours, "hours",
                                  self._thresholds["oplog_window_warning_hours"]))
        if rs_status_members:
            signals.append(Signal("members_up",   members_up))
            signals.append(Signal("members_down", members_down, "", 0))
        if lag_per_member:
            # BL-115: display as human-readable duration (value stays in seconds for threshold comparison)
            lag_display = self._fmt_duration(max_lag_sec)
            signals.append(Signal("replication_lag_max_sec", lag_display,
                                  "",   # unit embedded in display value
                                  self._thresholds["replication_lag_warning_sec"]))

        # BL-107: store for Backup & Recovery section
        self._oplog_window_hours = oplog_window_hours

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

        # BL-095: index-to-data ratio
        index_to_data_ratio = round(total_index_mb / total_data_mb, 2) if total_data_mb > 0 else 0.0

        # Severity based on MongoDB data size, not filesystem (filesystem is in Server Health)
        severity = HealthSeverity.OK
        if index_to_data_ratio > 2.0 and total_data_mb > 1.0:
            severity = HealthSeverity.WARNING

        # Only surface storage findings when there is an anomaly worth investigating.
        # Raw size rankings with no threshold context add noise, not signal.
        findings: List[str] = []
        if total_data_mb > 0:
            for s in coll_stats:
                share = s["size_mb"] / total_data_mb
                if share > 0.7 and len(coll_stats) > 1:
                    findings.append(
                        f"{s['db']}.{s['collection']} holds {share*100:.0f}% of total data "
                        f"({s['size_mb']:.1f} MB of {total_data_mb:.1f} MB) — "
                        f"verify this is expected."
                    )
                if s["avg_bytes"] > 50_000:
                    findings.append(
                        f"{s['db']}.{s['collection']}: avg document size {s['avg_bytes']:,} bytes — "
                        f"consider schema review or projection to reduce working-set pressure."
                    )
        if index_to_data_ratio > 2.0 and total_data_mb > 1.0:
            findings.append(
                f"Index size ({round(total_index_mb, 1)} MB) is {index_to_data_ratio}× data size "
                f"({round(total_data_mb, 1)} MB) — review unused indexes (§7 Unused Indexes)."
            )

        return ReportSection(
            name="Storage & Capacity",
            severity=severity,
            signals=[
                Signal("mongodb_data_mb",       round(total_data_mb, 1),    "MB"),
                Signal("mongodb_index_mb",      round(total_index_mb, 1),   "MB"),
                Signal("index_to_data_ratio",   index_to_data_ratio,        "×", 2.0),
            ],
            findings=findings,
        )

    # ── Section 5: Query Performance ───────────────────────────────────────────

    def _section_query_performance(self, user_dbs: List[str]) -> Tuple[ReportSection, List[Dict[str, Any]]]:
        threshold = self.config.agent.slow_query_threshold_ms
        limit     = self.config.agent.max_queries_to_analyze

        # BL-006: check profiler configuration for each user database
        # BL-100: also capture slowms values for explicit signal
        profiler_off_dbs:      List[str] = []
        profiler_high_ms_dbs:  List[str] = []
        profiler_slowms_values: List[int] = []
        for db in user_dbs:
            try:
                status = self._mongo.monitored_cluster[db].command({"profile": -1})
                level  = status.get("was", status.get("level", -1))
                slowms = int(status.get("slowms", 0))
                if level == 0:
                    profiler_off_dbs.append(db)
                elif slowms > 100:
                    profiler_high_ms_dbs.append(db)
                if level != 0:
                    profiler_slowms_values.append(slowms)
            except Exception as exc:
                logger.warning("BL-006: profiler status unavailable for %s: %s", db, exc)

        slow_queries: List[Dict[str, Any]] = []
        total_profiled = 0   # all queries captured by the profiler (denominator for %)
        for db in user_dbs:
            # Count every profiler entry (excludes cursor/admin noise — same filter as slow)
            _prof_filter = {"op": {"$nin": ["getmore", "killCursors"]}}
            total_profiled += self._mcp.count(db, "system.profile", filter=_prof_filter)
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

        # BL-102: aggregation pipeline anti-patterns from profiler entries
        slow_agg_count = 0
        agg_antipatterns: List[str] = []
        for q in slow_queries:
            cmd = q.get("query", {})
            if isinstance(cmd, dict) and "aggregate" in cmd:
                slow_agg_count += 1
                pipeline = cmd.get("pipeline", [])
                for issue in self._detect_pipeline_antipatterns(pipeline):
                    ns_str = f"{q.get('db', '')}.{q.get('collection', '')}: {issue}"
                    if ns_str not in agg_antipatterns:
                        agg_antipatterns.append(ns_str)

        # Percentage of profiled queries that were slow (same window — both from system.profile)
        slow_pct = round(count / total_profiled * 100, 1) if total_profiled > 0 else 0.0

        # Scan & sort aggregate metrics
        collscan_count    = sum(1 for q in slow_queries if "COLLSCAN" in q["plan_summary"])
        sort_stage_count  = sum(1 for q in slow_queries if q["has_sort_stage"])
        sort_spill_count  = sum(1 for q in slow_queries if q["sort_spills"] > 0)
        total_spill_bytes = sum(q["sort_spill_bytes"] for q in slow_queries)

        # BL-021/BL-093: severity based on % of profiled queries that are slow
        if total_profiled == 0 or count == 0:
            severity = HealthSeverity.OK
            _pct_note = ""
            _ms_note = ""
        else:
            pct_sev, _pct_note = self._baseline.assess(
                "slow_query_pct", slow_pct,
                static_warn=self._thresholds["slow_query_pct_warning"],
                static_crit=self._thresholds["slow_query_pct_critical"],
            )
            ms_sev, _ms_note = self._baseline.assess(
                "max_execution_ms", float(max_ms),
                static_warn=self._thresholds["slow_query_ms_warning"],
                static_crit=self._thresholds["slow_query_ms_critical"],
            )
            severity = worst_severity([pct_sev, ms_sev])
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
            # ── BL-085: clean summary headline ──────────────────────────────
            collscan_str = f" — {collscan_count} COLLSCAN" if collscan_count else ""
            spill_str    = (
                f" — {sort_spill_count} sort spill(s) to disk ({total_spill_bytes // 1024} KB)"
                if sort_spill_count else ""
            )
            findings.append(
                f"{count} slow queries ({slow_pct}% of {total_profiled} profiled)"
                f"{collscan_str}{spill_str}"
                f"  ·  threshold: {threshold} ms  ·  max: {max_ms} ms  ·  avg: {avg_ms:.0f} ms"
            )
            if collscan_count:
                findings.append(
                    f"{collscan_count} of {count} operation(s) scanned the entire collection "
                    f"(COLLSCAN) — each is a candidate for an index."
                )
            if sort_spill_count:
                findings.append(
                    f"Sort spills detected — {sort_spill_count} query/queries exceeded the "
                    f"100 MB in-memory sort limit. Add indexes covering the sort field to eliminate spills."
                )
            # ── BL-085: per-collection detail block (collapsible via BL-083) ──
            # Suppress collections where docs_examined == 0 AND plan unknown (profiler noise)
            for coll, qs in sorted(by_coll.items(), key=lambda x: -max(q["execution_time_ms"] for q in x[1])):
                c_max    = max(q["execution_time_ms"] for q in qs)
                c_avg    = sum(q["execution_time_ms"] for q in qs) / len(qs)
                c_exam   = max(q["docs_examined"]   for q in qs)
                c_ret    = max((q["docs_returned"]   for q in qs), default=0)
                c_keys   = max(q["keys_examined"]   for q in qs)
                c_plans  = {q["plan_summary"] for q in qs if q["plan_summary"]}
                c_sorts  = sum(1 for q in qs if q["has_sort_stage"])
                plan_str = " / ".join(sorted(c_plans)) if c_plans else "unknown"
                # BL-085: skip zero-examination unknown-plan entries (profiler internal ops)
                if c_exam == 0 and plan_str == "unknown":
                    continue
                targeting = round(c_exam / c_ret, 1) if c_ret else float("inf")
                targeting_str = f"{targeting:,.0f}×" if targeting != float("inf") else "∞"
                sort_note = f"  sort: {c_sorts}/{len(qs)}" if c_sorts else ""
                # Use double-space prefix so BL-083 puts these into the <details> block
                findings.append(
                    f"  {coll}  [{len(qs)} slow op(s)  max {c_max} ms  avg {c_avg:.0f} ms]"
                )
                findings.append(
                    f"  plan: {plan_str}  ·  docs examined: {c_exam:,}  ·  "
                    f"keys examined: {c_keys:,}  ·  targeting: {targeting_str}{sort_note}"
                )

        # BL-006: profiler findings
        if profiler_off_dbs:
            severity = worst_severity([severity, HealthSeverity.WARNING])
            findings.append(
                f"  Profiler disabled (level 0) on: {', '.join(profiler_off_dbs)} — "
                f"slow query data may be incomplete or missing."
            )
        if profiler_high_ms_dbs:
            severity = worst_severity([severity, HealthSeverity.WARNING])
            findings.append(
                f"  Profiler slowms > 100ms on: {', '.join(profiler_high_ms_dbs)} — "
                f"fast queries not captured; lower slowms to ≤ 100 for better coverage."
            )

        # BL-102: surface aggregation anti-patterns in findings
        if agg_antipatterns:
            severity = worst_severity([severity, HealthSeverity.WARNING])
            findings.append(
                f"  {len(agg_antipatterns)} aggregation pipeline anti-pattern(s) detected:"
            )
            for issue in agg_antipatterns[:5]:
                findings.append(f"    {issue}")
            if len(agg_antipatterns) > 5:
                findings.append(f"    … and {len(agg_antipatterns) - 5} more.")

        # BL-100: profiler slowms as explicit signal
        max_slowms = max(profiler_slowms_values, default=0)

        signals = [
            Signal("slow_query_pct",     slow_pct,         "%",       self._thresholds["slow_query_pct_warning"]),
            Signal("slow_query_count",   count),
            Signal("total_profiled",     total_profiled),
            Signal("collscan_count",      collscan_count,   "", 0),
            Signal("sort_stage_count",    sort_stage_count, "", 0),
            Signal("sort_spill_count",    sort_spill_count, "", 0),
            Signal("max_execution_ms",    max_ms,           "ms",      self._thresholds["slow_query_ms_warning"]),
            Signal("avg_execution_ms",    round(avg_ms, 1), "ms"),
        ]
        if max_slowms > 0:
            signals.append(Signal("profiler_slowms", max_slowms, "ms", 100))
        if slow_agg_count > 0:
            signals.append(Signal("slow_aggregation_count", slow_agg_count, "", 0))
        if profiler_off_dbs:
            signals.append(Signal("profiler_disabled_dbs", len(profiler_off_dbs), "", 0))
        if profiler_high_ms_dbs:
            signals.append(Signal("profiler_high_slowms_dbs", len(profiler_high_ms_dbs), "", 0))

        return ReportSection(
            name="Query Performance",
            severity=severity,
            signals=signals,
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
                Signal("collections_checked",       len(collections)),
                Signal("under_indexed_collections", len(under_indexed),  "", 0),
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

        # BL-007: detect redundant indexes (left-prefix redundancies)
        # BL-096: detect exact duplicate indexes (identical key spec including directions)
        # Group by db+collection, then compare key patterns within each group.
        redundant: List[Dict[str, Any]] = []
        exact_dupes: List[Dict[str, Any]] = []
        from collections import defaultdict
        by_coll: Dict[str, List[Dict]] = defaultdict(list)
        for idx in all_indexes:
            if not idx["is_id"] and isinstance(idx.get("key"), dict):
                by_coll[f"{idx['db']}.{idx['collection']}"].append(idx)

        for fq_coll, idxs in by_coll.items():
            # BL-096: exact duplicates — same key fields AND directions
            seen_key_specs: Dict[str, str] = {}  # canonical key str → first index name
            for idx in idxs:
                key_canon = str(list(idx["key"].items()))
                if key_canon in seen_key_specs:
                    if not any(d["name"] == idx["name"] and d["fq_coll"] == fq_coll
                               for d in exact_dupes):
                        exact_dupes.append({
                            **idx,
                            "duplicate_of": seen_key_specs[key_canon],
                            "fq_coll": fq_coll,
                        })
                else:
                    seen_key_specs[key_canon] = idx["name"]

            # BL-007: left-prefix redundancies (key names only — direction-agnostic)
            key_lists = [list(idx["key"].keys()) for idx in idxs]
            for i, idx_a in enumerate(idxs):
                # Skip if already flagged as an exact duplicate
                if any(d["name"] == idx_a["name"] and d["fq_coll"] == fq_coll
                       for d in exact_dupes):
                    continue
                keys_a = key_lists[i]
                for j, idx_b in enumerate(idxs):
                    if i == j:
                        continue
                    keys_b = key_lists[j]
                    # idx_a is a left-prefix of idx_b → idx_a is redundant
                    if 0 < len(keys_a) < len(keys_b) and keys_b[:len(keys_a)] == keys_a:
                        if not any(r["name"] == idx_a["name"] and r["collection"] == idx_a["collection"]
                                   for r in redundant):
                            redundant.append({
                                **idx_a,
                                "covered_by": idx_b["name"],
                                "fq_coll": fq_coll,
                            })
                        break

        if exact_dupes:
            severity = HealthSeverity.CRITICAL
        elif unused or redundant:
            severity = HealthSeverity.WARNING
        else:
            severity = HealthSeverity.OK

        findings: List[str] = []

        # BL-096: exact duplicate findings (highest priority — always safe to drop)
        if exact_dupes:
            findings.append(
                f"{len(exact_dupes)} exact duplicate index(es) detected — identical key spec "
                f"as an existing index, consuming RAM and slowing writes with zero benefit."
            )
            for idx in exact_dupes[:10]:
                key_str = ", ".join(f"{k}: {v}" for k, v in idx["key"].items())
                findings.append(
                    f'  {idx["fq_coll"]} → "{idx["name"]}" {{{key_str}}} '
                    f'is an exact duplicate of "{idx["duplicate_of"]}"'
                )
            if len(exact_dupes) > 10:
                findings.append(f"  … and {len(exact_dupes) - 10} more exact duplicate(s).")

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
        elif not exact_dupes:
            findings.append(
                f"All {len(custom)} custom index(es) across "
                f"{len({i['collection'] for i in all_indexes})} collection(s) are actively used."
            )

        # BL-007: redundant index findings
        if redundant:
            findings.append(
                f"{len(redundant)} redundant index(es) detected — each is a left-prefix of "
                f"an existing compound index and can be safely dropped."
            )
            for idx in redundant[:10]:
                key_str = ", ".join(f"{k}: {v}" for k, v in idx["key"].items())
                findings.append(
                    f'  {idx["fq_coll"]} → "{idx["name"]}" {{{key_str}}} is covered by "{idx["covered_by"]}"'
                )
            if len(redundant) > 10:
                findings.append(f"  … and {len(redundant) - 10} more redundant index(es).")

        if used:
            top = sorted(used, key=lambda x: -x["ops"])[:3]
            findings.append(
                "Most-used: " + ", ".join(
                    f'{i["collection"]}.{i["name"]} ({i["ops"]:,} ops)' for i in top
                )
            )

        signals = [
            Signal("total_indexes",       len(all_indexes)),
            Signal("exact_duplicates",    len(exact_dupes),  "", 0),
            Signal("unused_indexes",      len(unused),       "", 0),
            Signal("redundant_indexes",   len(redundant),    "", 0),
            Signal("used_indexes",        len(used)),
        ]

        return ReportSection(
            name="Unused Indexes",
            severity=severity,
            signals=signals,
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
        signals.append(Signal("memory_resident_mb", rss_mb, "MB", self._thresholds["memory_resident_warning_mb"]))
        if rss_mb >= self._thresholds["memory_resident_critical_mb"]:
            severities.append(HealthSeverity.CRITICAL)
            findings.append(
                f"  Resident memory ({rss_mb:,} MB) exceeds critical threshold "
                f"({self._thresholds['memory_resident_critical_mb']:,} MB) — review WiredTiger cache size and working set."
            )
        elif rss_mb >= self._thresholds["memory_resident_warning_mb"]:
            severities.append(HealthSeverity.WARNING)
            findings.append(
                f"  Resident memory ({rss_mb:,} MB) is elevated — monitor for growth."
            )

        # ── Page faults (BL-098) ────────────────────────────────────────────────
        # Cumulative since restart — any healthy server will have some.
        # Baseline-aware: flag if current run is significantly above cluster norm.
        extra = ss.get("extra_info", {})
        page_faults = int(extra.get("page_faults", 0))
        if page_faults > 0:
            signals.append(Signal("page_faults", page_faults, "faults (cumulative)"))
            pf_sev, pf_note = self._baseline.assess(
                "page_faults", float(page_faults),
                higher_is_worse=True,
            )
            if pf_sev != HealthSeverity.OK:
                severities.append(pf_sev)
                findings.append(
                    f"  Page faults ({page_faults:,}) are elevated vs cluster baseline "
                    f"({pf_note}) — working set may not fit in RAM."
                )

        # ── Network throughput (BL-099) ─────────────────────────────────────────
        network = ss.get("network", {})
        bytes_in  = int(network.get("bytesIn",  0))
        bytes_out = int(network.get("bytesOut", 0))
        net_in_mb  = round(bytes_in  / 1_048_576, 1)
        net_out_mb = round(bytes_out / 1_048_576, 1)
        if net_in_mb > 0 or net_out_mb > 0:
            signals.append(Signal("network_bytes_in_mb",  net_in_mb,  "MB (cumulative)"))
            signals.append(Signal("network_bytes_out_mb", net_out_mb, "MB (cumulative)"))
            findings.append(
                f"Network since restart: {net_in_mb:,.0f} MB in  {net_out_mb:,.0f} MB out"
            )

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
            static_warn=self._thresholds["cache_hit_ratio_warning"] * 100,
            static_crit=self._thresholds["cache_hit_ratio_critical"] * 100,
            higher_is_worse=False,
        )
        severities.append(cache_sev)
        # Single card: hit ratio (the metric that matters) + used/max as context in finding
        signals.append(Signal("wt_cache_hit_ratio", cache_hit_pct, "%",
                               self._thresholds["cache_hit_ratio_warning"] * 100))
        cache_note_str = f"  {cache_note}" if cache_note else ""
        if cache_sev == HealthSeverity.CRITICAL:
            findings.append(
                f"  Cache hit ratio is critically low ({cache_hit_pct:.1f}%) — "
                f"data is being read from disk on most requests. Increase wiredTigerCacheSizeGB or reduce working set."
            )
        elif cache_sev == HealthSeverity.WARNING:
            findings.append(
                f"  Cache hit ratio ({cache_hit_pct:.1f}%) is below the {self._thresholds['cache_hit_ratio_warning'] * 100:.0f}% "
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
            static_warn=self._thresholds["lock_wait_pct_warning"],
            static_crit=self._thresholds["lock_wait_pct_critical"],
        )
        severities.append(lock_sev)
        signals.append(Signal("lock_wait_pct", lock_wait_pct, "%",
                               self._thresholds["lock_wait_pct_warning"]))
        if lock_sev == HealthSeverity.CRITICAL:
            findings.append(
                f"  Lock contention is critically high ({lock_wait_pct:.1f}%) — "
                f"investigate long-running operations or high write concurrency."
            )
        elif lock_sev == HealthSeverity.WARNING:
            findings.append(
                f"  Lock wait percentage ({lock_wait_pct:.1f}%) exceeds warning threshold "
                f"({self._thresholds['lock_wait_pct_warning']}%) — watch for concurrency issues."
            )

        # ── BL-103: Plan cache hit rate ─────────────────────────────────────────
        # MongoDB 8.0+: metrics.query.planCache.classic.{hits,misses}
        # MongoDB 7.0:  metrics.queryPlanner.{planCacheHits,planCacheMisses}
        _qp_new  = ss.get("metrics", {}).get("query", {}).get("planCache", {})
        _classic = _qp_new.get("classic", {})
        _qp_old  = ss.get("metrics", {}).get("queryPlanner", {})
        pc_hits   = int(_classic.get("hits",   0) or _qp_old.get("planCacheHits",   0))
        pc_misses = int(_classic.get("misses", 0) or _qp_old.get("planCacheMisses", 0))
        if pc_hits + pc_misses > 0:
            plan_cache_hit_rate = round(pc_hits / (pc_hits + pc_misses) * 100, 1)
            signals.append(Signal("plan_cache_hit_rate_pct", plan_cache_hit_rate, "%",
                                   self._thresholds["plan_cache_hit_rate_warning"]))
            if plan_cache_hit_rate < self._thresholds["plan_cache_hit_rate_critical"]:
                severities.append(HealthSeverity.CRITICAL)
                findings.append(
                    f"  Plan cache hit rate critically low ({plan_cache_hit_rate:.1f}%) — "
                    f"queries are re-planning on most executions. Review query shape stability and index changes."
                )
            elif plan_cache_hit_rate < self._thresholds["plan_cache_hit_rate_warning"]:
                severities.append(HealthSeverity.WARNING)
                findings.append(
                    f"  Plan cache hit rate ({plan_cache_hit_rate:.1f}%) is below the "
                    f"{self._thresholds['plan_cache_hit_rate_warning']}% warning threshold — "
                    f"query re-planning is elevated; check for schema or index churn."
                )

        # ── BL-097: Active long-running operations ──────────────────────────────
        long_ops = self._mongo.get_current_op(
            running_longer_than_secs=self._thresholds["long_running_op_warning_sec"]
        )
        long_ops_count = len(long_ops)
        longest_op_sec = max((int(op.get("secs_running", 0)) for op in long_ops), default=0)
        signals.append(Signal("long_running_ops_count", long_ops_count, "operations", 0))
        if long_ops_count > 0:
            signals.append(Signal("longest_op_sec", longest_op_sec, "s",
                                  self._thresholds["long_running_op_critical_sec"]))
            if longest_op_sec >= self._thresholds["long_running_op_critical_sec"]:
                severities.append(HealthSeverity.CRITICAL)
            else:
                severities.append(HealthSeverity.WARNING)
            top_ops = sorted(long_ops, key=lambda x: -int(x.get("secs_running", 0)))[:3]
            findings.append(
                f"  {long_ops_count} operation(s) running ≥ "
                f"{self._thresholds['long_running_op_warning_sec']}s "
                f"(longest: {longest_op_sec}s):"
            )
            for op in top_ops:
                ns      = op.get("ns", op.get("command", {}).get("$db", "unknown"))
                secs    = int(op.get("secs_running", 0))
                op_type = op.get("op", "?")
                waiting = "  [waiting for lock]" if op.get("waitingForLock") else ""
                findings.append(f"    {op_type} on {ns}  {secs}s{waiting}")

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
            static_warn=self._thresholds["query_targeting_warning"],
            static_crit=self._thresholds["query_targeting_critical"],
        )
        severities.append(target_sev)
        signals.append(Signal("cluster_targeting_ratio", targeting_ratio, "docs scanned per read",
                               self._thresholds["query_targeting_warning"]))
        target_note_str = f"  {target_note}" if target_note else ""
        if scan_and_order:
            findings.append(f"{scan_and_order:,} in-memory sort operation(s) since restart")
        if target_note_str:
            findings.append(target_note_str.strip())
        if target_sev == HealthSeverity.CRITICAL:
            findings.append(
                f"  Cluster targeting ratio is critically high ({targeting_ratio:,.0f}×) — "
                f"many queries are doing full collection scans. Review index coverage."
            )
        elif target_sev == HealthSeverity.WARNING:
            findings.append(
                f"  Cluster targeting ratio ({targeting_ratio:,.1f}×) exceeds warning threshold "
                f"({self._thresholds['query_targeting_warning']}×) — check for missing or unused indexes."
            )

        return ReportSection(
            name="Operations",
            severity=worst_severity(severities),
            signals=signals,
            findings=findings,
        )

    # ── Section 9: Backup & Recovery (BL-106/107) ──────────────────────────────

    def _section_backup_recovery(self) -> ReportSection:
        """BL-106: detect active backup cursor; BL-107: assess PITR coverage via oplog window."""
        if self._mongo is None:
            return ReportSection(
                name="Backup & Recovery",
                severity=HealthSeverity.WARNING,
                signals=[],
                findings=["serverStatus unavailable — backup status check skipped."],
            )

        ss = self._mongo.get_server_status()
        if ss is None:
            return ReportSection(
                name="Backup & Recovery",
                severity=HealthSeverity.WARNING,
                signals=[],
                findings=["serverStatus command unavailable — backup status check skipped."],
            )

        severities: List[HealthSeverity] = [HealthSeverity.OK]
        findings:   List[str]            = []
        signals:    List[Signal]         = []

        # BL-106: backupCursorOpen — True when a backup agent or manual backup is active
        storage_engine   = ss.get("storageEngine", {})
        backup_cursor_open = bool(storage_engine.get("backupCursorOpen", False))
        signals.append(Signal("backup_cursor_open", int(backup_cursor_open), ""))
        if backup_cursor_open:
            findings.append(
                "Active backup cursor detected — a backup process is connected and running."
            )
        else:
            severities.append(HealthSeverity.WARNING)
            findings.append(
                "No active backup cursor (backupCursorOpen=false) — verify that scheduled backups "
                "are configured (e.g. mongodump cron job, filesystem snapshots, or a third-party tool)."
            )

        # BL-107: PITR readiness — oplog window must cover the backup interval
        oplog_hours      = getattr(self, "_oplog_window_hours", None)
        backup_interval  = self._thresholds["backup_interval_hours"]
        if oplog_hours is not None:
            signals.append(Signal("oplog_window_for_pitr", oplog_hours, "hours", backup_interval))
            if oplog_hours < backup_interval:
                severities.append(HealthSeverity.WARNING)
                findings.append(
                    f"  Oplog window ({oplog_hours}h) is shorter than the backup interval "
                    f"({backup_interval}h) — point-in-time recovery (PITR) may not be possible "
                    f"for all gaps between backups."
                )
            else:
                findings.append(
                    f"  Oplog window ({oplog_hours}h) covers the backup interval ({backup_interval}h) — "
                    f"PITR is achievable if backups run on schedule."
                )
        else:
            findings.append(
                "Oplog window could not be determined — PITR coverage cannot be assessed. "
                "Ensure replication is configured for standalone instances if PITR is required."
            )

        return ReportSection(
            name="Backup & Recovery",
            severity=worst_severity(severities),
            signals=signals,
            findings=findings,
        )

    # ── Section 10: Connections & Concurrency (BL-013) — OM API ─────────────────

    def _section_connections(self) -> ReportSection:
        """§10 — connections, WiredTiger tickets, lock queue per RS member via OM."""
        _SKIP = ReportSection(
            name="Connections & Concurrency",
            severity=HealthSeverity.OK,
            signals=[],
            findings=["Ops Manager not configured — set OM_URL and API keys to enable this section."],
        )
        if self._om is None:
            return _SKIP
        try:
            hosts = self._om.get_hosts()
            if not hosts:
                return ReportSection(
                    name="Connections & Concurrency",
                    severity=HealthSeverity.OK,
                    signals=[],
                    findings=["Ops Manager returned no hosts for this group."],
                )

            METRICS = [
                "CONNECTIONS", "TICKETS_AVAILABLE_READS",
                "TICKETS_AVAILABLE_WRITE", "GLOBAL_LOCK_CURRENT_QUEUE_TOTAL",
            ]
            total_connections = 0
            min_tickets_reads: Optional[float] = None
            min_tickets_writes: Optional[float] = None
            max_lock_queue = 0.0
            member_lines: List[str] = []

            for h in hosts:
                meas = self._om.get_host_measurements(h["id"], METRICS)
                c  = meas.get("CONNECTIONS")
                tr = meas.get("TICKETS_AVAILABLE_READS")
                tw = meas.get("TICKETS_AVAILABLE_WRITE")
                lq = meas.get("GLOBAL_LOCK_CURRENT_QUEUE_TOTAL")
                if c  is not None: total_connections += int(c)
                if tr is not None: min_tickets_reads  = tr if min_tickets_reads  is None else min(min_tickets_reads,  tr)
                if tw is not None: min_tickets_writes = tw if min_tickets_writes is None else min(min_tickets_writes, tw)
                if lq is not None: max_lock_queue = max(max_lock_queue, lq)
                type_label = h.get("typeName", "UNKNOWN")
                conn_str   = f"{int(c)} conns" if c is not None else "conns n/a"
                member_lines.append(f"  {h.get('hostname','?')}:{h.get('port','?')}  [{type_label}]  {conn_str}")

            severities = [HealthSeverity.OK]
            signals: List[Signal] = []
            findings: List[str] = [f"Polled {len(hosts)} member(s):"] + member_lines

            signals.append(Signal("total_connections", total_connections, "connections",
                                   self._thresholds["connections_warning"]))
            if total_connections > self._thresholds["connections_warning"]:
                severities.append(HealthSeverity.WARNING)
                findings.append(
                    f"  Connections ({total_connections:,}) exceed warning threshold "
                    f"({self._thresholds['connections_warning']:,})."
                )

            if min_tickets_reads is not None:
                signals.append(Signal("tickets_reads", min_tickets_reads, "tickets",
                                       self._thresholds["tickets_warning"]))
                if min_tickets_reads < self._thresholds["tickets_warning"]:
                    severities.append(HealthSeverity.WARNING)
                    findings.append(f"  Read ticket exhaustion risk ({min_tickets_reads:.0f} remaining).")

            if min_tickets_writes is not None:
                signals.append(Signal("tickets_writes", min_tickets_writes, "tickets",
                                       self._thresholds["tickets_warning"]))
                if min_tickets_writes < self._thresholds["tickets_warning"]:
                    severities.append(HealthSeverity.WARNING)
                    findings.append(f"  Write ticket exhaustion risk ({min_tickets_writes:.0f} remaining).")

            signals.append(Signal("lock_queue_total", max_lock_queue, "operations",
                                   self._thresholds["lock_queue_warning"]))
            if max_lock_queue > self._thresholds["lock_queue_warning"]:
                severities.append(HealthSeverity.WARNING)
                findings.append(
                    f"  Lock queue depth ({max_lock_queue:.0f}) exceeds threshold — "
                    f"investigate long-running operations."
                )

            return ReportSection(
                name="Connections & Concurrency",
                severity=worst_severity(severities),
                signals=signals,
                findings=findings,
            )
        except Exception as exc:
            logger.warning("§9 connections section failed: %s", exc)
            return ReportSection(
                name="Connections & Concurrency",
                severity=HealthSeverity.OK,
                signals=[],
                findings=[f"Ops Manager unreachable — section skipped ({exc})."],
            )

    # ── Section 10: Infrastructure (BL-015) — OM API ────────────────────────────

    def _section_infrastructure(self) -> ReportSection:
        """§10 — CPU, disk I/O, system memory per primary via OM."""
        _SKIP = ReportSection(
            name="Infrastructure",
            severity=HealthSeverity.OK,
            signals=[],
            findings=["Ops Manager not configured — set OM_URL and API keys to enable this section."],
        )
        if self._om is None:
            return _SKIP
        try:
            hosts = self._om.get_hosts()
            if not hosts:
                return ReportSection(
                    name="Infrastructure",
                    severity=HealthSeverity.OK,
                    signals=[],
                    findings=["Ops Manager returned no hosts for this group."],
                )

            primary = next(
                (h for h in hosts if h.get("typeName", "").upper() == "REPLICA_PRIMARY"),
                hosts[0],
            )
            secondaries = [h for h in hosts if h.get("id") != primary["id"]]

            HOST_METRICS = [
                "PROCESS_NORMALIZED_CPU_USER",
                "SYSTEM_CPU_IOWAIT",
                "SYSTEM_MEMORY_USED",
                "SYSTEM_MEMORY_AVAILABLE",
            ]
            DISK_METRICS = [
                "DISK_PARTITION_IOPS_WRITE",
                "DISK_PARTITION_LATENCY_WRITE",
            ]

            severities = [HealthSeverity.OK]
            signals: List[Signal] = []
            sec_note = f"  ({len(secondaries)} secondary node(s))" if secondaries else ""
            findings: List[str] = [
                f"Primary: {primary.get('hostname','?')}:{primary.get('port','?')}{sec_note}"
            ]

            meas = self._om.get_host_measurements(primary["id"], HOST_METRICS)

            cpu_user = meas.get("PROCESS_NORMALIZED_CPU_USER")
            if cpu_user is not None:
                cpu_user = round(cpu_user, 1)
                signals.append(Signal("cpu_user_pct", cpu_user, "%",
                                       self._thresholds["cpu_user_pct_warning"]))
                if cpu_user >= self._thresholds["cpu_user_pct_warning"]:
                    severities.append(HealthSeverity.WARNING)
                    findings.append(
                        f"  CPU user ({cpu_user}%) exceeds {self._thresholds['cpu_user_pct_warning']}% — "
                        f"check for expensive queries or background tasks."
                    )

            iowait = meas.get("SYSTEM_CPU_IOWAIT")
            if iowait is not None:
                iowait = round(iowait, 1)
                signals.append(Signal("cpu_iowait_pct", iowait, "%",
                                       self._thresholds["cpu_iowait_pct_warning"]))
                if iowait >= self._thresholds["cpu_iowait_pct_warning"]:
                    severities.append(HealthSeverity.WARNING)
                    findings.append(
                        f"  I/O wait ({iowait}%) above {self._thresholds['cpu_iowait_pct_warning']}% — "
                        f"disk subsystem may be a bottleneck."
                    )

            mem_used  = meas.get("SYSTEM_MEMORY_USED")
            mem_avail = meas.get("SYSTEM_MEMORY_AVAILABLE")
            if mem_used is not None and mem_avail is not None and (mem_used + mem_avail) > 0:
                mem_used_pct = round(mem_used / (mem_used + mem_avail) * 100, 1)
                signals.append(Signal("system_memory_used_pct", mem_used_pct, "%",
                                       self._thresholds["system_memory_used_pct_warning"]))
                if mem_used_pct >= self._thresholds["system_memory_used_pct_warning"]:
                    severities.append(HealthSeverity.WARNING)
                    findings.append(
                        f"  System memory usage ({mem_used_pct}%) above "
                        f"{self._thresholds['system_memory_used_pct_warning']}% — risk of OS swapping."
                    )

            partition = self._om.get_disk_name(primary["id"])
            if partition:
                disk_meas = self._om.get_disk_measurements(primary["id"], partition, DISK_METRICS)
                findings.append(f"Disk partition: {partition}")
                iops_write = disk_meas.get("DISK_PARTITION_IOPS_WRITE")
                if iops_write is not None:
                    signals.append(Signal("disk_iops_write", round(iops_write, 1), "IOPS"))
                lat_write = disk_meas.get("DISK_PARTITION_LATENCY_WRITE")
                if lat_write is not None:
                    lat_write = round(lat_write, 2)
                    signals.append(Signal("disk_write_latency_ms", lat_write, "ms",
                                           self._thresholds["disk_write_latency_warning_ms"]))
                    if lat_write >= self._thresholds["disk_write_latency_warning_ms"]:
                        severities.append(HealthSeverity.WARNING)
                        findings.append(
                            f"  Disk write latency ({lat_write}ms) above "
                            f"{self._thresholds['disk_write_latency_warning_ms']}ms — "
                            f"investigate disk I/O saturation."
                        )
            else:
                findings.append("Disk partition not discoverable via Ops Manager.")

            return ReportSection(
                name="Infrastructure",
                severity=worst_severity(severities),
                signals=signals,
                findings=findings,
            )
        except Exception as exc:
            logger.warning("§10 infrastructure section failed: %s", exc)
            return ReportSection(
                name="Infrastructure",
                severity=HealthSeverity.OK,
                signals=[],
                findings=[f"Ops Manager unreachable — section skipped ({exc})."],
            )

    # ── helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt_duration(seconds: float) -> str:
        """BL-115: Human-readable duration — '2h 30m', '45s', '1h 0m'."""
        s = int(seconds)
        if s < 60:
            return f"{s}s"
        if s < 3600:
            m, rem = divmod(s, 60)
            return f"{m}m {rem}s" if rem else f"{m}m"
        h, rem = divmod(s, 3600)
        m = rem // 60
        return f"{h}h {m}m" if m else f"{h}h"

    # Mapping: baseline metric key → (section_name, signal_name, higher_is_worse)
    _TREND_SIGNAL_MAP: List[tuple] = [
        ("slow_query_pct",        "Query Performance", "slow_query_pct",            True),
        ("max_execution_ms",      "Query Performance", "max_execution_ms",           True),
        ("disk_used_pct",         "Server Health",     "filesystem_disk_used_pct",   True),
        ("oplog_window_hours",    "Replication Health","oplog_window_hours",          False),
        ("cache_hit_ratio_pct",   "Operations",        "wt_cache_hit_ratio",          False),
        ("lock_wait_pct",         "Operations",        "lock_wait_pct",               True),
        ("cluster_targeting_ratio","Operations",       "cluster_targeting_ratio",     True),
        ("page_faults",           "Operations",        "page_faults",                 True),
    ]

    def _attach_trends(self, report: "HealthCheckReport") -> None:
        """BL-114: Attach trend direction to tracked signals based on baseline history."""
        if self._baseline.is_cold_start:
            return
        sec_map = {s.name: s for s in report.sections}
        for _bkey, sec_name, sig_name, higher_is_worse in self._TREND_SIGNAL_MAP:
            section = sec_map.get(sec_name)
            if not section:
                continue
            for sig in section.signals:
                if sig.name == sig_name and isinstance(sig.value, (int, float)):
                    sig.trend = self._baseline.trend(_bkey, float(sig.value), higher_is_worse)

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

    @staticmethod
    def _detect_pipeline_antipatterns(pipeline: list) -> List[str]:
        """BL-102: return anti-pattern descriptions found in an aggregation pipeline."""
        issues: List[str] = []
        if not isinstance(pipeline, list) or not pipeline:
            return issues
        stage_names: List[str] = []
        for stage in pipeline:
            if isinstance(stage, dict):
                for k in stage:
                    stage_names.append(k)
                    break
        if not stage_names:
            return issues

        match_idx  = next((i for i, s in enumerate(stage_names) if s == "$match"),  -1)
        lookup_idx = next((i for i, s in enumerate(stage_names) if s == "$lookup"), -1)
        unwind_idx = next((i for i, s in enumerate(stage_names) if s == "$unwind"), -1)

        # $lookup before any $match → join runs on entire collection
        if lookup_idx >= 0 and (match_idx < 0 or lookup_idx < match_idx):
            issues.append("$lookup before $match — join on full collection; add $match first")
        # $unwind before $match → array expansion on all documents
        if unwind_idx >= 0 and (match_idx < 0 or unwind_idx < match_idx):
            issues.append("$unwind before $match — array expansion on full collection")
        # $group as first stage — no index usage possible
        if stage_names[0] == "$group":
            issues.append("$group as first stage — full scan required; add $match first if possible")
        # $sort without subsequent $limit — unbounded in-memory sort
        for i, s in enumerate(stage_names):
            if s == "$sort" and "$limit" not in stage_names[i + 1:]:
                issues.append("$sort without $limit — unbounded in-memory sort; add $limit after $sort")
                break
        return issues

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

    def _precompute_cardinality(self, slow_queries: List[Dict[str, Any]]) -> None:
        """BL-101: estimate field cardinality for slow-query collections using $sample.

        Stores results in self._low_cardinality_fields keyed by "db.collection.field".
        A field is flagged as low-cardinality when < 3% of sampled documents have distinct values.
        """
        self._low_cardinality_fields: Dict[str, Dict] = {}
        if not slow_queries or self._mcp is None:
            return

        by_coll: Dict[tuple, Dict] = {}
        for q in slow_queries:
            coll = q["collection"]
            db   = q.get("db", "")
            if coll and not coll.startswith("system."):
                key = (db, coll)
                if key not in by_coll:
                    by_coll[key] = {"db": db, "collection": coll, "fields": set()}
                for f in self._extract_filter_fields(q.get("query", {})):
                    by_coll[key]["fields"].add(f)

        SAMPLE_SIZE = 10_000
        for (db, coll), info in list(by_coll.items())[:5]:  # cap to 5 collections
            for field in list(info["fields"])[:3]:           # cap to 3 fields each
                try:
                    pipeline = [
                        {"$sample": {"size": SAMPLE_SIZE}},
                        {"$group": {"_id": f"${field}"}},
                        {"$count": "distinct_count"},
                    ]
                    result = self._mcp.aggregate(db, coll, pipeline)
                    if result:
                        distinct = result[0].get("distinct_count", 0)
                        ratio = distinct / SAMPLE_SIZE
                        if ratio < 0.03:
                            self._low_cardinality_fields[f"{db}.{coll}.{field}"] = {
                                "distinct_ratio": round(ratio, 4),
                                "sample_size": SAMPLE_SIZE,
                            }
                except Exception as exc:
                    logger.debug(
                        "BL-101 cardinality check failed for %s.%s.%s: %s",
                        db, coll, field, exc,
                    )

    def _build_recommendations(
        self,
        slow_queries: List[Dict[str, Any]],
        sections: List[ReportSection],
        unused_indexes: List[Dict[str, Any]],
    ) -> List[Recommendation]:
        recs: List[Recommendation] = []

        # BL-089: derive recommendation priority from section consequence tier.
        # Prevents P3/P4 section issues (index, observability) from appearing as "P0".
        from utils.html_reporter import SECTION_TIER

        def _rec_priority(section_name: str, is_critical: bool = True) -> str:
            """Return recommendation priority label = section consequence tier (P0–P4).

            Per config/scoring_tiers.md §4: priority is the tier of the section
            that produced the finding. A Replication breach → P0. Missing Indexes → P3.
            The is_critical param is kept for call-site compatibility but not used.
            """
            return SECTION_TIER.get(section_name, "P4")

        # Build flat signal → (value, threshold, section_name) lookup used by rules below
        _sigs: Dict[str, Any] = {}
        _sig_section: Dict[str, str] = {}
        for _s in sections:
            for _sig in _s.signals:
                _sigs[_sig.name] = _sig
                _sig_section[_sig.name] = _s.name

        def _val(name: str):
            """Return (value, threshold) for a named signal, or (None, None)."""
            sig = _sigs.get(name)
            if sig is None:
                return None, None
            return sig.value, sig.threshold

        def _breached_high(name: str) -> bool:
            v, t = _val(name)
            return isinstance(v, (int, float)) and isinstance(t, (int, float)) and v > t

        def _breached_low(name: str) -> bool:
            v, t = _val(name)
            return isinstance(v, (int, float)) and isinstance(t, (int, float)) and v < t

        # ── MEDIUM: create missing indexes for slow full-scan collections ─────────
        # Missing Indexes is a P3 section (performance, not durability) → medium priority.
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
                if (q.get("docs_examined", 0) >= self._thresholds["full_scan_examined_min"]
                    and (q.get("docs_returned", 0) / q["docs_examined"]
                         if q.get("docs_examined") else 1.0)
                    <= self._thresholds["full_scan_selectivity_max"])
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

            # BL-101: downgrade confidence if suggested index fields have low cardinality
            low_card_note = ""
            lc_map = getattr(self, "_low_cardinality_fields", {})
            for field in best_fields:
                lc_key = f"{db_label}.{coll}.{field}"
                if lc_key in lc_map:
                    ratio = lc_map[lc_key]["distinct_ratio"]
                    confidence  = "low"
                    low_card_note = (
                        f" — note: field '{field}' has low cardinality "
                        f"({ratio * 100:.1f}% distinct), index selectivity will be poor"
                    )
                    break

            sort_note = (
                f"; has_sort_stage=true (sort on {sort_fields[0]} done in memory)"
                if has_sort and sort_fields else
                f"; has_sort_stage=true" if has_sort else ""
            )
            evidence_base = (
                f"{examined:,} docs scanned, {returned} returned ({ms}ms) — {examined / returned:.0f}x targeting ratio, COLLSCAN{sort_note}"
                if returned else
                f"COLLSCAN, 0 docs returned{sort_note}"
            )
            recs.append(Recommendation(
                priority=_rec_priority("Missing Indexes"),  # P3 → medium
                collection=fq_coll,
                action=action,
                evidence=evidence_base + low_card_note,
                confidence=confidence,
            ))

        # ── HIGH: short oplog window — replication sync risk (P0 section) ──────────
        for section in sections:
            for sig in section.signals:
                if sig.name == "oplog_window_hours" and sig.threshold is not None:
                    if isinstance(sig.value, (int, float)) and sig.value < sig.threshold:
                        recs.append(Recommendation(
                            priority=_rec_priority("Replication Health"),  # P0 → high
                            collection="cluster",
                            action=f"db.adminCommand({{replSetResizeOplog: 1, size: 51200}})  // run on PRIMARY",
                            evidence=f"oplog_window={sig.value:.1f}h < {sig.threshold}h threshold — secondary resync risk",
                            confidence="high",
                        ))

        # ── MEDIUM: profiler disabled — slow queries not captured (P3 section) ──
        for section in sections:
            for sig in section.signals:
                if sig.name == "profiler_disabled_dbs" and isinstance(sig.value, int) and sig.value > 0:
                    recs.append(Recommendation(
                        priority=_rec_priority("Query Performance"),  # P3 → medium
                        collection="cluster",
                        action="db.setProfilingLevel(1, {slowms: 100})  // run on each affected database",
                        evidence=f"{sig.value} database(s) have profiler disabled — slow queries not captured",
                        confidence="high",
                    ))

        # ── LOW: drop unused indexes (P4 section — observability, no operational risk) ──
        for idx in unused_indexes:
            db_name    = idx["db"]
            coll_name  = idx["collection"]
            index_name = idx["name"]
            since      = idx.get("since", "last restart") or "last restart"
            recs.append(Recommendation(
                priority=_rec_priority("Unused Indexes"),  # P4 → low
                collection=f"{db_name}.{coll_name}",
                action=f'db.{coll_name}.dropIndex("{index_name}")',
                evidence=f'0 accesses since {since} — write overhead with no read benefit',
                confidence="medium",
            ))

        # ── HIGH: disk space running low (Storage & Capacity P1) ─────────────
        if _breached_high("filesystem_disk_used_pct"):
            v, t = _val("filesystem_disk_used_pct")
            recs.append(Recommendation(
                priority=_rec_priority("Storage & Capacity"),  # P1 → high
                collection="cluster",
                action="db.runCommand({compact: '<collection>'}), expand volume, or add TTL indexes to expire old data",
                evidence=f"filesystem_disk_used_pct={v:.1f}% exceeds {t}% — writes will stop when disk is full",
                confidence="high",
            ))

        # ── HIGH: WiredTiger cache hit ratio too low (Operations P1) ────────
        if _breached_low("wt_cache_hit_ratio"):
            v, t = _val("wt_cache_hit_ratio")
            recs.append(Recommendation(
                priority=_rec_priority("Operations"),  # P1 → high
                collection="cluster",
                action="Increase storage.wiredTiger.engineConfig.cacheSizeGB to 50-60% of available RAM",
                evidence=f"wt_cache_hit_ratio={v:.1f}% below {t}% threshold — reads bypassing cache, hitting disk",
                confidence="high",
            ))

        # ── HIGH: resident memory high — OOM or swap risk (Operations P1) ────
        if _breached_high("memory_resident_mb"):
            v, t = _val("memory_resident_mb")
            recs.append(Recommendation(
                priority=_rec_priority("Operations"),  # P1 → high
                collection="cluster",
                action="Lower storage.wiredTiger.engineConfig.cacheSizeGB, add indexes, or add RAM",
                evidence=f"memory_resident_mb={v:.0f}MB exceeds {t:.0f}MB threshold — swap risk",
                confidence="high",
            ))

        # ── HIGH: global lock wait % elevated (Operations P1) ────────────────
        if _breached_high("lock_wait_pct"):
            v, t = _val("lock_wait_pct")
            recs.append(Recommendation(
                priority=_rec_priority("Operations"),  # P1 → high
                collection="cluster",
                action="db.currentOp({waitingForLock: true}) to find blocking operations",
                evidence=f"lock_wait_pct={v:.1f}% exceeds {t}% threshold — {v:.1f}% time spent waiting for locks",
                confidence="high",
            ))

        # ── P1: cluster targeting ratio high — signal lives in Operations (P1 tier) ──────────
        # Must fire even when per-collection createIndex recs exist: those address specific
        # collections; this one flags the cluster-wide scan problem that drives the Operations
        # CRITICAL and its score penalty, so the Action Plan has a P1 action to match.
        if _breached_high("cluster_targeting_ratio"):
            v, t = _val("cluster_targeting_ratio")
            recs.append(Recommendation(
                priority=_rec_priority("Operations"),  # signal is in Operations → P1
                collection="cluster",
                action="Add indexes on frequently filtered fields — see Missing Indexes section for specific collections",
                evidence=f"cluster_targeting_ratio={v:.1f}x vs {t}x threshold — scanning {v:.1f} docs per result causes cache pressure and write stalls",
                confidence="medium",
            ))

        # ── MEDIUM: sort spill to disk (Query Performance P3) ───────────────
        if _breached_high("sort_spill_count"):
            v, _ = _val("sort_spill_count")
            recs.append(Recommendation(
                priority=_rec_priority("Query Performance"),  # P3 → medium
                collection="cluster",
                action="Add indexes covering sort fields, or set allowDiskUseByDefault: true in mongod.conf",
                evidence=f"sort_spill_count={v} — {v} sort(s) exceeded in-memory buffer and spilled to disk",
                confidence="high",
            ))

        # ── LOW: profiler slowms threshold too high (Query Performance P3, warning-level) ─
        if _breached_high("profiler_high_slowms_dbs"):
            v, _ = _val("profiler_high_slowms_dbs")
            recs.append(Recommendation(
                priority=_rec_priority("Query Performance", is_critical=False),  # P3 warning → low
                collection="cluster",
                action="db.setProfilingLevel(1, {slowms: 50})  // run on each affected database",
                evidence=f"{v} database(s) have slowms too high — queries between 50-100ms are not captured",
                confidence="medium",
            ))

        # ── MEDIUM: connection count approaching limit (Connections & Concurrency P2) ──
        if _breached_high("total_connections"):
            v, t = _val("total_connections")
            recs.append(Recommendation(
                priority=_rec_priority("Connections & Concurrency"),  # P2 → medium
                collection="cluster",
                action="Reduce maxPoolSize in application drivers, or run db.currentOp() to find idle connections",
                evidence=f"total_connections={v:.0f} exceeds {t:.0f} threshold — memory overhead and scheduling pressure",
                confidence="medium",
            ))

        # ── HIGH: read ticket exhaustion (Operations P1) ─────────────────────
        if _breached_low("tickets_reads"):
            v, t = _val("tickets_reads")
            recs.append(Recommendation(
                priority=_rec_priority("Operations"),  # P1 → high
                collection="cluster",
                action="db.currentOp({op: 'query'}) to find queries holding tickets; add indexes to reduce scan time",
                evidence=f"tickets_reads={v:.0f} remaining (threshold: {t:.0f}) — read concurrency slots nearly exhausted",
                confidence="high",
            ))

        # ── HIGH: write ticket exhaustion (Operations P1) ────────────────────
        if _breached_low("tickets_writes"):
            v, t = _val("tickets_writes")
            recs.append(Recommendation(
                priority=_rec_priority("Operations"),  # P1 → high
                collection="cluster",
                action="db.currentOp({op: {$in: ['insert','update','remove']}}) to find writes holding tickets; batch bulk writes",
                evidence=f"tickets_writes={v:.0f} remaining (threshold: {t:.0f}) — write concurrency slots nearly exhausted",
                confidence="high",
            ))

        # ── MEDIUM: high I/O wait (Infrastructure P2) ────────────────────────
        if _breached_high("cpu_iowait_pct"):
            v, t = _val("cpu_iowait_pct")
            recs.append(Recommendation(
                priority=_rec_priority("Infrastructure"),  # P2 → medium
                collection="cluster",
                action="Add indexes to reduce scans, increase WiredTiger cache, or upgrade to faster storage (NVMe SSD)",
                evidence=f"cpu_iowait_pct={v:.1f}% exceeds {t}% threshold — {v:.1f}% CPU time spent waiting on disk I/O",
                confidence="medium",
            ))

        # ── MEDIUM: system memory near exhaustion (Infrastructure P2) ────────
        if _breached_high("system_memory_used_pct"):
            v, t = _val("system_memory_used_pct")
            recs.append(Recommendation(
                priority=_rec_priority("Infrastructure"),  # P2 → medium
                collection="cluster",
                action="Reduce storage.wiredTiger.engineConfig.cacheSizeGB to leave OS headroom, or add RAM",
                evidence=f"system_memory_used_pct={v:.1f}% exceeds {t}% threshold — swapping causes severe latency spikes",
                confidence="high",
            ))

        # ── MEDIUM: disk write latency high (Infrastructure P2) ─────────────
        if _breached_high("disk_write_latency_ms"):
            v, t = _val("disk_write_latency_ms")
            recs.append(Recommendation(
                priority=_rec_priority("Infrastructure"),  # P2 → medium
                collection="cluster",
                action="Check iostat/iotop for write pressure; enable journalCompressor: snappy, or upgrade storage",
                evidence=f"disk_write_latency_ms={v:.1f}ms exceeds {t}ms threshold — elevated write latency",
                confidence="medium",
            ))

        # ── BL-106: no active backup cursor (Backup & Recovery P1) ────────────
        bc_sig = _sigs.get("backup_cursor_open")
        if bc_sig is not None and bc_sig.value == 0:
            recs.append(Recommendation(
                priority=_rec_priority("Backup & Recovery"),  # P1 → high
                collection="cluster",
                action="Configure automated backups (mongodump cron, filesystem snapshots, or Percona Backup)",
                evidence="backupCursorOpen=false — no backup process connected; data loss risk on failure",
                confidence="medium",
            ))

        # ── BL-107: PITR gap — oplog window shorter than backup interval ──────
        pitr_sig = _sigs.get("oplog_window_for_pitr")
        if (pitr_sig is not None and pitr_sig.threshold is not None
                and isinstance(pitr_sig.value, (int, float))
                and pitr_sig.value < pitr_sig.threshold):
            v, t = pitr_sig.value, pitr_sig.threshold
            recs.append(Recommendation(
                priority=_rec_priority("Backup & Recovery"),  # P1 → high
                collection="cluster",
                action=f"db.adminCommand({{replSetResizeOplog: 1, size: 51200}})  // run on PRIMARY",
                evidence=f"oplog_window={v:.1f}h < backup_interval={t:.0f}h — PITR gap between snapshots",
                confidence="high",
            ))

        # ── BL-103: plan cache hit rate low (Operations P2) ──────────────────
        if _breached_low("plan_cache_hit_rate_pct"):
            v, t = _val("plan_cache_hit_rate_pct")
            recs.append(Recommendation(
                priority=_rec_priority("Operations"),  # P2 → medium
                collection="cluster",
                action="Stabilise query shapes: avoid dynamic field names, use parameterised queries",
                evidence=f"plan_cache_hit_rate_pct={v:.1f}% below {t}% threshold — frequent re-planning adds latency",
                confidence="medium",
            ))

        # Deduplicate: same (collection, action) → keep highest priority only
        _PRI_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
        seen: Dict[tuple, Recommendation] = {}
        for r in recs:
            key = (r.collection.strip().lower(), r.action.strip().lower())
            existing = seen.get(key)
            if existing is None or _PRI_ORDER.get(r.priority, 9) < _PRI_ORDER.get(existing.priority, 9):
                seen[key] = r
        deduped = sorted(seen.values(), key=lambda r: _PRI_ORDER.get(r.priority, 9))
        return deduped

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
