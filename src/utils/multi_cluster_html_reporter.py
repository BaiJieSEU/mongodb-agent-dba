"""Multi-cluster HTML report renderer (BL-076).

Produces a single self-contained HTML page with:
- Cluster switcher tabs at the top (severity-coloured dot per cluster)
- Per-cluster sidebar + main content pane (hidden/shown by JS)
- Pure CSS/JS tab switching — no page reload
"""
from __future__ import annotations

from models.multi_cluster_report import MultiClusterReport
from models.health_check_report import HealthSeverity
from utils.html_reporter import (
    _CSS, _health_score, _sidebar, _status_bar,
    _build_content, _recommendations_html, _overall_health_summary, _rating_explainer,
    SECTION_TIER, _TIER_LABEL,
)

_TAB_CSS = """
/* ── Cluster tab bar (BL-078 / BL-079) ── */
.cluster-tabs {
  display: flex; align-items: center; gap: 0;
  background: var(--surface); border-bottom: 1px solid var(--border);
  padding: 0 12px; overflow-x: auto; flex-shrink: 0;
  position: sticky; top: 0; z-index: 100;
  min-height: 44px;
}
.tab-btn {
  display: flex; align-items: center; gap: 8px;
  padding: 11px 18px; cursor: pointer;
  background: transparent; border: none; outline: none;
  border-bottom: 2px solid transparent;
  font-family: var(--font); font-size: 13px; color: var(--t2);
  white-space: nowrap; transition: color 0.12s, border-color 0.12s;
  flex-shrink: 0;
}
.tab-btn:hover  { color: var(--t1); }
.tab-btn.active { color: var(--t1); border-bottom-color: var(--blue); }
.tab-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.tdot-ok   { background: var(--green); }
.tdot-warn { background: var(--amber); }
.tdot-crit { background: var(--red); }

/* ── Cluster identity label (right side of tab bar — BL-079) ── */
.tab-spacer { flex: 1; min-width: 16px; }
.tab-identity {
  display: flex; align-items: center; gap: 7px;
  padding: 0 8px; font-size: 12px; color: var(--t2);
  white-space: nowrap; flex-shrink: 0; border-left: 1px solid var(--border);
  margin-left: 4px; padding-left: 16px;
}
.tab-id-label { color: var(--t3); font-size: 11px; }
.tab-id-name  { font-weight: 600; color: var(--t1); font-size: 13px; }

/* ── Dropdown nav for large fleets (> 6 clusters — BL-078) ── */
.cluster-select-wrap {
  display: flex; align-items: center; gap: 10px; padding: 0 4px;
}
.cluster-select {
  background: var(--surface2); border: 1px solid var(--border-em);
  color: var(--t1); font-family: var(--font); font-size: 13px;
  padding: 6px 10px; border-radius: 5px; cursor: pointer; outline: none;
  min-width: 220px;
}
.cluster-select:focus { border-color: var(--blue); }
.cluster-select option { background: var(--surface2); }

/* ── Each cluster panel — only one visible at a time ── */
.cluster-panel { display: none; }
.cluster-panel.active { display: flex; min-height: 100vh; }

/* Override sidebar offset to sit below sticky tab bar */
.cluster-panel .sidebar { top: 44px; height: calc(100vh - 44px); }
.cluster-panel .section { scroll-margin-top: 68px; }

/* ── Fleet summary panel (BL-091) ── */
.summary-panel { display: none; flex-direction: column; padding: 32px 40px; max-width: 900px; margin: 0 auto; width: 100%; box-sizing: border-box; }
.summary-panel.active { display: flex; }
.summary-head { margin-bottom: 28px; }
.summary-title { font-size: 22px; font-weight: 700; color: var(--t1); margin-bottom: 6px; }
.summary-sub { font-size: 13px; color: var(--t2); }
.fleet-score-badge {
  display: inline-block; font-size: 32px; font-weight: 800;
  padding: 6px 20px; border-radius: 8px; margin: 16px 0 4px;
  font-family: var(--mono);
}
.fleet-score-ok   { background: rgba(79,201,100,.15); color: var(--green); }
.fleet-score-warn { background: rgba(243,156,18,.15);  color: var(--amber); }
.fleet-score-crit { background: rgba(231,76,60,.15);   color: var(--red);   }
.summary-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.summary-table th { text-align: left; padding: 8px 12px; color: var(--t3); font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; border-bottom: 1px solid var(--border); }
.summary-table td { padding: 10px 12px; border-bottom: 1px solid var(--border); vertical-align: top; }
.summary-table tr:last-child td { border-bottom: none; }
.summary-table tr:hover td { background: var(--surface2); }
.cluster-name-cell { font-weight: 600; color: var(--t1); }
.cluster-dot { margin-right: 8px; vertical-align: middle; }
.rs-tag { font-size: 11px; color: var(--t3); margin-top: 3px; padding-left: 16px; }
.top-issue-cell { color: var(--t2); font-size: 12px; }
.sev-cell { font-size: 12px; font-weight: 600; white-space: nowrap; }
.view-link { color: var(--blue); text-decoration: none; font-weight: 600; white-space: nowrap; }
.view-link:hover { text-decoration: underline; }
.score-cell { font-family: var(--mono); font-weight: 700; font-size: 14px; white-space: nowrap; }
.score-unit { font-size: 11px; color: var(--t3); font-weight: 400; }
.score-ok   { color: var(--green); }
.score-warn { color: var(--amber); }
.score-crit { color: var(--red);   }
.n-actions-cell { color: var(--t2); font-size: 12px; }

@media (max-width: 820px) {
  .cluster-panel .sidebar { top: 0; height: auto; }
  .cluster-panel .section { scroll-margin-top: 24px; }
  .tab-identity { display: none; }
  .summary-panel { padding: 16px; }
}
"""

