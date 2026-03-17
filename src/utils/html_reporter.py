"""Self-contained HTML report renderer for HealthCheckReport (BL-060) — v4.

Design system (from sample):
  - Font: system-ui (no external deps, no loading flash)
  - Weights: 400 body / 500 emphasis only
  - Sizes: 11px labels · 13px body · 15px (unused) · 22px metrics
  - Color encodes meaning only — red=critical, amber=warning, green=ok
  - Borders: single rgba opacity throughout
  - Alerts: left-border accent, no icon element
  - Status bar: CSS-grid gap separator trick
"""
from __future__ import annotations

import math
from models.health_check_report import (
    HealthCheckReport, HealthSeverity, ReportSection, worst_severity,
)

# ── severity maps ──────────────────────────────────────────────────────────────

# CSS color var name (used inline)
_COLOR = {
    HealthSeverity.OK:       "var(--green)",
    HealthSeverity.WARNING:  "var(--amber)",
    HealthSeverity.CRITICAL: "var(--red)",
}
# Tag class suffix: tag-{X}
_TAG = {
    HealthSeverity.OK:       "tag-green",
    HealthSeverity.WARNING:  "tag-amber",
    HealthSeverity.CRITICAL: "tag-red",
}
_TAG_LABEL = {
    HealthSeverity.OK:       "Healthy",
    HealthSeverity.WARNING:  "Warning",
    HealthSeverity.CRITICAL: "Critical",
}
# Nav dot class
_DOT = {
    HealthSeverity.OK:       "d-green",
    HealthSeverity.WARNING:  "d-amber",
    HealthSeverity.CRITICAL: "d-red",
}
# Alert div class: alert-{X}
_ALERT = {
    HealthSeverity.OK:       "alert-green",
    HealthSeverity.WARNING:  "alert-amber",
    HealthSeverity.CRITICAL: "alert-red",
}
# Status bar value color class
_STATUS_COLOR = {
    HealthSeverity.OK:       "c-green",
    HealthSeverity.WARNING:  "c-amber",
    HealthSeverity.CRITICAL: "c-red",
}
# Recommendation priority badge class
_REC_PRI = {"high": "rp0", "medium": "rp1", "low": "rp2"}
_REC_LBL = {"high": "P0",  "medium": "P1",  "low": "P2"}


# ── section routing ────────────────────────────────────────────────────────────

_SECTION_META: dict[str, tuple[str, str]] = {
    "Cluster Overview":   ("sec-overview",       "Cluster status"),
    "Server Health":      ("sec-server",         "Server health"),
    "Replication Health": ("sec-replication",    "Replication health"),
    "Storage & Capacity": ("sec-storage",        "Storage"),
    "Query Performance":  ("sec-queries",        "Slow query analysis"),
    "Missing Indexes":    ("sec-indexes",        "Missing indexes"),
    "Unused Indexes":     ("sec-indexes-unused", "Unused indexes"),
}

_NAV_GROUPS: list[tuple[str, list[tuple[str, str, str | None]]]] = [
    ("Overview", [
        ("Cluster status",  "sec-overview",    "Cluster Overview"),
        ("Server health",   "sec-server",      "Server Health"),
        ("Alerts",          "alerts",          None),
    ]),
    ("Performance", [
        ("Slow queries",    "sec-queries",     "Query Performance"),
        ("Index analysis",  "sec-indexes",     None),
        ("Operations",      "sec-ops",         None),
    ]),
    ("Reliability", [
        ("Replication",     "sec-replication", "Replication Health"),
        ("Connections",     "sec-connections", None),
        ("Storage",         "sec-storage",     "Storage & Capacity"),
    ]),
    ("Action", [
        ("Recommendations", "recommendations", None),
    ]),
]

_OPS_UNAVAILABLE = [
    "Reads/sec, writes/sec, getmore rate",
    "Lock wait time and blocking operations",
    "WiredTiger cache hit rate and eviction stats",
    "Page faults and memory (RSS)",
]
_CONN_UNAVAILABLE = [
    "Current / max connections per node",
    "Connection pool utilisation by client service",
    "Connection creation rate and average age",
    "Connections waiting for a lock",
]


