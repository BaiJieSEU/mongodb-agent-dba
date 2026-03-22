"""Markdown renderer for MultiClusterReport (BL-076)."""
from __future__ import annotations

from models.multi_cluster_report import MultiClusterReport
from models.health_check_report import HealthSeverity
from utils.markdown_reporter import render_markdown as _render_single

_EMOJI = {
    HealthSeverity.OK:       "✅",
    HealthSeverity.WARNING:  "⚠️",
    HealthSeverity.CRITICAL: "❌",
}
_LABEL = {
    HealthSeverity.OK:       "OK",
    HealthSeverity.WARNING:  "WARNING",
    HealthSeverity.CRITICAL: "CRITICAL",
}


def _cluster_display(cr) -> str:
    if cr.cluster_name:
        return cr.cluster_name
    uri = cr.cluster_uri
    return uri.split("@")[-1] if "@" in uri else uri


def render_multi_markdown(report: MultiClusterReport) -> str:
    lines: list[str] = []

    overall_emoji = _EMOJI[report.overall_severity]
    overall_label = _LABEL[report.overall_severity]

    lines += [
        "# MongoDB Fleet Health Report",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| **Run ID** | `{report.run_id}` |",
        f"| **Time** | {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC |",
        f"| **Clusters** | {report.cluster_count} |",
        f"| **Overall** | {overall_emoji} {overall_label} |",
        "",
        "---",
        "",
        "## Fleet Summary",
        "",
        "| Cluster | Overall | Critical sections | Warning sections | Recommendations |",
        "|---|---|---|---|---|",
    ]

    for cr in report.clusters:
        label = _cluster_display(cr)
        sev   = f"{_EMOJI[cr.overall_severity]} {_LABEL[cr.overall_severity]}"
        n_crit = sum(1 for s in cr.sections if s.severity == HealthSeverity.CRITICAL)
        n_warn = sum(1 for s in cr.sections if s.severity == HealthSeverity.WARNING)
        n_recs = len(cr.recommendations)
        lines.append(f"| {label} | {sev} | {n_crit} | {n_warn} | {n_recs} |")

    lines += ["", "---", ""]

    # Full per-cluster sections
    for i, cr in enumerate(report.clusters):
        label = _cluster_display(cr)
        lines += [f"# Cluster: {label}", ""]

        # Embed single-cluster markdown but skip its H1 header block
        cluster_md = _render_single(cr)
        cluster_lines = cluster_md.split("\n")
        # Find the first "---" separator which closes the header table, then take everything after
        start = 0
        for j, line in enumerate(cluster_lines):
            if line.strip() == "---":
                start = j + 1
                break
        lines += cluster_lines[start:]

        if i < len(report.clusters) - 1:
            lines += ["", "---", ""]

    return "\n".join(lines)