_SEV_DOT = {
    HealthSeverity.OK:       "tdot-ok",
    HealthSeverity.WARNING:  "tdot-warn",
    HealthSeverity.CRITICAL: "tdot-crit",
}

_FLEET_JS = """
// Injected by render_multi_html — array of {name, dotCls, sevLabel, sevColor}
// Index 0 is always the summary; clusters start at index 1.
var _clusterMeta = [];

function switchCluster(idx) {
  idx = parseInt(idx, 10);

  // Hide all panels
  document.querySelectorAll('.cluster-panel').forEach(function(el) { el.classList.remove('active'); });
  document.querySelector('.summary-panel') && document.querySelector('.summary-panel').classList.remove('active');
  document.querySelectorAll('.tab-btn').forEach(function(el) { el.classList.remove('active'); });

  if (idx === 0) {
    // Summary tab
    var sp = document.querySelector('.summary-panel');
    if (sp) sp.classList.add('active');
  } else {
    // Cluster tab (clusters are 1-indexed in the tab bar; data-cluster is 0-based)
    var panel = document.querySelector('.cluster-panel[data-cluster="' + (idx - 1) + '"]');
    if (panel) panel.classList.add('active');
  }

  var btns = document.querySelectorAll('.tab-btn');
  if (btns[idx]) btns[idx].classList.add('active');

  // Update identity label (right side of sticky tab bar)
  var meta = _clusterMeta[idx];
  if (meta) {
    var dot  = document.getElementById('tab-id-dot');
    var name = document.getElementById('tab-id-name');
    var sev  = document.getElementById('tab-id-sev');
    if (dot)  { dot.className = 'tab-dot ' + (meta.dotCls || ''); }
    if (name) { name.textContent = meta.name; }
    if (sev)  { sev.textContent = meta.sevLabel; sev.style.color = meta.sevColor || ''; }
  }

  // Sync dropdown if present (dropdown values are also 0-based where 0 = summary)
  var sel = document.querySelector('.cluster-select');
  if (sel) sel.value = idx;

  // Scroll to top of newly shown panel
  window.scrollTo({ top: 0 });
}

// Smooth scroll for nav links (skip if href is used as a switchCluster anchor)
document.addEventListener('click', function(e) {
  var a = e.target.closest('a[href^="#"]');
  if (!a) return;
  e.preventDefault();
  var target = document.querySelector(a.getAttribute('href'));
  if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
});
"""


def _prefix_ids(html: str, prefix: str) -> str:
    """Prefix all HTML id attributes and href anchors with a cluster-scoped prefix."""
    html = html.replace(' id="', f' id="{prefix}')
    html = html.replace('href="#', f'href="#{prefix}')
    return html


_SEV_COLOR = {
    HealthSeverity.OK:       "var(--green)",
    HealthSeverity.WARNING:  "var(--amber)",
    HealthSeverity.CRITICAL: "var(--red)",
}
_SEV_LABEL = {
    HealthSeverity.OK:       "Healthy",
    HealthSeverity.WARNING:  "Warning",
    HealthSeverity.CRITICAL: "Critical",
}

_LARGE_FLEET_THRESHOLD = 6  # clusters above this count use dropdown instead of tabs
_TIER_ORDER_MAP = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}


