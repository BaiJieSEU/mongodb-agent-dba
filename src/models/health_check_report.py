"""Typed data models for the cluster health check report (BL-020)."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class HealthSeverity(str, Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


# Used by max() across sections to derive overall severity
_SEVERITY_RANK = {HealthSeverity.OK: 0, HealthSeverity.WARNING: 1, HealthSeverity.CRITICAL: 2}


def worst_severity(severities: List[HealthSeverity]) -> HealthSeverity:
    return max(severities, key=lambda s: _SEVERITY_RANK[s], default=HealthSeverity.OK)


@dataclass
class Signal:
    """A single measured value, optionally compared to a threshold."""
    name: str
    value: Any
    unit: str = ""
    threshold: Optional[Any] = None
    tooltip: Optional[str] = None   # static definition or LLM-contextual interpretation

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"name": self.name, "value": self.value}
        if self.unit:
            d["unit"] = self.unit
        if self.threshold is not None:
            d["threshold"] = self.threshold
        if self.tooltip:
            d["tooltip"] = self.tooltip
        return d


@dataclass
class ReportSection:
    """One health-check dimension (query performance, index health, etc.)."""
    name: str
    severity: HealthSeverity
    signals: List[Signal]
    findings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "severity": self.severity.value,
            "signals": [s.to_dict() for s in self.signals],
            "findings": self.findings,
        }


@dataclass
class Recommendation:
    """One actionable recommendation produced by the health check."""
    priority: str       # P0–P4 (consequence tier of the section driving this recommendation)
    collection: str
    action: str         # exact MongoDB command or description
    evidence: str       # signals that drove this recommendation
    confidence: str     # high | medium | low

    def to_dict(self) -> Dict[str, Any]:
        return {
            "priority": self.priority,
            "collection": self.collection,
            "action": self.action,
            "evidence": self.evidence,
            "confidence": self.confidence,
        }


@dataclass
class HealthCheckReport:
    """Top-level health check report — matches BL-020 schema."""
    run_id: str
    timestamp: datetime
    cluster_uri: str
    overall_severity: HealthSeverity
    sections: List[ReportSection]
    recommendations: List[Recommendation]
    cluster_name: str = ""      # human-readable name from monitored_clusters config
    report_path: str = ""       # filled in after save
    agent_version: str = ""     # BL-087: version of this agent (from __version__)
    om_version: str = ""        # BL-087: Ops Manager version (empty if OM not configured)
    health_summary: str = ""    # LLM-generated natural language health summary

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat() + "Z",
            "cluster_uri": self.cluster_uri,
            "cluster_name": self.cluster_name,
            "overall_severity": self.overall_severity.value,
            "sections": [s.to_dict() for s in self.sections],
            "recommendations": [r.to_dict() for r in self.recommendations],
        }
        if self.agent_version:
            d["agent_version"] = self.agent_version
        if self.om_version:
            d["om_version"] = self.om_version
        if self.health_summary:
            d["health_summary"] = self.health_summary
        return d
