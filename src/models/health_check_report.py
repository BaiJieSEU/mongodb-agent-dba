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

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"name": self.name, "value": self.value}
        if self.unit:
            d["unit"] = self.unit
        if self.threshold is not None:
            d["threshold"] = self.threshold
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
    priority: str       # high | medium | low
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
    report_path: str = ""       # filled in after save

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat() + "Z",
            "cluster_uri": self.cluster_uri,
            "overall_severity": self.overall_severity.value,
            "sections": [s.to_dict() for s in self.sections],
            "recommendations": [r.to_dict() for r in self.recommendations],
        }
