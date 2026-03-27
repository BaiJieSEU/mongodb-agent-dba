"""Markdown report renderer for HealthCheckReport (BL-061).

Produces standard CommonMark — no GitHub-specific extensions required.
Sections use ## headings with severity emoji prefix.
Signals render as a Markdown table.
Recommendations render as a numbered list with a bold action line.
"""
from __future__ import annotations

from models.health_check_report import HealthCheckReport, HealthSeverity, ReportSection

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


def render_markdown(report: HealthCheckReport) -> str:
    lines: list[str] = []

    overall_emoji = _EMOJI[report.overall_severity]
    overall_label = _LABEL[report.overall_severity]

    # ── Header ─────────────────────────────────────────────────────────────────
    lines += [
        "# MongoDB Cluster Health Report",
        "",
        f"| Field | Value |",
        f"|---|---|",
        f"| **Run ID** | `{report.run_id}` |",
        f"| **Time** | {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC |",
        f"| **Cluster** | `{report.cluster_uri}` |",
        f"| **Overall** | {overall_emoji} {overall_label} |",
        "",
        "---",
        "",
    ]

    # ── Sections ───────────────────────────────────────────────────────────────
    for i, section in enumerate(report.sections, 1):
        emoji = _EMOJI[section.severity]
        label = _LABEL[section.severity]

        lines += [
            f"## {emoji} §{i} {section.name}",
            "",
            f"**Severity:** {label}",
            "",
        ]

        # Signals table
        if section.signals:
            lines += [
                "| Signal | Value | Threshold |",
                "|---|---|---|",
            ]
            for sig in section.signals:
                val = f"{sig.value} {sig.unit}".strip()
                thr = f"{sig.threshold} {sig.unit}".strip() if sig.threshold is not None else "—"
                name = sig.name.replace("_", " ")
                lines.append(f"| {name} | {val} | {thr} |")
            lines.append("")

        # Findings
        if section.findings:
            for finding in section.findings:
                # Indent continuation lines as blockquote for readability
                if finding.startswith("  "):
                    lines.append(f"> {finding.strip()}")
                else:
                    lines.append(finding)
            lines.append("")

        lines.append("---")
        lines.append("")

    # ── Recommendations ────────────────────────────────────────────────────────
    lines += ["## Recommendations", ""]

    if not report.recommendations:
        lines += ["No actions required.", ""]
    else:
        _pri_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
        sorted_recs = sorted(report.recommendations, key=lambda r: _pri_order.get(r.priority, 9))
        for i, rec in enumerate(sorted_recs, 1):
            priority_label = rec.priority.upper()
            confidence_label = rec.confidence.upper()
            lines += [
                f"{i}. **[{priority_label}]** `{rec.collection}`",
                f"   - **Action:** `{rec.action}`",
                f"   - **Evidence:** {rec.evidence}",
                f"   - **Confidence:** {confidence_label}",
                "",
            ]

    return "\n".join(lines)
