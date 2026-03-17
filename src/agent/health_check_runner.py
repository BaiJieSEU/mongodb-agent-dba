"""Cluster health check runner (BL-020 through BL-004).

Deterministic pipeline — tool execution order is fixed, severity thresholds are
rule-based Python. LLM is NOT used here; findings are derived directly from
structured MCP results so scheduled runs are reliable and fast.

MCP tool availability (confirmed via list_tools()):
  ✅ list-databases, list-collections, find, aggregate, count
  ✅ collection-storage-size, db-stats, collection-indexes
  ⚠️  serverStatus — NOT available (no runCommand).
       Workaround: local.startup_log → version/uptime; db-stats → disk usage.
       Connections, memory, page faults cannot be obtained via MCP read-only.
  ⚠️  replSetGetStatus — NOT available.
       Workaround: local.system.replset → RS config; local.oplog.rs → oplog window.
       Member health states and per-member lag are not obtainable via MCP.

Section order:
  1  Cluster Overview      list-databases, list-collections
  2  Server Health         local.startup_log, db-stats (BL-001)
  3  Replication Health    local.system.replset, local.oplog.rs (BL-002)
  4  Storage & Capacity    collection-storage-size, count, db-stats (BL-003)
  5  Query Performance     find on system.profile
  6  Index Health          collection-indexes on top slow collections
  7  Index Usage           aggregate $indexStats (BL-004)
"""

import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone
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
    "disk_used_pct_warning": 80,
    "disk_used_pct_critical": 90,
    "oplog_window_warning_hours": 24,
    "oplog_window_critical_hours": 4,
    "full_scan_examined_min": 1000,
    "full_scan_selectivity_max": 0.01,
}

_SYSTEM_DBS = {"admin", "config", "local"}


