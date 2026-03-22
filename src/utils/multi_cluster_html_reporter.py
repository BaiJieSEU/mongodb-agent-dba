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

@media (max-width: 820px) {
  .cluster-panel .sidebar { top: 0; height: auto; }
  .cluster-panel .section { scroll-margin-top: 24px; }
  .tab-identity { display: none; }
}
"""

_SEV_DOT = {
    HealthSeverity.OK:       "tdot-ok",
    HealthSeverity.WARNING:  "tdot-warn",
    HealthSeverity.CRITICAL: "tdot-crit",
}

_FLEET_JS = """
// Injected by render_multi_html — array of {name, dotCls, sevLabel, sevColor}
var _clusterMeta = [];

function switchCluster(idx) {
  idx = parseInt(idx, 10);
  document.querySelectorAll('.cluster-panel').forEach(function(el) { el.classList.remove('active'); });
  document.querySelectorAll('.tab-btn').forEach(function(el) { el.classList.remove('active'); });

  var panel = document.querySelector('.cluster-panel[data-cluster="' + idx + '"]');
  if (panel) panel.classList.add('active');
  var btns = document.querySelectorAll('.tab-btn');
  if (btns[idx]) btns[idx].classList.add('active');

  // Update identity label (right side of sticky tab bar)
  var meta = _clusterMeta[idx];
  if (meta) {
    var dot  = document.getElementById('tab-id-dot');
    var name = document.getElementById('tab-id-name');
    var sev  = document.getElementById('tab-id-sev');
    if (dot)  { dot.className = 'tab-dot ' + meta.dotCls; }
    if (name) { name.textContent = meta.name; }
    if (sev)  { sev.textContent = meta.sevLabel; sev.style.color = meta.sevColor; }
  }

  // Sync dropdown if present
  var sel = document.querySelector('.cluster-select');
  if (sel) sel.value = idx;

  // Scroll to top of newly shown panel
  window.scrollTo({ top: 0 });
}

// Smooth scroll for nav links
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


def render_multi_html(report: MultiClusterReport) -> str:
    """Render a MultiClusterReport as a self-contained tabbed HTML page."""
    ts = report.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
    n  = report.cluster_count
    large_fleet = n > _LARGE_FLEET_THRESHOLD

    # ── Cluster labels + meta ────────────────────────────────────────────────
    labels = [
        cr.cluster_name or (cr.cluster_uri.split("@")[-1] if "@" in cr.cluster_uri else cr.cluster_uri)
        for cr in report.clusters
    ]

    # ── Tab bar or dropdown (BL-078) ─────────────────────────────────────────
    first_dot  = _SEV_DOT[report.clusters[0].overall_severity]
    first_name = labels[0]
    first_sev  = _SEV_LABEL[report.clusters[0].overall_severity]
    first_col  = _SEV_COLOR[report.clusters[0].overall_severity]

    if large_fleet:
        # Dropdown navigation for large fleets
        options = "".join(
            f'<option value="{i}"{"  selected" if i == 0 else ""}>{labels[i]}</option>'
            for i, cr in enumerate(report.clusters)
        )
        nav_html = (
            f'<div class="cluster-select-wrap">'
            f'<span class="tab-dot {first_dot}" id="select-dot"></span>'
            f'<select class="cluster-select" onchange="switchCluster(this.value)">{options}</select>'
            f'</div>'
        )
    else:
        # Horizontal tab buttons for small fleets
        tab_buttons = []
        for i, cr in enumerate(report.clusters):
            dot_cls = _SEV_DOT[cr.overall_severity]
            active  = " active" if i == 0 else ""
            tab_buttons.append(
                f'<button class="tab-btn{active}" onclick="switchCluster({i})">'
                f'<span class="tab-dot {dot_cls}"></span>{labels[i]}'
                f'</button>'
            )
        nav_html = "".join(tab_buttons)

    # Identity label always shown on the right (BL-079)
    identity_html = (
        f'<div class="tab-spacer"></div>'
        f'<div class="tab-identity">'
        f'<span class="tab-id-label">Viewing</span>'
        f'<span class="tab-dot {first_dot}" id="tab-id-dot"></span>'
        f'<span class="tab-id-name" id="tab-id-name">{first_name}</span>'
        f'<span style="color:{first_col}; font-size:11px; font-family:var(--mono);" id="tab-id-sev">{first_sev}</span>'
        f'</div>'
    )

    tabs_html = f'<div class="cluster-tabs">{nav_html}{identity_html}</div>'

    # ── JS cluster metadata array (injected for identity updates) ───────────
    meta_entries = []
    for i, cr in enumerate(report.clusters):
        meta_entries.append(
            f'{{name:{repr(labels[i])},dotCls:{repr(_SEV_DOT[cr.overall_severity])},'
            f'sevLabel:{repr(_SEV_LABEL[cr.overall_severity])},sevColor:{repr(_SEV_COLOR[cr.overall_severity])}}}'
        )
    cluster_meta_js = f"_clusterMeta = [{','.join(meta_entries)}];"

    # ── Per-cluster panels (sidebar + pane) ──────────────────────────────────
    panels_html: list[str] = []

    for i, cr in enumerate(report.clusters):
        pfx    = f"c{i}-"
        score  = _health_score(cr)
        active = " active" if i == 0 else ""
        label  = labels[i]
        n_recs = len(cr.recommendations)

        # Sidebar — prefix href anchors to match the prefixed section IDs
        raw_sidebar = _sidebar(cr, score)
        raw_sidebar = raw_sidebar.replace('href="#', f'href="#{pfx}')

        # Main pane — prefix section IDs to avoid duplicate-id collisions
        content_html = _build_content(cr)
        content_html = _prefix_ids(content_html, pfx)
        recs_html    = _recommendations_html(cr.recommendations)
        recs_html    = _prefix_ids(recs_html, pfx)
        status_html   = _status_bar(cr)
        oh_summary    = _prefix_ids(_overall_health_summary(cr), pfx)   # BL-080
        explainer     = _prefix_ids(_rating_explainer(cr), pfx)          # BL-080

        pane = (
            f'<main class="main">'
            f'<div class="report-header">'
            f'<div class="report-title">MongoDB cluster health report</div>'
            f'<div class="report-cluster">{label}</div>'
            f'<div class="report-sub">{ts} &middot; Run&thinsp;{report.run_id} &middot; {len(cr.sections)} sections &middot; '
            f'{n_recs} recommendation{"s" if n_recs != 1 else ""}</div>'
            f'</div>'
            f'{oh_summary}'
            f'{explainer}'
            f'{status_html}'
            f'{content_html}'
            f'<hr class="divider">'
            f'{recs_html}'
            f'<div class="report-footer">mongodb-dba-agent · {label} · {ts}</div>'
            f'</main>'
        )

        panels_html.append(
            f'<div class="cluster-panel{active}" data-cluster="{i}">'
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
{"".join(panels_html)}
<script>{_FLEET_JS}{cluster_meta_js}</script>
</body>
</html>"""