def _top_issue(cr) -> str:
    """Return a short description of the highest-consequence non-OK section."""
    best_section = None
    best_rank = 999
    for s in cr.sections:
        if s.severity.value == "ok":
            continue
        tier = SECTION_TIER.get(s.name, "P4")
        rank = _TIER_ORDER_MAP.get(tier, 4)
        if rank < best_rank:
            best_rank = rank
            best_section = s
    if best_section is None:
        return "All sections healthy"
    tier = SECTION_TIER.get(best_section.name, "P4")
    label = _TIER_LABEL.get(tier, tier)
    return f"{best_section.name} ({tier} – {label})"


def _score_css(score: int) -> str:
    if score >= 80:
        return "score-ok"
    if score >= 60:
        return "score-warn"
    return "score-crit"


def _fleet_score_css(score: int) -> str:
    if score >= 80:
        return "fleet-score-ok"
    if score >= 60:
        return "fleet-score-warn"
    return "fleet-score-crit"


def _rs_name(cluster_uri: str) -> str:
    """Extract the replicaSet name from a MongoDB URI, or empty string if absent."""
    from urllib.parse import urlparse, parse_qs
    try:
        qs = parse_qs(urlparse(cluster_uri).query)
        return qs.get("replicaSet", [""])[0]
    except Exception:
        return ""


def _build_summary_panel(report: MultiClusterReport, labels: list, ts: str) -> str:
    """Build the fleet summary panel (BL-091) — default first tab."""
    scores = [_health_score(cr) for cr in report.clusters]

    fleet_sub = (
        f"{report.cluster_count} cluster{'s' if report.cluster_count != 1 else ''}"
        f" · Report generated at {ts}"
    )

    # Rows sorted by score ascending (worst first)
    rows_data = sorted(
        zip(range(len(report.clusters)), report.clusters, labels, scores),
        key=lambda x: x[3],
    )

    rows_html = ""
    for orig_idx, cr, label, score in rows_data:
        tab_idx   = orig_idx + 1  # summary=0, cluster[0]=1, ...
        sev_dot   = _SEV_DOT[cr.overall_severity]
        sev_color = _SEV_COLOR[cr.overall_severity]
        sev_label = _SEV_LABEL[cr.overall_severity]
        top       = _top_issue(cr)
        n_recs    = len(cr.recommendations)
        score_cls = _score_css(score)
        rs        = _rs_name(cr.cluster_uri)
        # Strip "(rs_name)" suffix from label when we show it separately below
        display_label = label
        if rs and display_label.endswith(f"({rs})"):
            display_label = display_label[:-(len(rs) + 3)].strip()
        rs_tag = f'<div class="rs-tag">Replica set: {rs}</div>' if rs else ""
        rows_html += (
            f'<tr onclick="switchCluster({tab_idx})" style="cursor:pointer">'
            f'<td class="cluster-name-cell">'
            f'<span class="tab-dot {sev_dot} cluster-dot"></span>{display_label}'
            f'{rs_tag}'
            f'</td>'
            f'<td class="score-cell {score_cls}">{score}<span class="score-unit"> /100</span></td>'
            f'<td class="sev-cell" style="color:{sev_color}">{sev_label}</td>'
            f'<td class="top-issue-cell">{top}</td>'
            f'<td class="n-actions-cell">{n_recs}</td>'
            f'<td><a class="view-link" href="#" onclick="switchCluster({tab_idx}); return false;">View →</a></td>'
            f'</tr>'
        )

    return (
        f'<div class="summary-panel active">'
        f'<div class="summary-head">'
        f'<div class="summary-title">MongoDB Fleet Health Report</div>'
        f'<div class="summary-sub">{fleet_sub}</div>'
        f'</div>'
        f'<table class="summary-table">'
        f'<thead><tr>'
        f'<th>Cluster</th><th>Score</th><th>Severity</th><th>Top Issue</th><th>Actions</th><th></th>'
        f'</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table>'
        f'</div>'
    )