# ── CSS ────────────────────────────────────────────────────────────────────────

_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --font: system-ui, -apple-system, sans-serif;
  --mono: ui-monospace, 'SF Mono', 'Cascadia Code', monospace;

  --bg:        #0e1117;
  --surface:   #161b25;
  --surface2:  #1c2333;
  --border:    rgba(255,255,255,0.10);
  --border-em: rgba(255,255,255,0.18);

  --t1: #f0f4fa;
  --t2: #a8b5c8;
  --t3: #6b7a94;

  --red:   #f06060;
  --amber: #e09b3a;
  --green: #32c98a;

  --red-bg:    rgba(240,96,96,0.10);
  --amber-bg:  rgba(224,155,58,0.10);
  --green-bg:  rgba(50,201,138,0.10);

  --red-border:   rgba(240,96,96,0.28);
  --amber-border: rgba(224,155,58,0.28);
  --green-border: rgba(50,201,138,0.28);
}

body {
  background: var(--bg);
  color: var(--t1);
  font-family: var(--font);
  font-size: 13px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

/* ── Layout ── */
.layout { display: flex; min-height: 100vh; }

/* ── Sidebar ── */
.sidebar {
  width: 220px; min-width: 220px;
  background: var(--surface);
  border-right: 1px solid var(--border);
  padding: 24px 0;
  position: sticky; top: 0;
  height: 100vh; overflow-y: auto;
  display: flex; flex-direction: column;
}
.sidebar-top { padding: 0 16px 20px; border-bottom: 1px solid var(--border); margin-bottom: 12px; }
.sidebar-cluster { font-size: 15px; font-weight: 500; color: var(--t1); margin-bottom: 2px; }
.sidebar-meta { font-size: 11px; color: var(--t3); font-family: var(--mono); }

.nav-group { padding: 0 8px; margin-bottom: 8px; }
.nav-group-label { font-size: 11px; color: var(--t3); padding: 6px 8px 3px; letter-spacing: 0.04em; }

.nav-item {
  display: flex; align-items: center; gap: 8px;
  padding: 5px 8px; border-radius: 5px;
  font-size: 13px; color: var(--t2);
  text-decoration: none;
  transition: background 0.1s, color 0.1s;
}
.nav-item:hover  { background: var(--surface2); color: var(--t1); }
.nav-item.active { background: rgba(77,159,255,0.10); color: #4d9fff; }

.nav-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.d-red   { background: var(--red); }
.d-amber { background: var(--amber); }
.d-green { background: var(--green); }
.d-gray  { background: var(--t3); }

.sidebar-score {
  margin-top: auto;
  padding: 16px 16px 0;
  border-top: 1px solid var(--border);
  display: flex; align-items: center; gap: 12px;
}
.score-ring { position: relative; width: 44px; height: 44px; flex-shrink: 0; }
.score-ring svg { transform: rotate(-90deg); }
.score-num {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 500;
}
.score-info   { font-size: 12px; color: var(--t2); }
.score-status { font-size: 11px; margin-top: 1px; }

/* ── Main ── */
.main { flex: 1; padding: 32px 40px; max-width: 920px; }

/* ── Report header ── */
.report-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: 28px; padding-bottom: 20px; border-bottom: 1px solid var(--border);
}
.report-title { font-size: 18px; font-weight: 500; color: var(--t1); margin-bottom: 3px; }
.report-sub   { font-size: 13px; color: var(--t2); }
.report-right { text-align: right; font-size: 11px; color: var(--t3); font-family: var(--mono); line-height: 1.8; }
.report-right strong { color: var(--t2); font-weight: 400; }

/* ── Status bar — gap separator trick ── */
.status-bar {
  display: grid;
  gap: 1px; background: var(--border);
  border: 1px solid var(--border); border-radius: 8px;
  overflow: hidden; margin-bottom: 28px;
}
.status-cell { background: var(--surface); padding: 12px 14px; text-align: center; }
.status-val  { font-size: 18px; font-weight: 500; font-family: var(--mono); margin-bottom: 3px; }
.status-lbl  { font-size: 11px; color: var(--t3); }
.c-red   { color: var(--red); }
.c-amber { color: var(--amber); }
.c-green { color: var(--green); }
.c-dim   { color: var(--t1); }

/* ── Section ── */
.section { margin-bottom: 4px; scroll-margin-top: 24px; }
.section-hd { display: flex; align-items: baseline; gap: 8px; margin-bottom: 12px; }
.section-title { font-size: 13px; font-weight: 500; color: var(--t1); }

.tag { font-size: 11px; padding: 1px 7px; border-radius: 4px; font-family: var(--mono); }
.tag-red   { background: var(--red-bg);   color: var(--red);   border: 1px solid var(--red-border); }
.tag-amber { background: var(--amber-bg); color: var(--amber); border: 1px solid var(--amber-border); }
.tag-green { background: var(--green-bg); color: var(--green); border: 1px solid var(--green-border); }
.tag-gray  { background: var(--surface2); color: var(--t3);   border: 1px solid var(--border); }

.divider { border: none; border-top: 1px solid var(--border); margin: 24px 0; }

/* ── Alert — left-border accent ── */
.alert {
  border-radius: 6px; padding: 12px 14px;
  margin-bottom: 8px; border-left: 2px solid;
}
.alert-red   { background: var(--red-bg);   border-color: var(--red); }
.alert-amber { background: var(--amber-bg); border-color: var(--amber); }
.alert-green { background: var(--green-bg); border-color: var(--green); }
.alert-title { font-size: 13px; font-weight: 500; margin-bottom: 4px; }
.alert-red   .alert-title { color: var(--red); }
.alert-amber .alert-title { color: var(--amber); }
.alert-green .alert-title { color: var(--green); }
.alert-body { font-size: 12px; color: var(--t2); line-height: 1.6; }
code { font-family: var(--mono); font-size: 11px; color: var(--t2); }

/* ── Findings list ── */
.findings { list-style: none; font-size: 12px; line-height: 1.7; margin-top: 8px; }
.findings li { padding: 2px 0; color: var(--t2); }
.findings li::before { content: "—  "; color: var(--t3); }
.findings li.indent { padding-left: 1.5rem; color: var(--t3); font-family: var(--mono); font-size: 11px; }
.findings li.indent::before { content: ""; }

/* ── Metric grid ── */
.metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 14px; }
.metric {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 6px; padding: 12px 14px;
}
.metric.m-red   { border-color: var(--red-border); }
.metric.m-amber { border-color: var(--amber-border); }
.metric-lbl   { font-size: 11px; color: var(--t3); margin-bottom: 5px; }
.metric-val   { font-size: 22px; font-weight: 500; font-family: var(--mono); margin-bottom: 2px; }
.metric-sub   { font-size: 11px; color: var(--t3); }
.metric-limit { font-size: 11px; color: var(--t3); margin-top: 3px; }

