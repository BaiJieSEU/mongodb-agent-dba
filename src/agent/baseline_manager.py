"""Baseline-aware severity assessment for health checks (BL-021).

Tracks per-cluster metric history in agent_memory.health_baselines.
Each run's key signals are appended to a rolling window (default: 10 runs).
After COLD_START_RUNS (3) runs, severity is assessed relative to the cluster's
own historical baseline instead of static thresholds.

Hard safety limits (coded as constants) always apply regardless of baseline:
  - oplog window < 2 h  → CRITICAL
  - disk used > 95 %    → CRITICAL

Collection schema (one document per cluster):
{
    "cluster_uri": str,          # unique key
    "run_count":   int,          # total runs recorded for this cluster
    "metrics": {
        "slow_query_count":      [3, 5, 2, 4, 1],  # last BASELINE_WINDOW values
        "max_execution_ms":      [...],
        "disk_used_pct":         [...],
        "oplog_window_hours":    [...],
        "cache_hit_ratio_pct":   [...],
        "lock_wait_pct":         [...],
        "cluster_targeting_ratio": [...],
    }
}
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from pymongo import MongoClient

if TYPE_CHECKING:
    from models.health_check_report import HealthCheckReport, HealthSeverity

logger = logging.getLogger(__name__)

# ── Hard safety limits — never overridden by baseline ──────────────────────────
# (metric_name, threshold, direction)  direction: "above" | "below"
_HARD_LIMITS: List[Tuple[str, float, str]] = [
    ("disk_used_pct",      95.0, "above"),  # disk > 95 % → always CRITICAL
    ("oplog_window_hours",  2.0, "below"),  # oplog < 2 h → always CRITICAL
]

# Metrics where a *higher* current value compared with the baseline is worse
_HIGHER_IS_WORSE = {
    "slow_query_count",
    "max_execution_ms",
    "disk_used_pct",
    "lock_wait_pct",
    "cluster_targeting_ratio",
    "page_faults",           # BL-098
}

# Metrics where a *lower* current value compared with the baseline is worse
_LOWER_IS_WORSE = {
    "cache_hit_ratio_pct",
    "oplog_window_hours",
}


def _fmt(v: float) -> str:
    """Format a baseline mean for display (trim trailing zeros)."""
    if v == int(v):
        return str(int(v))
    return f"{v:.1f}"


class BaselineManager:
    """Loads, assesses, and records per-cluster metric baselines."""

    BASELINE_WINDOW = 10   # keep last N runs in the rolling window
    COLD_START_RUNS = 3    # need this many runs before baseline replaces static thresholds
    WARN_MULTIPLIER = 2.0  # current > 2× baseline → WARNING
    CRIT_MULTIPLIER = 3.0  # current > 3× baseline → CRITICAL

    def __init__(self, agent_store_uri: str, cluster_uri: str) -> None:
        self._agent_store_uri = agent_store_uri
        self._cluster_uri = cluster_uri
        self._run_count: int = 0
        self._metrics: Dict[str, List[float]] = {}

    def _get_collection(self):
        """Open a short-lived connection and return the health_baselines collection."""
        client = MongoClient(
            self._agent_store_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
        coll = client["agent_memory"]["health_baselines"]
        return client, coll

    # ── lifecycle ───────────────────────────────────────────────────────────────

    def _ensure_index(self, coll) -> None:
        try:
            coll.create_index(
                [("cluster_uri", 1)], unique=True, name="baseline_cluster_uri"
            )
        except Exception as exc:
            logger.debug("BaselineManager index creation skipped: %s", exc)

    def load(self) -> None:
        """Load prior baseline document for this cluster from agent_memory."""
        client = None
        try:
            client, coll = self._get_collection()
            self._ensure_index(coll)
            doc = coll.find_one({"cluster_uri": self._cluster_uri})
            if doc:
                self._run_count = int(doc.get("run_count", 0))
                self._metrics   = {k: list(v) for k, v in doc.get("metrics", {}).items()}
                # BL-122: load score history into metrics dict for unified access
                if "score_history" in doc:
                    self._metrics["score_history"] = list(doc["score_history"])
                logger.info(
                    "Baseline loaded for %s — %d prior run(s)",
                    self._cluster_uri, self._run_count,
                )
            else:
                logger.info(
                    "No baseline found for %s — starting cold-start period",
                    self._cluster_uri,
                )
        except Exception as exc:
            logger.warning("BaselineManager.load() failed (non-fatal): %s", exc)
        finally:
            if client:
                client.close()

    # ── query helpers ───────────────────────────────────────────────────────────

    @property
    def run_count(self) -> int:
        return self._run_count

    @property
    def is_cold_start(self) -> bool:
        return self._run_count < self.COLD_START_RUNS

    def cold_start_note(self) -> str:
        return (
            f"baseline not yet established "
            f"(run {self._run_count + 1} of {self.COLD_START_RUNS})"
        )

    def baseline_mean(self, metric: str) -> Optional[float]:
        """Rolling mean of recorded values, or None if no data."""
        values = self._metrics.get(metric)
        if not values:
            return None
        return sum(values) / len(values)

    def trend(self, metric: str, current: float, higher_is_worse: bool = True) -> Optional[str]:
        """Return "up" | "down" | "stable" | None.

        None means no baseline history yet (cold start or new metric).
        Direction is always raw: "up" means current > mean, "down" means current < mean.
        The caller / renderer decides whether "up" is good or bad for this metric.
        """
        if self.is_cold_start:
            return None
        mean = self.baseline_mean(metric)
        if mean is None or mean == 0:
            return None
        ratio = current / mean
        if ratio > 1.10:
            return "up"
        if ratio < 0.90:
            return "down"
        return "stable"

    # ── severity assessment ─────────────────────────────────────────────────────

    def assess(
        self,
        metric: str,
        value: float,
        static_warn: Optional[float] = None,
        static_crit: Optional[float] = None,
        higher_is_worse: bool = True,
    ) -> Tuple["HealthSeverity", str]:
        """Return (severity, context_note) for a metric observation.

        Priority order:
          1. Hard safety limits — always CRITICAL regardless of history
          2. Cold start — fall back to static thresholds with a note
          3. Baseline comparison — deviation × multiplier
          4. Static thresholds as a floor (never downgrade from a detected deviation)

        context_note is a parenthetical string suitable for appending to a finding,
        e.g. "(baseline: 2, 3.5× above normal)" or "(baseline not yet established)".
        Empty string means the metric is within normal bounds.
        """
        # Deferred import to avoid circular dependency at module load time
        from models.health_check_report import HealthSeverity, worst_severity

        # 1. Hard limits
        hard = self._hard_limit(metric, value)
        if hard is not None:
            return hard, ""

        # 2. Cold start — static thresholds + note
        if self.is_cold_start:
            sev = self._static_severity(value, static_warn, static_crit, higher_is_worse)
            return sev, f"({self.cold_start_note()})"

        # 3. Baseline comparison
        mean = self.baseline_mean(metric)
        if mean is None:
            # New metric — no history yet; fall back to static
            return self._static_severity(value, static_warn, static_crit, higher_is_worse), ""

        sev, note = self._baseline_severity(metric, value, mean, higher_is_worse)

        # 4. Static floor — never silently downgrade a genuinely bad value
        static_sev = self._static_severity(value, static_warn, static_crit, higher_is_worse)
        final_sev = worst_severity([sev, static_sev])
        return final_sev, note

    def _baseline_severity(
        self, metric: str, value: float, mean: float, higher_is_worse: bool
    ) -> Tuple["HealthSeverity", str]:
        from models.health_check_report import HealthSeverity

        if higher_is_worse:
            if mean == 0:
                if value > 0:
                    note = f"(baseline: 0, new occurrence)"
                    return HealthSeverity.WARNING, note
                return HealthSeverity.OK, f"(baseline: {_fmt(mean)})"

            ratio = value / mean
            if ratio >= self.CRIT_MULTIPLIER:
                sev, label = HealthSeverity.CRITICAL, f"{ratio:.1f}× above normal"
            elif ratio >= self.WARN_MULTIPLIER:
                sev, label = HealthSeverity.WARNING, f"{ratio:.1f}× above normal"
            else:
                return HealthSeverity.OK, f"(baseline: {_fmt(mean)})"
            return sev, f"(baseline: {_fmt(mean)}, {label})"

        else:  # lower_is_worse
            if value == 0:
                return HealthSeverity.CRITICAL, f"(baseline: {_fmt(mean)}, dropped to 0)"

            ratio = mean / value  # how many times below baseline
            if ratio >= self.CRIT_MULTIPLIER:
                sev, label = HealthSeverity.CRITICAL, f"{ratio:.1f}× below normal"
            elif ratio >= self.WARN_MULTIPLIER:
                sev, label = HealthSeverity.WARNING, f"{ratio:.1f}× below normal"
            else:
                return HealthSeverity.OK, f"(baseline: {_fmt(mean)})"
            return sev, f"(baseline: {_fmt(mean)}, {label})"

    @staticmethod
    def _static_severity(
        value: float,
        warn: Optional[float],
        crit: Optional[float],
        higher_is_worse: bool,
    ) -> "HealthSeverity":
        from models.health_check_report import HealthSeverity

        if higher_is_worse:
            if crit is not None and value >= crit:
                return HealthSeverity.CRITICAL
            if warn is not None and value >= warn:
                return HealthSeverity.WARNING
        else:
            if crit is not None and value <= crit:
                return HealthSeverity.CRITICAL
            if warn is not None and value <= warn:
                return HealthSeverity.WARNING
        return HealthSeverity.OK

    @staticmethod
    def _hard_limit(metric: str, value: float) -> Optional["HealthSeverity"]:
        from models.health_check_report import HealthSeverity

        for name, threshold, direction in _HARD_LIMITS:
            if metric == name:
                if direction == "above" and value >= threshold:
                    return HealthSeverity.CRITICAL
                if direction == "below" and value <= threshold:
                    return HealthSeverity.CRITICAL
        return None

    # ── persistence ─────────────────────────────────────────────────────────────

    def record_from_report(self, report: "HealthCheckReport", score: Optional[int] = None) -> None:
        """Extract key signals from report sections and persist to rolling baseline.

        score: the computed health score (0–100) for this run — stored for sparkline (BL-122).
        """
        # Maps (section_name, signal_name) → baseline_metric_key
        _SIGNAL_MAP: Dict[Tuple[str, str], str] = {
            ("Query Performance", "slow_query_pct"):        "slow_query_pct",
            ("Query Performance", "max_execution_ms"):      "max_execution_ms",
            ("Server Health",     "filesystem_disk_used_pct"): "disk_used_pct",
            ("Replication Health","oplog_window_hours"):    "oplog_window_hours",
            ("Operations",        "wt_cache_hit_ratio"):    "cache_hit_ratio_pct",
            ("Operations",        "lock_wait_pct"):         "lock_wait_pct",
            ("Operations",        "cluster_targeting_ratio"): "cluster_targeting_ratio",
            ("Operations",        "page_faults"):           "page_faults",   # BL-098
        }

        metrics: Dict[str, float] = {}
        for section in report.sections:
            for sig in section.signals:
                key = (section.name, sig.name)
                if key in _SIGNAL_MAP and isinstance(sig.value, (int, float)):
                    metrics[_SIGNAL_MAP[key]] = float(sig.value)

        if not metrics:
            logger.warning("BaselineManager: no recordable signals found in report")
            return

        client = None
        try:
            client, coll = self._get_collection()
            push_ops = {
                f"metrics.{k}": {"$each": [v], "$slice": -self.BASELINE_WINDOW}
                for k, v in metrics.items()
            }
            if score is not None:
                push_ops["score_history"] = {"$each": [score], "$slice": -self.BASELINE_WINDOW}
            coll.update_one(
                {"cluster_uri": self._cluster_uri},
                {"$inc": {"run_count": 1}, "$push": push_ops},
                upsert=True,
            )
            logger.info(
                "Baseline updated for %s — run %d, %d metric(s) recorded",
                self._cluster_uri, self._run_count + 1, len(metrics),
            )
        except Exception as exc:
            logger.warning("BaselineManager.record_from_report() failed (non-fatal): %s", exc)
        finally:
            if client:
                client.close()

    def score_history(self) -> List[int]:
        """Return stored score history for sparkline rendering (BL-122)."""
        return [int(v) for v in self._metrics.get("score_history", [])]