class HealthCheckRunner:
    """Runs a complete cluster health check using MCP tools and produces a report."""

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

            # Fetch user databases once — shared by sections 1, 3, 4, 7
            db_blocks = self._mcp.call_tool("list-databases", {})
            all_dbs = self._parse_name_blocks(db_blocks)
            user_dbs = [d for d in all_dbs if d not in _SYSTEM_DBS]

            # Fixed, deterministic section order
            sections.append(self._section_cluster_overview(user_dbs))
            sections.append(self._section_server_health())                   # BL-001
            sections.append(self._section_replication_health())              # BL-002
            sections.append(self._section_storage_stats(user_dbs))          # BL-003
            perf_section, slow_queries = self._section_query_performance()
            sections.append(perf_section)
            top_colls = self._top_slow_collections(slow_queries, n=3)
            sections.append(self._section_index_health(top_colls))
            sections.append(self._section_index_usage(user_dbs))             # BL-004

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

    # ── MCP output parsers ─────────────────────────────────────────────────────

    @staticmethod
    def _parse_name_blocks(blocks: List[str]) -> List[str]:
        """Extract name from 'Name: foo' or 'Name: foo, Size: ...' MCP blocks."""
        names = []
        for b in blocks:
            if b.startswith("Name:"):
                raw = b[len("Name:"):].strip()
                names.append(raw.split(",")[0].strip())
        return names

    @staticmethod
    def _parse_db_stats(blocks: List[str]) -> Optional[Dict[str, Any]]:
        """Parse 'Statistics for database X: {json}' MCP block."""
        for b in blocks:
            if b.startswith("Statistics for database"):
                try:
                    return json.loads(b[b.index("{"):])
                except (ValueError, json.JSONDecodeError):
                    pass
        return None

    @staticmethod
    def _parse_storage_size_mb(blocks: List[str]) -> float:
        """Parse 'The size of `db.coll` is `N.NN MB`' block → float MB."""
        for b in blocks:
            m = re.search(r"is `([\d.]+)\s*(MB|KB|GB|bytes)`", b)
            if m:
                val, unit = float(m.group(1)), m.group(2)
                if unit == "KB":    return round(val / 1024, 3)
                if unit == "GB":    return round(val * 1024, 3)
                if unit == "bytes": return round(val / 1_048_576, 6)
                return round(val, 3)   # MB
        return 0.0

    @staticmethod
    def _parse_count(blocks: List[str]) -> int:
        """Parse 'Found N documents' block → int."""
        for b in blocks:
            m = re.search(r"Found ([\d,]+) documents", b)
            if m:
                return int(m.group(1).replace(",", ""))
        return 0

    @staticmethod
    def _parse_json_docs(blocks: List[str]) -> List[Dict[str, Any]]:
        """Parse MCP aggregate/find result blocks (skip header, parse JSON docs)."""
        docs = []
        for b in blocks[1:]:
            try:
                docs.append(json.loads(b))
            except (json.JSONDecodeError, TypeError):
                pass
        return docs

    # ── Section 1: Cluster Overview ────────────────────────────────────────────

    def _section_cluster_overview(self, user_dbs: List[str]) -> ReportSection:
        collections_by_db: Dict[str, List[str]] = {}
        for db in user_dbs:
            coll_blocks = self._mcp.call_tool("list-collections", {"database": db})
            colls = self._parse_name_blocks(coll_blocks)
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
        startup_blocks = self._mcp.call_tool("find", {
            "database": "local",
            "collection": "startup_log",
            "sort": {"startTime": -1},
            "limit": 1,
        })
        version, hostname, uptime_hours = "unknown", "unknown", 0.0
        for doc in self._parse_json_docs(startup_blocks):
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
        stats_blocks = self._mcp.call_tool("db-stats", {"database": "admin"})
        stats = self._parse_db_stats(stats_blocks) or {}
        fs_used  = stats.get("fsUsedSize",  0)
        fs_total = stats.get("fsTotalSize", 0)
        disk_used_gb  = round(fs_used  / 1_073_741_824, 1)
        disk_total_gb = round(fs_total / 1_073_741_824, 1)
        disk_used_pct = round(fs_used / fs_total * 100, 1) if fs_total else 0.0

        if disk_used_pct >= _THRESHOLDS["disk_used_pct_critical"]:
            severity = HealthSeverity.CRITICAL
        elif disk_used_pct >= _THRESHOLDS["disk_used_pct_warning"]:
            severity = HealthSeverity.WARNING
        else:
            severity = HealthSeverity.OK

        findings = [
            f"MongoDB {version}  ·  host: {hostname}  ·  uptime: {uptime_hours}h",
            f"Disk: {disk_used_gb} GB used of {disk_total_gb} GB ({disk_used_pct}%)",
            "Not available via MCP: active connections, memory (RSS), page faults, lock stats.",
        ]
        if disk_used_pct >= _THRESHOLDS["disk_used_pct_warning"]:
            findings.append(
                f"Disk usage at {disk_used_pct}% — "
                f"{'CRITICAL' if disk_used_pct >= _THRESHOLDS['disk_used_pct_critical'] else 'WARNING'}."
            )

        return ReportSection(
            name="Server Health",
            severity=severity,
            signals=[
                Signal("mongodb_version", version),
                Signal("uptime_hours", uptime_hours, "hours"),
                Signal("disk_used_gb", disk_used_gb, "GB"),
                Signal("disk_used_pct", disk_used_pct, "%", _THRESHOLDS["disk_used_pct_warning"]),
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
        rs_config_docs = self._parse_json_docs(
            self._mcp.call_tool("find", {"database": "local", "collection": "system.replset", "limit": 1})
        )
        is_replica_set = bool(rs_config_docs)
        rs_name = rs_config_docs[0].get("_id", "unknown") if rs_config_docs else None
        members = rs_config_docs[0].get("members", []) if rs_config_docs else []

        # Oplog window
        head_docs = self._parse_json_docs(
            self._mcp.call_tool("find", {"database": "local", "collection": "oplog.rs",
                                         "sort": {"ts": -1}, "limit": 1})
        )
        tail_docs = self._parse_json_docs(
            self._mcp.call_tool("find", {"database": "local", "collection": "oplog.rs",
                                         "sort": {"ts": 1}, "limit": 1})
        )

        def _ts_seconds(doc: Dict) -> Optional[int]:
            ts = doc.get("ts", {})
            if isinstance(ts, dict) and "$timestamp" in ts:
                return ts["$timestamp"]["t"]
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

        # Severity from oplog window
        severity = HealthSeverity.OK
        if oplog_window_hours is not None:
            if oplog_window_hours < _THRESHOLDS["oplog_window_critical_hours"]:
                severity = HealthSeverity.CRITICAL
            elif oplog_window_hours < _THRESHOLDS["oplog_window_warning_hours"]:
                severity = HealthSeverity.WARNING

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
            findings.append(f"Oplog window: {oplog_window_hours}h")
            if oplog_window_hours < _THRESHOLDS["oplog_window_warning_hours"]:
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
            db_stats = self._parse_db_stats(
                self._mcp.call_tool("db-stats", {"database": db})
            ) or {}
            total_data_mb  += db_stats.get("dataSize",  0) / 1_048_576
            total_index_mb += db_stats.get("indexSize", 0) / 1_048_576
            fs_used  = db_stats.get("fsUsedSize",  0)
            fs_total = db_stats.get("fsTotalSize", 0)
            if fs_total:
                disk_used_pct = round(fs_used / fs_total * 100, 1)

            coll_blocks = self._mcp.call_tool("list-collections", {"database": db})
            user_colls = [
                c for c in self._parse_name_blocks(coll_blocks)
                if not c.startswith("system.")
            ]
            for coll in user_colls:
                size_mb = self._parse_storage_size_mb(
                    self._mcp.call_tool("collection-storage-size", {"database": db, "collection": coll})
                )
                doc_count = self._parse_count(
                    self._mcp.call_tool("count", {"database": db, "collection": coll})
                )
                avg_bytes = round(size_mb * 1_048_576 / doc_count) if doc_count else 0
                coll_stats.append({
                    "db": db, "collection": coll,
                    "size_mb": size_mb, "doc_count": doc_count, "avg_bytes": avg_bytes,
                })

        coll_stats.sort(key=lambda x: -x["size_mb"])

        if disk_used_pct >= _THRESHOLDS["disk_used_pct_critical"]:
            severity = HealthSeverity.CRITICAL
        elif disk_used_pct >= _THRESHOLDS["disk_used_pct_warning"]:
            severity = HealthSeverity.WARNING
        else:
            severity = HealthSeverity.OK

        findings = [
            f"Data size: {total_data_mb:.1f} MB  ·  Index size: {total_index_mb:.1f} MB  "
            f"·  Disk used: {disk_used_pct}%",
            "Collections (largest first):",
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
                Signal("total_data_mb",   round(total_data_mb, 1),   "MB"),
                Signal("total_index_mb",  round(total_index_mb, 1),  "MB"),
                Signal("disk_used_pct",   disk_used_pct, "%", _THRESHOLDS["disk_used_pct_warning"]),
                Signal("collections_analysed", len(coll_stats), "collections"),
            ],
            findings=findings,
        )

    # ── Section 5: Query Performance ───────────────────────────────────────────

    def _section_query_performance(self) -> Tuple[ReportSection, List[Dict[str, Any]]]:
        threshold = self.config.agent.slow_query_threshold_ms
        limit     = self.config.agent.max_queries_to_analyze

        # TODO (BL-050): iterate all user databases; hard-coded to testdb for now
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
        for doc in self._parse_json_docs(blocks):
            ns = doc.get("ns", "")
            collection = ns.split(".", 1)[-1] if "." in ns else ns
            slow_queries.append({
                "collection": collection,
                "query":      doc.get("query", doc.get("command", {})),
                "execution_time_ms": doc.get("millis", 0),
                "docs_examined":     doc.get("docsExamined", 0),
                "docs_returned":     doc.get("nreturned", 0),
                "operation":         doc.get("op", "query"),
            })

        count  = len(slow_queries)
        max_ms = max((q["execution_time_ms"] for q in slow_queries), default=0)
        avg_ms = sum(q["execution_time_ms"] for q in slow_queries) / count if count else 0.0

        if count == 0:
            severity = HealthSeverity.OK
        elif count >= _THRESHOLDS["slow_query_count_critical"] or max_ms >= _THRESHOLDS["slow_query_ms_critical"]:
            severity = HealthSeverity.CRITICAL
        else:
            severity = HealthSeverity.WARNING

        by_coll: Dict[str, List[Dict]] = {}
        for q in slow_queries:
            by_coll.setdefault(q["collection"], []).append(q)

        findings: List[str] = []
        if count == 0:
            findings.append(f"No slow queries above {threshold}ms — profiler is active.")
        else:
            findings.append(
                f"{count} slow op(s)  threshold: {threshold}ms  max: {max_ms}ms  avg: {avg_ms:.0f}ms"
            )
            for coll, qs in sorted(by_coll.items(), key=lambda x: -len(x[1])):
                c_max  = max(q["execution_time_ms"] for q in qs)
                c_avg  = sum(q["execution_time_ms"] for q in qs) / len(qs)
                c_exam = max(q["docs_examined"] for q in qs)
                findings.append(
                    f"  {coll}: {len(qs)} op(s)  max {c_max}ms  avg {c_avg:.0f}ms  "
                    f"up to {c_exam:,} docs examined"
                )

        return ReportSection(
            name="Query Performance",
            severity=severity,
            signals=[
                Signal("slow_query_count",  count,             "queries", _THRESHOLDS["slow_query_count_warning"]),
                Signal("max_execution_ms",  max_ms,            "ms",      _THRESHOLDS["slow_query_ms_warning"]),
                Signal("avg_execution_ms",  round(avg_ms, 1),  "ms"),
            ],
            findings=findings,
        ), slow_queries

    # ── Section 6: Index Health ─────────────────────────────────────────────────

    def _section_index_health(self, collections: List[str]) -> ReportSection:
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
                "database": "testdb", "collection": coll,
            })
            index_data[coll] = [b for b in blocks if b.startswith("Field:")]

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
                Signal("collections_checked",       len(collections),    "collections"),
                Signal("under_indexed_collections", len(under_indexed),  "collections", 0),
            ],
            findings=findings,
        )

    # ── Section 7: Index Usage (BL-004) ────────────────────────────────────────

    def _section_index_usage(self, user_dbs: List[str]) -> ReportSection:
        """aggregate $indexStats — ops count per index since last mongod restart."""
        all_indexes: List[Dict[str, Any]] = []

        for db in user_dbs:
            coll_blocks = self._mcp.call_tool("list-collections", {"database": db})
            user_colls = [
                c for c in self._parse_name_blocks(coll_blocks)
                if not c.startswith("system.")
            ]
            for coll in user_colls:
                docs = self._parse_json_docs(
                    self._mcp.call_tool("aggregate", {
                        "database": db,
                        "collection": coll,
                        "pipeline": [{"$indexStats": {}}],
                    })
                )
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
        severity = HealthSeverity.WARNING if unused else HealthSeverity.OK

        findings = [
            f"{len(all_indexes)} total index(es) across "
            f"{len({i['collection'] for i in all_indexes})} collection(s)."
        ]
        if unused:
            findings.append(f"{len(unused)} unused index(es) (0 ops since restart):")
            for idx in unused:
                findings.append(
                    f"  {idx['db']}.{idx['collection']}.{idx['name']}  key={idx['key']}  since {idx['since']}"
                )
            findings.append("Consider dropping unused indexes to reduce write overhead and storage.")
        else:
            findings.append("All non-_id indexes have been used since last restart.")

        if used:
            findings.append(f"{len(used)} index(es) with recorded usage:")
            for idx in sorted(used, key=lambda x: -x["ops"])[:5]:
                findings.append(
                    f"  {idx['collection']}.{idx['name']}: {idx['ops']:,} ops"
                )

        return ReportSection(
            name="Index Usage",
            severity=severity,
            signals=[
                Signal("total_indexes",  len(all_indexes), "indexes"),
                Signal("unused_indexes", len(unused),      "indexes", 0),
                Signal("used_indexes",   len(used),        "indexes"),
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

            examined   = q.get("docs_examined", 0)
            returned   = q.get("docs_returned", 0)
            ms         = q.get("execution_time_ms", 0)
            selectivity = returned / examined if examined else 1.0

            if (examined < _THRESHOLDS["full_scan_examined_min"]
                    or selectivity > _THRESHOLDS["full_scan_selectivity_max"]):
                continue

            query_obj = q.get("query", {})
            if isinstance(query_obj, dict):
                filter_obj   = query_obj.get("filter", query_obj.get("query", query_obj))
                filter_fields = [
                    f for f in (filter_obj.keys() if isinstance(filter_obj, dict) else [])
                    if not f.startswith("$") and f not in ("find", "filter", "limit", "sort")
                ]
            else:
                filter_fields = []

            if filter_fields:
                index_spec = ", ".join(f'"{f}": 1' for f in filter_fields[:2])
                action     = f"db.{coll}.createIndex({{{index_spec}}})"
                confidence = "high"
            else:
                action     = f"Identify filter fields on {coll} and create a covering index"
                confidence = "medium"

            recs.append(Recommendation(
                priority="high",
                collection=coll,
                action=action,
                evidence=(
                    f"{examined:,} docs examined, {returned} returned ({ms}ms) — "
                    f"selectivity {selectivity:.4f}, likely full collection scan"
                ),
                confidence=confidence,
            ))

        return recs

    # ── persistence ────────────────────────────────────────────────────────────

    def _save_report(self, report: HealthCheckReport) -> Path:
        from utils.html_reporter import render_html

        REPORTS_DIR.mkdir(exist_ok=True)
        stem = f"health_{report.timestamp.strftime('%Y-%m-%d_%H-%M-%S')}"

        json_path = REPORTS_DIR / f"{stem}.json"
        json_path.write_text(json.dumps(report.to_dict(), indent=2, default=str))
        logger.info("Health check report saved: %s", json_path)

        # Set report_path before rendering HTML so the footer shows the correct path
        report.report_path = str(json_path)
        html_path = REPORTS_DIR / f"{stem}.html"
        html_path.write_text(render_html(report), encoding="utf-8")
        logger.info("HTML report saved: %s", html_path)

        return json_path

    def _purge_old_reports(self, days: int = 90) -> None:
        cutoff = datetime.utcnow() - timedelta(days=days)
        for pattern in ("health_*.json", "health_*.html"):
            for f in REPORTS_DIR.glob(pattern):
                if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                    f.unlink()
                    logger.info("Purged old report: %s", f)