/* ── Placeholder ── */
.placeholder {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 6px; padding: 14px 16px;
}
.placeholder-title { font-size: 12px; color: var(--t3); margin-bottom: 8px; }
.placeholder-list  { list-style: none; margin-bottom: 10px; }
.placeholder-list li { font-size: 12px; color: var(--t2); padding: 2px 0; }
.placeholder-list li::before { content: "—  "; color: var(--t3); }
.placeholder-ref { font-size: 11px; color: var(--t3); font-family: var(--mono); }
.placeholder-ref code { color: var(--t2); background: var(--surface); padding: 1px 5px; border-radius: 3px; }

/* ── Recommendations ── */
.rec-list { list-style: none; }
.rec-item { display: flex; gap: 10px; padding: 10px 0; border-bottom: 1px solid var(--border); align-items: flex-start; }
.rec-item:last-child { border-bottom: none; }
.rec-p { font-size: 11px; font-family: var(--mono); padding: 2px 6px; border-radius: 3px; flex-shrink: 0; margin-top: 1px; }
.rp0 { background: var(--red-bg);   color: var(--red);   border: 1px solid var(--red-border); }
.rp1 { background: var(--amber-bg); color: var(--amber); border: 1px solid var(--amber-border); }
.rp2 { background: var(--surface2); color: var(--t3);   border: 1px solid var(--border); }
.rec-body { font-size: 12px; color: var(--t2); line-height: 1.6; flex: 1; }
.rec-body strong { color: var(--t1); font-weight: 500; display: block; margin-bottom: 2px; font-size: 13px; }
.rec-action { font-family: var(--mono); font-size: 11px; color: var(--t2); background: var(--surface2); border: 1px solid var(--border); border-radius: 4px; padding: 3px 8px; display: inline-block; margin: 3px 0 4px; word-break: break-all; }
.rec-evidence { font-size: 12px; color: var(--t2); }
.conf-high { color: var(--green); font-size: 11px; font-family: var(--mono); }
.conf-med  { color: var(--amber); font-size: 11px; font-family: var(--mono); }
.conf-low  { color: var(--t3);   font-size: 11px; font-family: var(--mono); }
.no-recs   { font-size: 12px; color: var(--t3); padding: 12px 0; }