def render_multi_html(report: MultiClusterReport) -> str:
    """Render a MultiClusterReport as a self-contained tabbed HTML page."""
    ts = report.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
    n  = report.cluster_count
    large_fleet = n > _LARGE_FLEET_THRESHOLD

    # ── Cluster labels ───────────────────────────────────────────────────────
    labels = [
        cr.cluster_name or (cr.cluster_uri.split("@")[-1] if "@" in cr.cluster_uri else cr.cluster_uri)
        for cr in report.clusters
    ]

    # ── Tab bar: Summary (index 0) + cluster tabs (1, 2, ...) ───────────────
    summary_btn = '<button class="tab-btn active" onclick="switchCluster(0)">Fleet Summary</button>'

    if large_fleet:
        options = '<option value="0" selected>Fleet Summary</option>'
        options += "".join(
            f'<option value="{i + 1}">{labels[i]}</option>'
            for i in range(len(report.clusters))
        )
        nav_html = (
            f'<div class="cluster-select-wrap">'
            f'{summary_btn}'
            f'<select class="cluster-select" onchange="switchCluster(this.value)">{options}</select>'
            f'</div>'
        )
    else:
        tab_buttons = [summary_btn]
        for i, cr in enumerate(report.clusters):
            dot_cls = _SEV_DOT[cr.overall_severity]
            tab_buttons.append(
                f'<button class="tab-btn" onclick="switchCluster({i + 1})">'
                f'<span class="tab-dot {dot_cls}"></span>{labels[i]}'
                f'</button>'
            )
        nav_html = "".join(tab_buttons)

    # Identity label — starts as "Fleet Summary" (BL-079)
    identity_html = (
        f'<div class="tab-spacer"></div>'
        f'<div class="tab-identity">'
        f'<span class="tab-id-label">Viewing</span>'
        f'<span class="tab-dot" id="tab-id-dot"></span>'
        f'<span class="tab-id-name" id="tab-id-name">Fleet Summary</span>'
        f'<span style="color:var(--t2); font-size:11px; font-family:var(--mono);" id="tab-id-sev"></span>'
        f'</div>'
    )

    tabs_html = f'<div class="cluster-tabs">{nav_html}{identity_html}</div>'

    # ── JS metadata — index 0 = summary, 1..n = clusters ────────────────────
    meta_entries = ['{name:"Fleet Summary",dotCls:"",sevLabel:"",sevColor:"var(--t2)"}']
    for i, cr in enumerate(report.clusters):
        meta_entries.append(
            f'{{name:{repr(labels[i])},dotCls:{repr(_SEV_DOT[cr.overall_severity])},'
            f'sevLabel:{repr(_SEV_LABEL[cr.overall_severity])},sevColor:{repr(_SEV_COLOR[cr.overall_severity])}}}'
        )
    cluster_meta_js = f"_clusterMeta = [{','.join(meta_entries)}];"

    # ── Summary panel (BL-091) ───────────────────────────────────────────────
    summary_panel_html = _build_summary_panel(report, labels, ts)

    # ── Per-cluster panels (sidebar + pane) ──────────────────────────────────
    panels_html: list[str] = []

    for i, cr in enumerate(report.clusters):
        pfx    = f"c{i}-"
        score  = _health_score(cr)
        label  = labels[i]
        n_recs = len(cr.recommendations)

        # Strip "(rsName)" from display label; show RS separately
        rs = _rs_name(cr.cluster_uri)
        display_label = label
        if rs and display_label.endswith(f"({rs})"):
            display_label = display_label[:-(len(rs) + 3)].strip()
        rs_header_line = (
            f'<div class="report-sub" style="margin-top:2px">Replica set: {rs}</div>'
            if rs else ""
        )

        raw_sidebar = _sidebar(cr, score)
        raw_sidebar = raw_sidebar.replace('href="#', f'href="#{pfx}')

        content_html = _build_content(cr)
        content_html = _prefix_ids(content_html, pfx)
        recs_html    = _recommendations_html(cr)
        recs_html    = _prefix_ids(recs_html, pfx)
        status_html  = _status_bar(cr)
        oh_summary   = _prefix_ids(_overall_health_summary(cr), pfx)
        explainer    = _prefix_ids(_rating_explainer(cr), pfx)

        pane = (
            f'<main class="main">'
            f'<div class="report-header">'
            f'<div class="report-title">MongoDB cluster health report</div>'
            f'<div class="report-cluster">{display_label}</div>'
            f'{rs_header_line}'
            f'<div class="report-sub" style="margin-top:4px">Report generated at {ts} &middot; Run&thinsp;{report.run_id} &middot; {len(cr.sections)} sections &middot; '
            f'{n_recs} recommendation{"s" if n_recs != 1 else ""}</div>'
            f'</div>'
            f'{oh_summary}'
            f'{explainer}'
            f'{recs_html}'
            f'{status_html}'
            f'{content_html}'
            f'<div class="report-footer">mongodb-dba-agent · {display_label} · {ts}</div>'
            f'</main>'
        )

        panels_html.append(
            f'<div class="cluster-panel" data-cluster="{i}">'
            f'{raw_sidebar}'
            f'{pane}'
            f'</div>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MongoDB fleet health — {n} cluster{"s" if n != 1 else ""}</title>
  <style>{_CSS}{_TAB_CSS}</style>
</head>
<body>
{tabs_html}
{summary_panel_html}
{"".join(panels_html)}
<script>{_FLEET_JS}{cluster_meta_js}</script>
</body>
</html>"""
