"""Multi-cluster health check report model (BL-076)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from models.health_check_report import HealthCheckReport, HealthSeverity, worst_severity


@dataclass
class MultiClusterReport:
    """Unified report covering N clusters — BL-076."""
    run_id: str
    timestamp: datetime
    overall_severity: HealthSeverity
    clusters: List[HealthCheckReport]
    report_path: str = ""  # JSON path; .html and .md written alongside

    @property
    def cluster_count(self) -> int:
        return len(self.clusters)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat() + "Z",
            "cluster_count": self.cluster_count,
            "overall_severity": self.overall_severity.value,
            "clusters": [c.to_dict() for c in self.clusters],
        }