/* ── Footer ── */
.report-footer { padding: 16px 0; text-align: center; font-size: 11px; color: var(--t3); border-top: 1px solid var(--border); margin-top: 8px; font-family: var(--mono); }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-thumb { background: var(--border-em); border-radius: 3px; }

/* ── Responsive ── */
@media (max-width: 768px) {
  .layout { flex-direction: column; }
  .sidebar { width: 100%; height: auto; position: relative; }
  .main { padding: 16px; max-width: none; }
  .metric-grid { grid-template-columns: repeat(2, 1fr); }
  .report-header { flex-direction: column; gap: 12px; }
  .report-right { text-align: left; }
}
"""


# ── helpers ────────────────────────────────────────────────────────────────────

def _health_score(report: HealthCheckReport) -> int:
    if not report.sections:
        return 100
    weights = {HealthSeverity.OK: 1.0, HealthSeverity.WARNING: 0.6, HealthSeverity.CRITICAL: 0.0}
    return round(sum(weights[s.severity] for s in report.sections) / len(report.sections) * 100)

def _fmt(v: object) -> str:
    if isinstance(v, float): return f"{v:,.1f}"
    if isinstance(v, int):   return f"{v:,}"
    return str(v)


# ── sidebar ────────────────────────────────────────────────────────────────────

def _sidebar(report: HealthCheckReport, score: int) -> str:
    cluster  = report.cluster_uri.split("@")[-1] if "@" in report.cluster_uri else report.cluster_uri
    date_str = report.timestamp.strftime("%Y-%m-%d · %H:%M UTC")

    by_name  = {s.name: s for s in report.sections}
    n_issues = sum(1 for s in report.sections if s.severity != HealthSeverity.OK)

    def _dot(anchor: str, section_name: str | None) -> str:
        if section_name and section_name in by_name:
            return _DOT[by_name[section_name].severity]
        if anchor == "alerts":
            if n_issues == 0: return "d-gray"
            return "d-red" if any(s.severity == HealthSeverity.CRITICAL for s in report.sections) else "d-amber"
        if anchor == "sec-indexes":
            sevs = [by_name[n].severity for n in ("Missing Indexes", "Unused Indexes") if n in by_name]
            return _DOT[worst_severity(sevs)] if sevs else "d-gray"
        if anchor == "recommendations":
            return "d-green" if report.recommendations else "d-gray"
        return "d-gray"

    groups_html: list[str] = []
    for group_name, items in _NAV_GROUPS:
        nav_items: list[str] = []
        for label, anchor, section_name in items:
            display = label
            if anchor == "alerts":
                display = f"Alerts ({n_issues})" if n_issues else "Alerts"
            dot_cls = _dot(anchor, section_name)
            nav_items.append(
                f'    <a class="nav-item" href="#{anchor}">'
                f'<span class="nav-dot {dot_cls}"></span>{display}</a>'
            )
        groups_html.append(
            f'  <div class="nav-group">\n'
            f'    <div class="nav-group-label">{group_name}</div>\n'
            + "\n".join(nav_items)
            + "\n  </div>"
        )

    sev_color  = _COLOR[report.overall_severity]
    sev_label  = _TAG_LABEL[report.overall_severity]
    issue_str  = f"{n_issues} issue{'s' if n_issues != 1 else ''}" if n_issues else "All clear"

    r    = 17
    circ = 2 * math.pi * r
    off  = circ * (1 - score / 100)

    return f"""<nav class="sidebar">
  <div class="sidebar-top">
    <div class="sidebar-cluster">{cluster}</div>
    <div class="sidebar-meta">{date_str}</div>
  </div>
{"".join(groups_html)}
  <div class="sidebar-score">
    <div class="score-ring">
      <svg width="44" height="44" viewBox="0 0 44 44">
        <circle cx="22" cy="22" r="{r}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="3.5"/>
        <circle cx="22" cy="22" r="{r}" fill="none" stroke="{sev_color}" stroke-width="3.5"
          stroke-dasharray="{circ:.1f}" stroke-dashoffset="{off:.1f}" stroke-linecap="round"/>
      </svg>
      <div class="score-num" style="color:{sev_color}">{score}</div>
    </div>
    <div>
      <div class="score-info">Overall health</div>
      <div class="score-status" style="color:{sev_color}">{sev_label} · {issue_str}</div>
    </div>
  </div>
