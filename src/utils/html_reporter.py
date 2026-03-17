"""Self-contained HTML report renderer for HealthCheckReport (BL-060).

No external dependencies — all CSS is inline. Output is a single .html file
that opens in any browser without needing Python, Node, or an internet connection.
"""

from models.health_check_report import HealthCheckReport, HealthSeverity, ReportSection, Recommendation

_COLOR = {
    HealthSeverity.OK:       ("#22c55e", "#052e16", "✓ OK"),
    HealthSeverity.WARNING:  ("#f59e0b", "#2d1a00", "⚠ WARNING"),
    HealthSeverity.CRITICAL: ("#ef4444", "#2d0a0a", "✗ CRITICAL"),
}

_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
  background: #0f172a;
  color: #e2e8f0;
  padding: 2rem 1.5rem;
  min-height: 100vh;
}

a { color: #7dd3fc; }

/* ── layout ── */
.container { max-width: 1100px; margin: 0 auto; }

/* ── header ── */
.header {
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 1.5rem 2rem;
  margin-bottom: 1.5rem;
  background: #1e293b;
}
.header h1 { font-size: 1.6rem; color: #f1f5f9; margin-bottom: 0.75rem; }
.meta-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 0.4rem 2rem; }
.meta-item { font-size: 0.85rem; color: #94a3b8; }
.meta-item span { color: #cbd5e1; }

/* ── overall severity banner ── */
.banner {
  border-radius: 8px;
  padding: 0.9rem 1.5rem;
  margin-bottom: 1.75rem;
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

/* ── section grid ── */
.sections {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(480px, 1fr));
  gap: 1.25rem;
  margin-bottom: 1.75rem;
}

.card {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 10px;
  overflow: hidden;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1.25rem;
  border-bottom: 1px solid #334155;
}
.card-header h2 { font-size: 0.95rem; font-weight: 600; color: #f1f5f9; }
.badge {
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.25rem 0.6rem;
  border-radius: 999px;
  letter-spacing: 0.04em;
}
.card-body { padding: 1rem 1.25rem; }

/* ── signals table ── */
.signals {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
  margin-bottom: 1rem;
}
.signals td { padding: 0.3rem 0.5rem; }
.signals td:first-child { color: #94a3b8; width: 55%; }
.signals td:last-child  { color: #e2e8f0; font-variant-numeric: tabular-nums; }
.threshold { color: #64748b; font-size: 0.75rem; }

/* ── findings list ── */
.findings { list-style: none; font-size: 0.83rem; line-height: 1.6; }
.findings li { padding: 0.15rem 0; color: #cbd5e1; }
.findings li::before { content: "›  "; color: #475569; }
.findings li.indent { padding-left: 1.5rem; color: #94a3b8; }
.findings li.indent::before { content: ""; }

/* ── recommendations ── */
.rec-section {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 1.75rem;
}
.rec-section h2 {
  padding: 0.75rem 1.25rem;
  border-bottom: 1px solid #334155;
  font-size: 0.95rem;
  color: #f1f5f9;
}
.rec-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.83rem;
}
.rec-table th {
  text-align: left;
  padding: 0.6rem 1.25rem;
  color: #64748b;
  font-weight: 600;
  font-size: 0.75rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  border-bottom: 1px solid #334155;
}
.rec-table td {
  padding: 0.75rem 1.25rem;
  vertical-align: top;
  border-bottom: 1px solid #1e293b;
  color: #cbd5e1;
}
.rec-table tr:last-child td { border-bottom: none; }
.rec-table td.action { font-family: monospace; font-size: 0.8rem; color: #7dd3fc; }
.rec-table td.evidence { color: #94a3b8; font-size: 0.8rem; }
.no-recs { padding: 1rem 1.25rem; color: #64748b; font-size: 0.85rem; }

/* ── footer ── */
.footer { font-size: 0.75rem; color: #475569; text-align: center; padding-top: 0.5rem; }

/* ── responsive ── */
@media (max-width: 640px) {
  .sections { grid-template-columns: 1fr; }
  body { padding: 1rem; }
}
"""


def _badge(severity: HealthSeverity) -> str:
    color, _, label = _COLOR[severity]
    return f'<span class="badge" style="background:{color}22;color:{color}">{label}</span>'


def _banner(severity: HealthSeverity) -> str:
    color, bg, label = _COLOR[severity]
    return (
        f'<div class="banner" style="background:{bg};border:1px solid {color}33;color:{color}">'
        f'<span style="font-size:1.4rem">{label.split()[0]}</span>'
        f'<span>Overall Cluster Health: {label.split()[-1]}</span>'
        f'</div>'
    )


def _signals_table(section: ReportSection) -> str:
    if not section.signals:
        return ""
    rows = []
    for sig in section.signals:
        val = f"{sig.value}"
        if sig.unit:
            val += f" <span style='color:#64748b'>{sig.unit}</span>"
        thresh = ""
        if sig.threshold is not None:
            thresh = f'<span class="threshold">(threshold: {sig.threshold} {sig.unit})</span>'
        rows.append(
            f"<tr><td>{sig.name.replace('_', ' ')}</td>"
            f"<td>{val} {thresh}</td></tr>"
        )
    return f'<table class="signals">{"".join(rows)}</table>'


def _findings_list(section: ReportSection) -> str:
    items = []
    for line in section.findings:
        if line.startswith("  "):
            items.append(f'<li class="indent">{line.strip()}</li>')
        else:
            items.append(f"<li>{line}</li>")
    return f'<ul class="findings">{"".join(items)}</ul>'


def _section_card(section: ReportSection, index: int) -> str:
    return f"""
<div class="card">
  <div class="card-header">
    <h2>§{index} &nbsp; {section.name}</h2>
    {_badge(section.severity)}
  </div>
  <div class="card-body">
    {_signals_table(section)}
    {_findings_list(section)}
  </div>
</div>"""


def _recommendations(recs: list) -> str:
    if not recs:
        return (
            '<div class="rec-section">'
            '<h2>Recommendations</h2>'
            '<p class="no-recs">No actions required — cluster looks healthy.</p>'
            '</div>'
        )

    _PRI_COLOR = {"high": "#ef4444", "medium": "#f59e0b", "low": "#22c55e"}
    _CONF_COLOR = {"high": "#22c55e", "medium": "#f59e0b", "low": "#94a3b8"}

    rows = []
    for rec in recs:
        pri_color  = _PRI_COLOR.get(rec.priority, "#94a3b8")
        conf_color = _CONF_COLOR.get(rec.confidence, "#94a3b8")
        rows.append(f"""
<tr>
  <td><span class="badge" style="background:{pri_color}22;color:{pri_color}">{rec.priority.upper()}</span></td>
  <td><strong>{rec.collection}</strong></td>
  <td class="action">{rec.action}</td>
  <td class="evidence">{rec.evidence}</td>
  <td><span style="color:{conf_color};font-size:0.8rem">{rec.confidence.upper()}</span></td>
</tr>""")

    return f"""
<div class="rec-section">
  <h2>Recommendations &nbsp;<span style="color:#64748b;font-weight:400;font-size:0.85rem">({len(recs)} item(s))</span></h2>
  <table class="rec-table">
    <thead><tr>
      <th>Priority</th><th>Collection</th><th>Action</th><th>Evidence</th><th>Confidence</th>
    </tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
</div>"""


def render_html(report: HealthCheckReport) -> str:
    """Render a HealthCheckReport as a self-contained HTML string."""

    section_cards = "\n".join(
        _section_card(s, i) for i, s in enumerate(report.sections, 1)
    )

    cluster_display = report.cluster_uri.split("@")[-1] if "@" in report.cluster_uri else report.cluster_uri

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MongoDB Health Check — {report.run_id}</title>
  <style>{_CSS}</style>
</head>
<body>
  <div class="container">

    <div class="header">
      <h1>MongoDB Cluster Health Check</h1>
      <div class="meta-grid">
        <div class="meta-item">Run ID &nbsp; <span>{report.run_id}</span></div>
        <div class="meta-item">Time &nbsp; <span>{report.timestamp.strftime("%Y-%m-%d %H:%M:%S")} UTC</span></div>
        <div class="meta-item">Cluster &nbsp; <span>{cluster_display}</span></div>
        <div class="meta-item">Sections &nbsp; <span>{len(report.sections)}</span></div>
      </div>
    </div>

    {_banner(report.overall_severity)}

    <div class="sections">
      {section_cards}
    </div>

    {_recommendations(report.recommendations)}

    <div class="footer">
      Report saved → {report.report_path or "—"} &nbsp;·&nbsp;
      Generated by MongoDB DBA Agent
    </div>

  </div>
</body>
</html>"""