</nav>"""


# ── status bar ─────────────────────────────────────────────────────────────────

_STATUS_SLOTS = [
    ("database_count",            "Databases"),
    ("collection_count",          "Collections"),
    ("slow_query_count",          "Slow queries"),
    ("under_indexed_collections", "Missing indexes"),
    ("unused_indexes",            "Unused indexes"),
    ("oplog_window_hours",        "Oplog window"),
]

def _status_bar(report: HealthCheckReport) -> str:
    sig_map: dict[str, tuple] = {}
    for section in report.sections:
        for sig in section.signals:
            sig_map[sig.name] = (sig.value, sig.unit or "", section.severity)

    cells: list[str] = []
    for name, label in _STATUS_SLOTS:
        if name not in sig_map:
            continue
        val, unit, sev = sig_map[name]
        color   = _STATUS_COLOR[sev]
        display = _fmt(val)
        if unit and unit not in ("collections", "databases", "indexes", "queries", "members"):
            display += f"&thinsp;{unit}"
        cells.append(
            f'<div class="status-cell">'
            f'<div class="status-val {color}">{display}</div>'
            f'<div class="status-lbl">{label}</div>'
            f'</div>'
        )

    if not cells:
        return ""

    n = len(cells)
    return (
        f'<div class="status-bar" style="grid-template-columns:repeat({n},1fr)">'
        + "".join(cells)
        + "</div>"
    )


# ── metric grid ───────────────────────────────────────────────────────────────

def _metric_grid(section: ReportSection) -> str:
    if not section.signals:
        return ""
    cards: list[str] = []
    for sig in section.signals:
        over = (
            sig.threshold is not None
            and isinstance(sig.value, (int, float))
            and sig.value > sig.threshold
        )
        if over:
            m_cls     = "m-red" if section.severity == HealthSeverity.CRITICAL else "m-amber"
            val_color = _COLOR[section.severity]
        else:
            m_cls, val_color = "", "var(--t1)"

        limit_html = (
            f'<div class="metric-limit">limit {sig.threshold} {sig.unit or ""}</div>'
            if sig.threshold is not None else ""
        )
        cards.append(
            f'<div class="metric {m_cls}">'
            f'<div class="metric-lbl">{sig.name.replace("_", " ").title()}</div>'
            f'<div class="metric-val" style="color:{val_color}">{_fmt(sig.value)}</div>'
            f'<div class="metric-sub">{sig.unit or ""}</div>'
            f'{limit_html}'
            f'</div>'
        )
    return f'<div class="metric-grid">{"".join(cards)}</div>'


# ── findings ──────────────────────────────────────────────────────────────────

def _findings_html(section: ReportSection) -> str:
    if not section.findings:
        return ""

    # Map severity to alert class
    alert_cls = {
        HealthSeverity.CRITICAL: "alert-red",
        HealthSeverity.WARNING:  "alert-amber",
        HealthSeverity.OK:       "alert-green",
    }[section.severity]

    parts: list[str] = []
    alert_shown = False
    list_items: list[str] = []

    for line in section.findings:
        is_indent = line.startswith("  ")
        if not is_indent and not alert_shown and section.severity != HealthSeverity.OK:
            parts.append(
                f'<div class="alert {alert_cls}">'
                f'<div class="alert-title">{line.strip()}</div>'
                f'</div>'
            )
            alert_shown = True
        else:
            cls = "indent" if is_indent else ""
            list_items.append(f'<li class="{cls}">{line.strip()}</li>')

    if list_items:
        parts.append(f'<ul class="findings">{"".join(list_items)}</ul>')
    return "".join(parts)


# ── section card ─────────────────────────────────────────────────────────────

def _section_card(section: ReportSection, anchor_id: str, display_name: str | None = None) -> str:
    name = display_name or section.name
    return (
        f'<div class="section" id="{anchor_id}">'
        f'<div class="section-hd">'
        f'<span class="section-title">{name}</span>'
        f'<span class="tag {_TAG[section.severity]}">{_TAG_LABEL[section.severity]}</span>'
        f'</div>'
        f'{_metric_grid(section)}'
        f'{_findings_html(section)}'
        f'</div>'
    )


# ── active alerts (synthetic) ─────────────────────────────────────────────────

def _alerts_section(report: HealthCheckReport) -> str:
    issues = [s for s in report.sections if s.severity != HealthSeverity.OK]

    if not issues:
        return (
            '<div class="section" id="alerts">'
            '<div class="section-hd">'
            '<span class="section-title">Active alerts</span>'
            '<span class="tag tag-green">Clear</span>'
            '</div>'
            '<div class="alert alert-green">'
            f'<div class="alert-title">No issues detected</div>'
            f'<div class="alert-body">All {len(report.sections)} sections are healthy.</div>'
            '</div></div>'
        )

    worst = (
        HealthSeverity.CRITICAL
        if any(s.severity == HealthSeverity.CRITICAL for s in issues)
        else HealthSeverity.WARNING
    )
    n = len(issues)

    boxes: list[str] = []
    for s in issues:
        _, display = _SECTION_META.get(s.name, ("", s.name))
        cls   = _ALERT[s.severity]
        first = s.findings[0].strip() if s.findings else "See section for details."
        desc_lines = [l.strip() for l in s.findings[1:] if not l.startswith("  ")]
        body_html = (
            f'<div class="alert-body">{desc_lines[0]}</div>'
            if desc_lines else ""
        )
        boxes.append(
            f'<div class="alert {cls}">'
            f'<div class="alert-title">{display} — {first}</div>'
            f'{body_html}'
            f'</div>'
        )

    return (
        f'<div class="section" id="alerts">'
        f'<div class="section-hd">'
        f'<span class="section-title">Active alerts</span>'
        f'<span class="tag {_TAG[worst]}">{n} issue{"s" if n != 1 else ""}</span>'
        f'</div>'
        + "".join(boxes)
        + "</div>"
    )


# ── placeholder section ───────────────────────────────────────────────────────

def _placeholder_section(anchor_id: str, title: str, unavailable: list[str], backlog_id: str) -> str:
    items_html = "".join(f'<li>{m}</li>' for m in unavailable)
    return (
        f'<div class="section" id="{anchor_id}">'
        f'<div class="section-hd">'
        f'<span class="section-title">{title}</span>'
        f'<span class="tag tag-gray">Not available</span>'
        f'</div>'
        f'<div class="placeholder">'
        f'<div class="placeholder-title">Metrics not accessible via read-only MCP:</div>'
        f'<ul class="placeholder-list">{items_html}</ul>'
        f'<div class="placeholder-ref">Planned: <code>{backlog_id}</code></div>'
        f'</div></div>'
    )


# ── recommendations ───────────────────────────────────────────────────────────

def _recommendations_html(recs: list) -> str:
    if not recs:
        return (
            '<div class="section" id="recommendations">'
            '<div class="section-hd">'
            '<span class="section-title">Recommendations</span>'
            '</div>'
            '<div class="no-recs">No actions required — cluster looks healthy.</div>'
            '</div>'
        )

    items: list[str] = []
    for rec in recs:
        pri_cls  = _REC_PRI.get(rec.priority, "rp2")
        pri_lbl  = _REC_LBL.get(rec.priority, "P2")
        conf_cls = {"high": "conf-high", "medium": "conf-med", "low": "conf-low"}.get(
            rec.confidence, "conf-low"
        )
        items.append(
            f'<li class="rec-item">'
            f'<span class="rec-p {pri_cls}">{pri_lbl}</span>'
            f'<div class="rec-body">'
            f'<strong>{rec.collection}</strong>'
            f'<div class="rec-action">{rec.action}</div>'
            f'<div class="rec-evidence">{rec.evidence} '
            f'<span class="{conf_cls}">{rec.confidence} confidence</span>'
            f'</div></div></li>'
        )

    worst_pri = "tag-red" if any(r.priority == "high" for r in recs) else "tag-amber"
    n = len(recs)
    return (
        f'<div class="section" id="recommendations">'
        f'<div class="section-hd">'
        f'<span class="section-title">Prioritised recommendations</span>'
        f'<span class="tag {worst_pri}">{n} action{"s" if n != 1 else ""}</span>'
        f'</div>'
        f'<ul class="rec-list">{"".join(items)}</ul>'
        f'</div>'
    )


# ── main content ──────────────────────────────────────────────────────────────

def _build_content(report: HealthCheckReport) -> str:
    by_name = {s.name: s for s in report.sections}

    def card(runner_name: str) -> str:
        if runner_name not in by_name:
            return ""
        anchor, display = _SECTION_META[runner_name]
        return _section_card(by_name[runner_name], anchor, display)

    blocks: list[str] = [
        card("Cluster Overview"),
        card("Server Health"),
        _alerts_section(report),
        card("Query Performance"),
        card("Missing Indexes"),
        card("Unused Indexes"),
        _placeholder_section("sec-ops",         "Operations", _OPS_UNAVAILABLE,  "BL-009"),
        card("Replication Health"),
        _placeholder_section("sec-connections", "Connections", _CONN_UNAVAILABLE, "BL-013"),
        card("Storage & Capacity"),
    ]
    return "\n<hr class=\"divider\">\n".join(b for b in blocks if b)


# ── JavaScript ────────────────────────────────────────────────────────────────

_JS = """
const sections = document.querySelectorAll('.section[id]');
const navLinks  = document.querySelectorAll('.nav-item[href^="#"]');

const observer = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      navLinks.forEach(l => l.classList.remove('active'));
      const link = document.querySelector(`.nav-item[href="#${entry.target.id}"]`);
      if (link) link.classList.add('active');
    }
  });
}, { threshold: 0.25 });

sections.forEach(s => observer.observe(s));
navLinks.forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    const t = document.querySelector(link.getAttribute('href'));
    if (t) t.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
});
"""


# ── entry point ───────────────────────────────────────────────────────────────

def render_html(report: HealthCheckReport) -> str:
    """Render a HealthCheckReport as a self-contained HTML string."""
    score   = _health_score(report)
    cluster = report.cluster_uri.split("@")[-1] if "@" in report.cluster_uri else report.cluster_uri
    ts      = report.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MongoDB health report — {cluster}</title>
  <style>{_CSS}</style>
</head>
<body>
<div class="layout">

{_sidebar(report, score)}

<main class="main">

  <div class="report-header">
    <div>
      <div class="report-title">MongoDB health check report</div>
      <div class="report-sub">Cluster diagnostic report</div>
    </div>
    <div class="report-right">
      <div><strong>{cluster}</strong></div>
      <div>Run&nbsp; {report.run_id}</div>
      <div>{ts}</div>
      <div>{len(report.sections)} sections · {len(report.recommendations)} recommendation(s)</div>
    </div>
  </div>

  {_status_bar(report)}

  {_build_content(report)}

  <hr class="divider">

  {_recommendations_html(report.recommendations)}

  <div class="report-footer">
    mongodb-dba-agent · {cluster} · {ts}
  </div>

</main>
</div>
<script>{_JS}</script>
</body>
</html>"""
