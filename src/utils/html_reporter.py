"""Self-contained HTML report renderer for HealthCheckReport (BL-060) — v5.

UX/UI improvements over v4:
  - Typography: section headings 15px/600, findings 13px, indent 12px
  - Amber corrected to #f59e0b (was too brownish at #e09b3a)
  - Fluid metric grid: auto-fill minmax(155px) — no more 4-col cramping on §Operations
  - Section cards get coloured left-border accent for WARNING / CRITICAL
  - LLM recommendations distinguished with blue AI badge
  - Recommendations layout: evidence on its own line
  - word-break: overflow-wrap on code blocks (no mid-word breaks)
  - Empty metric-sub divs suppressed via :empty CSS
  - Main content area widened to 1024px
  - Score ring number 14px (was 12px — illegible)
  - Metric breach detection handles below-threshold signals (cache hit ratio, etc.)
"""
from __future__ import annotations

import math
from models.health_check_report import (
    HealthCheckReport, HealthSeverity, ReportSection, worst_severity,
)

# ── severity maps ──────────────────────────────────────────────────────────────

_COLOR = {
    HealthSeverity.OK:       "var(--green)",
    HealthSeverity.WARNING:  "var(--amber)",
    HealthSeverity.CRITICAL: "var(--red)",
}
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
_DOT = {
    HealthSeverity.OK:       "d-green",
    HealthSeverity.WARNING:  "d-amber",
    HealthSeverity.CRITICAL: "d-red",
}
_ALERT = {
    HealthSeverity.OK:       "alert-green",
    HealthSeverity.WARNING:  "alert-amber",
    HealthSeverity.CRITICAL: "alert-red",
}
_STATUS_COLOR = {
    HealthSeverity.OK:       "c-green",
    HealthSeverity.WARNING:  "c-amber",
    HealthSeverity.CRITICAL: "c-red",
}
_REC_PRI = {"P0": "rp0", "P1": "rp1", "P2": "rp2", "P3": "rp3", "P4": "rp4"}
_REC_LBL = {"P0": "P0",  "P1": "P1",  "P2": "P2",  "P3": "P3",  "P4": "P4"}
_SECTION_BORDER = {
    HealthSeverity.OK:       "",
    HealthSeverity.WARNING:  "s-warn",
    HealthSeverity.CRITICAL: "s-crit",
}


# ── section routing ────────────────────────────────────────────────────────────

_SECTION_META: dict[str, tuple[str, str]] = {
    "Cluster Overview":          ("sec-overview",       "Cluster status"),
    "Server Health":             ("sec-server",         "Server health"),
    "Replication Health":        ("sec-replication",    "Replication health"),
    "Storage & Capacity":        ("sec-storage",        "Storage"),
    "Query Performance":         ("sec-queries",        "Slow query analysis"),
    "Missing Indexes":           ("sec-indexes",        "Missing indexes"),
    "Unused Indexes":            ("sec-indexes-unused", "Unused indexes"),
    "Operations":                ("sec-ops",            "Operations"),
    "Connections & Concurrency": ("sec-connections",    "Connections & concurrency"),
    "Infrastructure":            ("sec-infra",          "Infrastructure"),
}

_NAV_GROUPS: list[tuple[str, list[tuple[str, str, str | None]]]] = [
    ("Action Plan", [
        ("Recommendations", "recommendations", None),
    ]),
    ("Summary", [
        ("Cluster overview", "sec-overview", "Cluster Overview"),
        ("Active alerts",    "alerts",       None),
    ]),
    ("Availability", [
        ("Replication",               "sec-replication", "Replication Health"),
        ("Connections & concurrency", "sec-connections", "Connections & Concurrency"),
    ]),
    ("Resource Health", [
        ("Server health",  "sec-server",  "Server Health"),
        ("Storage",        "sec-storage", "Storage & Capacity"),
        ("Infrastructure", "sec-infra",   "Infrastructure"),
    ]),
    ("Performance", [
        ("Query performance", "sec-queries", "Query Performance"),
        ("Operations",        "sec-ops",     "Operations"),
    ]),
    ("Index Advisory", [
        ("Missing indexes", "sec-indexes",        "Missing Indexes"),
        ("Unused indexes",  "sec-indexes-unused", "Unused Indexes"),
    ]),
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
  --font: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --mono: ui-monospace, 'SF Mono', 'Cascadia Code', 'Fira Code', monospace;

  --bg:        #0e1117;
  --surface:   #161b25;
  --surface2:  #1c2333;
  --border:    rgba(255,255,255,0.09);
  --border-em: rgba(255,255,255,0.18);

  --t1: #f0f4fa;
  --t2: #a8b5c8;
  --t3: #8294b2;   /* was #6b7a94 — raised for WCAG AA contrast */

  --red:   #f87171;
  --amber: #f59e0b;
  --green: #34d399;
  --blue:  #60a5fa;

  --red-bg:    rgba(248,113,113,0.09);
  --amber-bg:  rgba(245,158,11,0.09);
  --green-bg:  rgba(52,211,153,0.09);
  --blue-bg:   rgba(96,165,250,0.09);

  --red-border:   rgba(248,113,113,0.30);
  --amber-border: rgba(245,158,11,0.30);
  --green-border: rgba(52,211,153,0.30);
  --blue-border:  rgba(96,165,250,0.30);
}

body {
  background: var(--bg);
  color: var(--t1);
  font-family: var(--font);
  font-size: 13px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* ── Layout ── */
.layout { display: flex; min-height: 100vh; }

/* ── Sticky identity bar (BL-079) ── */
.sticky-bar {
  position: sticky; top: 0; z-index: 100;
  background: var(--surface); border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 10px;
  padding: 0 20px; height: 44px; flex-shrink: 0;
}
.sticky-cluster { font-size: 13px; font-weight: 600; color: var(--t1); }
.sticky-sep { color: var(--t3); font-size: 12px; }
.sticky-sev { font-size: 12px; font-family: var(--mono); font-weight: 500; }
.sticky-ts { font-size: 12px; color: var(--t3); font-family: var(--mono); margin-left: auto; }

/* ── Sidebar ── */
.sidebar {
  width: 224px; min-width: 224px;
  background: var(--surface);
  border-right: 1px solid var(--border);
  padding: 24px 0;
  position: sticky; top: 44px;
  height: calc(100vh - 44px); overflow-y: auto;
  display: flex; flex-direction: column;
}
.sidebar-top {
  padding: 0 18px 20px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 14px;
}
.sidebar-cluster { font-size: 13px; font-weight: 600; color: var(--t1); margin-bottom: 3px; }
.sidebar-meta { font-size: 12px; color: var(--t3); font-family: var(--mono); }

.nav-group { padding: 0 10px; margin-bottom: 6px; }
.nav-group-label {
  font-size: 11px; color: var(--t3);
  padding: 6px 8px 3px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.nav-item {
  display: flex; align-items: center; gap: 9px;
  padding: 6px 8px; border-radius: 5px;
  font-size: 13px; color: var(--t2);
  text-decoration: none;
  transition: background 0.12s, color 0.12s;
}
.nav-item:hover  { background: var(--surface2); color: var(--t1); }
.nav-item.active { background: rgba(96,165,250,0.10); color: var(--blue); }

.nav-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.d-red   { background: var(--red); }
.d-amber { background: var(--amber); }
.d-green { background: var(--green); }
.d-gray  { background: var(--t3); }

.sidebar-score {
  margin-top: auto;
  padding: 16px 18px 0;
  border-top: 1px solid var(--border);
  display: flex; align-items: center; gap: 12px;
}
.score-ring { position: relative; width: 48px; height: 48px; flex-shrink: 0; }
.score-ring svg { transform: rotate(-90deg); }
.score-num {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 600;
}
.score-info   { font-size: 12px; color: var(--t2); font-weight: 500; }
.score-status { font-size: 12px; color: var(--t3); margin-top: 2px; }

/* ── Main ── */
.main { flex: 1; padding: 36px 48px; max-width: 1040px; }

/* ── Report header ── */
.report-header {
  margin-bottom: 28px; padding-bottom: 22px; border-bottom: 1px solid var(--border);
}
.report-title { font-size: 18px; font-weight: 600; color: var(--t1); margin-bottom: 3px; }
.report-cluster { font-size: 14px; font-weight: 600; color: var(--t2); margin-bottom: 6px; }
.report-sub   { font-size: 12px; color: var(--t3); }

/* ── Overall health summary (BL-080) ── */
.overall-health {
  display: flex; align-items: center; justify-content: space-between;
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 8px; padding: 16px 20px; margin-bottom: 10px;
}
.oh-left  { display: flex; align-items: center; gap: 12px; }
.oh-label { font-size: 12px; color: var(--t3); font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }
.oh-score { font-size: 24px; font-weight: 700; font-family: var(--mono); line-height: 1; }
.oh-denom { font-size: 12px; color: var(--t3); font-weight: 400; }

/* ── Status bar — gap separator trick ── */
.status-bar {
  display: grid;
  gap: 1px; background: var(--border);
  border: 1px solid var(--border); border-radius: 8px;
  overflow: hidden; margin-bottom: 32px;
}
.status-cell { background: var(--surface); padding: 14px 16px; text-align: center; }
.status-val  { font-size: 18px; font-weight: 600; font-family: var(--mono); margin-bottom: 4px; }
.status-lbl  { font-size: 12px; color: var(--t2); letter-spacing: 0.01em; }
.c-red   { color: var(--red); }
.c-amber { color: var(--amber); }
.c-green { color: var(--green); }
.c-dim   { color: var(--t1); }

/* ── Section card ── */
.section {
  scroll-margin-top: 68px;
  border-left: 3px solid transparent;
  padding-left: 14px;
  margin-left: -14px;
  margin-bottom: 4px;
}
.section.s-warn { border-left-color: var(--amber); }
.section.s-crit { border-left-color: var(--red); }

.section-hd {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 14px;
}
.section-title { font-size: 15px; font-weight: 600; color: var(--t1); }

.tag { font-size: 12px; padding: 2px 8px; border-radius: 4px; font-family: var(--mono); font-weight: 500; }
.tag-red   { background: var(--red-bg);   color: var(--red);   border: 1px solid var(--red-border); }
.tag-amber { background: var(--amber-bg); color: var(--amber); border: 1px solid var(--amber-border); }
.tag-green { background: var(--green-bg); color: var(--green); border: 1px solid var(--green-border); }
.tag-gray  { background: var(--surface2); color: var(--t3);   border: 1px solid var(--border); }

.divider { border: none; border-top: 1px solid var(--border); margin: 28px 0; }

/* ── Content group header ── */
.content-group {
  display: flex; align-items: center; gap: 12px;
  margin: 36px 0 20px;
}
.content-group-label {
  font-size: 11px; font-weight: 600; letter-spacing: 0.08em;
  text-transform: uppercase; color: var(--t3);
  white-space: nowrap;
}
.content-group-rule {
  flex: 1; height: 1px; background: var(--border);
}

/* ── Alert — left-border accent ── */
.alert {
  border-radius: 6px; padding: 12px 16px;
  margin-bottom: 8px; border-left: 3px solid;
}
.alert-red   { background: var(--red-bg);   border-color: var(--red); }
.alert-amber { background: var(--amber-bg); border-color: var(--amber); }
.alert-green { background: var(--green-bg); border-color: var(--green); }
.alert-title { font-size: 13px; font-weight: 600; margin-bottom: 4px; }
.alert-red   .alert-title { color: var(--red); }
.alert-amber .alert-title { color: var(--amber); }
.alert-green .alert-title { color: var(--green); }
.alert-body { font-size: 13px; color: var(--t2); line-height: 1.6; }
code { font-family: var(--mono); font-size: 12px; color: var(--t2); }

/* ── Findings list ── */
.findings { list-style: none; font-size: 13px; line-height: 1.75; margin-top: 10px; }
.findings li { padding: 1px 0; color: var(--t2); }
.findings li::before { content: "· "; color: var(--t3); }
.findings li.lead { color: var(--t1); font-weight: 500; }
.findings li.lead::before { content: "· "; color: var(--t3); }
.findings li.indent {
  padding-left: 1.4rem; color: var(--t3);
  font-family: var(--mono); font-size: 12px; line-height: 1.6;
}
.findings li.indent::before { content: ""; }

/* ── Metric grid ── */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(155px, 1fr));
  gap: 8px; margin-bottom: 16px;
}
.metric {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 7px; padding: 14px 16px;
  transition: border-color 0.15s;
}
.metric.m-crit { border-color: var(--red-border);   background: var(--red-bg); }
.metric.m-warn { border-color: var(--amber-border); background: var(--amber-bg); }
.metric-lbl { font-size: 12px; color: var(--t2); margin-bottom: 6px; letter-spacing: 0.01em; display: flex; align-items: center; gap: 4px; }
.metric-val { font-size: 20px; font-weight: 600; font-family: var(--mono); margin-bottom: 2px; line-height: 1.1; }
.metric-sub { font-size: 12px; color: var(--t3); }
.metric-sub:empty { display: none; }
.metric-limit { font-size: 12px; color: var(--t3); margin-top: 4px; border-top: 1px solid var(--border); padding-top: 4px; }

/* ── Metric tooltip ── */
.minfo { position: relative; display: inline-flex; align-items: center; cursor: default; }
.minfo-icon {
  font-size: 11px; color: var(--t3); line-height: 1;
  border: 1px solid var(--border); border-radius: 50%;
  width: 14px; height: 14px; display: inline-flex; align-items: center; justify-content: center;
  flex-shrink: 0; user-select: none;
  transition: color 0.15s, border-color 0.15s;
}
.minfo:hover .minfo-icon, .minfo:focus-within .minfo-icon {
  color: var(--blue); border-color: var(--blue);
}
.minfo-tip {
  visibility: hidden; opacity: 0;
  position: absolute; bottom: calc(100% + 8px); left: 50%; transform: translateX(-50%);
  background: #1e2a3a; border: 1px solid var(--blue-border);
  color: var(--t1); font-size: 12px; line-height: 1.5;
  padding: 8px 12px; border-radius: 6px;
  width: 260px; white-space: normal; z-index: 100;
  box-shadow: 0 4px 16px rgba(0,0,0,0.4);
  pointer-events: none;
  transition: opacity 0.15s;
}
.minfo-tip::after {
  content: ""; position: absolute; top: 100%; left: 50%; transform: translateX(-50%);
  border: 5px solid transparent; border-top-color: var(--blue-border);
}
.minfo:hover .minfo-tip, .minfo:focus-within .minfo-tip {
  visibility: visible; opacity: 1;
}
/* Mobile tap: toggle via hidden checkbox trick */
.minfo-chk { position: absolute; opacity: 0; width: 0; height: 0; }
.minfo-chk:checked ~ .minfo-tip { visibility: visible; opacity: 1; }

/* ── Placeholder ── */
.placeholder {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 7px; padding: 16px 18px;
}
.placeholder-title { font-size: 12px; color: var(--t3); margin-bottom: 8px; font-weight: 500; }
.placeholder-list  { list-style: none; margin-bottom: 10px; }
.placeholder-list li { font-size: 13px; color: var(--t2); padding: 2px 0; }
.placeholder-list li::before { content: "· "; color: var(--t3); }
.placeholder-ref { font-size: 11px; color: var(--t3); font-family: var(--mono); }
.placeholder-ref code { color: var(--t2); background: var(--surface); padding: 1px 6px; border-radius: 3px; }

/* ── Recommendations ── */
.rec-list { list-style: none; }
.rec-item {
  display: flex; gap: 12px;
  padding: 14px 0; border-bottom: 1px solid var(--border);
  align-items: flex-start;
}
.rec-item:last-child { border-bottom: none; }
.rec-p {
  font-size: 12px; font-family: var(--mono); font-weight: 600;
  padding: 3px 7px; border-radius: 4px; flex-shrink: 0; margin-top: 2px;
}
.rp0 { background: var(--red-bg);   color: var(--red);   border: 1px solid var(--red-border); }
.rp1 { background: var(--amber-bg); color: var(--amber); border: 1px solid var(--amber-border); }
.rp2 { background: var(--blue-bg);  color: var(--blue);  border: 1px solid var(--blue-border); }
.rp3 { background: var(--green-bg); color: var(--green); border: 1px solid var(--green-border); }
.rp4 { background: var(--surface2); color: var(--t3);   border: 1px solid var(--border); }
.rec-body  { font-size: 13px; color: var(--t2); line-height: 1.6; flex: 1; min-width: 0; }
.rec-collection { font-size: 14px; font-weight: 600; color: var(--t1); margin-bottom: 6px; }
.rec-action {
  font-family: var(--mono); font-size: 12px; color: var(--t2);
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 5px; padding: 6px 10px;
  display: block; margin: 6px 0 8px;
  overflow-wrap: break-word; word-break: break-word;
}
.rec-evidence { font-size: 12px; color: var(--t2); line-height: 1.6; margin-bottom: 6px; }
.rec-meta { display: flex; align-items: center; gap: 8px; margin-top: 2px; }
.conf-high { color: var(--green); font-size: 12px; font-family: var(--mono); }
.conf-med  { color: var(--amber); font-size: 12px; font-family: var(--mono); }
.conf-low  { color: var(--t3);   font-size: 12px; font-family: var(--mono); }
.conf-llm  { color: var(--blue); font-size: 12px; font-family: var(--mono); }
.badge-ai {
  font-size: 11px; font-family: var(--mono); font-weight: 600;
  padding: 2px 6px; border-radius: 3px;
  background: var(--blue-bg); color: var(--blue); border: 1px solid var(--blue-border);
}
.badge-rule {
  font-size: 11px; font-family: var(--mono); font-weight: 600;
  padding: 2px 6px; border-radius: 3px;
  background: var(--surface2); color: var(--t3); border: 1px solid var(--border);
}
.no-recs { font-size: 13px; color: var(--t3); padding: 16px 0; }

/* ── Health summary ── */
.health-summary {
  background: var(--surface2); border: 1px solid var(--border);
  border-left: 3px solid var(--blue); border-radius: 6px;
  padding: 14px 16px; margin-bottom: 18px;
}
.health-summary-label {
  display: block; font-size: 11px; font-family: var(--mono); font-weight: 600;
  color: var(--blue); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 8px;
}
.health-summary-text {
  font-size: 14px; color: var(--t1); line-height: 1.7; margin: 0;
}

/* ── Call-to-action table ── */
.cta-table-wrap { overflow-x: auto; }
.cta-table {
  width: 100%; border-collapse: collapse; font-size: 13px;
}
.cta-table thead th {
  font-size: 11px; font-family: var(--mono); font-weight: 600;
  color: var(--t3); text-transform: uppercase; letter-spacing: .05em;
  padding: 6px 10px; border-bottom: 1px solid var(--border);
  text-align: left; white-space: nowrap;
}
.cta-table tbody tr { border-bottom: 1px solid var(--border); }
.cta-table tbody tr:last-child { border-bottom: none; }
.cta-table tbody tr:hover { background: var(--surface2); }
.cta-table td { padding: 10px; vertical-align: top; }
.cta-table .rec-target {
  font-size: 13px; font-weight: 600; color: var(--t1); white-space: nowrap;
}
.cta-table .rec-action {
  font-family: var(--mono); font-size: 12px; color: var(--t2);
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 4px; padding: 4px 8px; display: inline-block;
  overflow-wrap: break-word; word-break: break-word; max-width: 360px;
}
.cta-table .rec-evidence-cell {
  font-size: 12px; color: var(--t3); line-height: 1.5; max-width: 260px;
}

/* ── Footer ── */
.report-footer {
  padding: 20px 0 8px; text-align: center;
  font-size: 12px; color: var(--t3);
  border-top: 1px solid var(--border);
  margin-top: 8px; font-family: var(--mono);
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-thumb { background: var(--border-em); border-radius: 3px; }

/* ── Rating explainer (BL-080) ── */
.rating-info {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 6px; padding: 8px 14px; margin-bottom: 24px;
}
.rating-info > summary {
  cursor: pointer; color: var(--t3); font-size: 11px;
  letter-spacing: 0.02em; user-select: none; list-style: none;
}
.rating-info > summary::-webkit-details-marker { display: none; }
.rating-info > summary::before { content: "▶  "; font-size: 9px; }
.rating-info[open] > summary::before { content: "▼  "; }
.rating-info > summary:hover { color: var(--t2); }
.rating-body {
  margin-top: 10px; display: flex; flex-direction: column; gap: 6px;
  color: var(--t2); font-size: 12px; line-height: 1.6;
}
.rating-body strong { color: var(--t1); }
.rating-formula {
  font-family: var(--mono); font-size: 11px; color: var(--t3);
  background: var(--surface); padding: 4px 10px; border-radius: 4px; margin-top: 2px;
}

/* ── Responsive ── */
@media (max-width: 820px) {
  .layout { flex-direction: column; }
  .sidebar { width: 100%; height: auto; position: relative; top: 0; overflow: visible; }
  .main { padding: 20px 16px; max-width: none; }
  .metric-grid { grid-template-columns: repeat(2, 1fr); }
  .overall-health { flex-direction: column; align-items: flex-start; gap: 8px; }
  .section { scroll-margin-top: 24px; }
}
"""


# ── helpers ────────────────────────────────────────────────────────────────────

# Consequence-tier mapping: each section → ticket priority (P0 = highest risk)
# P0 Data Safety / Availability  → cluster going down, failover fails, data loss
# P1 Outage                      → writes fail, node down, storage exhausted
# P2 Operational                 → resource pressure, degrading toward outage
# P3 Performance                 → slow but cluster stays up
# P4 Observability               → informational only
SECTION_TIER: dict[str, str] = {
    "Cluster Overview":          "P4",
    "Replication Health":        "P0",
    "Server Health":             "P1",
    "Storage & Capacity":        "P1",
    "Operations":                "P2",
    "Connections & Concurrency": "P2",
    "Infrastructure":            "P2",
    "Query Performance":         "P3",
    "Missing Indexes":           "P3",
    "Unused Indexes":            "P4",
}

# Penalty per tier, applied once per tier (worst severity wins within a tier)
_TIER_PENALTY: dict[str, dict[str, int]] = {
    "P0": {"critical": 50, "warning": 20},
    "P1": {"critical": 40, "warning": 15},
    "P2": {"critical": 25, "warning": 10},
    "P3": {"critical": 15, "warning":  5},
    "P4": {"critical":  5, "warning":  2},
}

_TIER_LABEL: dict[str, str] = {
    "P0": "Data Loss",
    "P1": "Outage",
    "P2": "Degraded",
    "P3": "Slow",
    "P4": "Observation",
}


def _health_score(report: HealthCheckReport) -> int:
    """Consequence-tier penalty score (0–100).

    Each section is assigned a ticket tier (P0–P4). One penalty is applied per tier
    based on the worst severity present in that tier. Lower-consequence issues cost
    fewer points, so a slow-query-only cluster still scores high while a replication
    failure or disk-full drives the score well below 60.
    """
    if not report.sections:
        return 100
    # Determine worst severity per tier
    tier_severity: dict[str, str] = {}
    for s in report.sections:
        tier = SECTION_TIER.get(s.name, "P4")
        sev  = s.severity.value  # "ok" | "warning" | "critical"
        prev = tier_severity.get(tier, "ok")
        if sev == "critical" or (sev == "warning" and prev == "ok"):
            tier_severity[tier] = sev
    # Sum penalties
    penalty = sum(
        _TIER_PENALTY[tier][sev]
        for tier, sev in tier_severity.items()
        if sev != "ok"
    )
    return max(0, 100 - penalty)


def _sticky_bar(cluster_label: str, severity: HealthSeverity, ts: str) -> str:
    """Sticky top bar showing cluster identity — BL-079."""
    sev_color = _COLOR[severity]
    sev_label = _TAG_LABEL[severity]
    return (
        f'<div class="sticky-bar">'
        f'<span class="sticky-cluster">{cluster_label}</span>'
        f'<span class="sticky-sep">·</span>'
        f'<span class="sticky-sev" style="color:{sev_color}">{sev_label}</span>'
        f'<span class="sticky-ts">{ts}</span>'
        f'</div>'
    )


def _overall_health_summary(report: HealthCheckReport) -> str:
    """Overall severity badge + health score block — BL-080."""
    score     = _health_score(report)
    sev_color = _COLOR[report.overall_severity]
    sev_label = _TAG_LABEL[report.overall_severity]
    tag_cls   = _TAG[report.overall_severity]

    return (
        f'<div class="overall-health">'
        f'<div class="oh-left">'
        f'<span class="oh-label">Overall health</span>'
        f'<span class="tag {tag_cls}">{sev_label}</span>'
        f'</div>'
        f'<div class="oh-score" style="color:{sev_color};">'
        f'{score}<span class="oh-denom">&thinsp;/&thinsp;100</span>'
        f'</div>'
        f'</div>'
    )


def _rating_explainer(report: HealthCheckReport) -> str:
    """Collapsible formula explanation for overall severity and health score — BL-080."""
    n = len(report.sections)
    if n == 0:
        return ""
    score  = _health_score(report)
    n_ok   = sum(1 for s in report.sections if s.severity == HealthSeverity.OK)
    n_warn = sum(1 for s in report.sections if s.severity == HealthSeverity.WARNING)
    n_crit = sum(1 for s in report.sections if s.severity == HealthSeverity.CRITICAL)

    # Build per-tier breakdown for this run
    tier_severity: dict[str, str] = {}
    for s in report.sections:
        tier = SECTION_TIER.get(s.name, "P4")
        sev  = s.severity.value
        prev = tier_severity.get(tier, "ok")
        if sev == "critical" or (sev == "warning" and prev == "ok"):
            tier_severity[tier] = sev

    rows = ""
    total_penalty = 0
    for tier in ["P0", "P1", "P2", "P3", "P4"]:
        sev = tier_severity.get(tier, "ok")
        if sev == "ok":
            penalty_str = "−0"
            style = "color:var(--ok)"
        else:
            p = _TIER_PENALTY[tier][sev]
            total_penalty += p
            penalty_str = f"−{p}"
            style = "color:var(--crit)" if sev == "critical" else "color:var(--warn)"
        rows += (
            f'<tr>'
            f'<td>{tier}</td>'
            f'<td>{_TIER_LABEL[tier]}</td>'
            f'<td style="text-transform:capitalize">{sev}</td>'
            f'<td style="{style};font-weight:600">{penalty_str}</td>'
            f'</tr>'
        )

    return (
        f'<details class="rating-info">'
        f'<summary>How is this score calculated?</summary>'
        f'<div class="rating-body">'
        f'<p>Score starts at <strong>100</strong> and deducts points based on the consequence of each issue.'
        f' Sections are grouped into consequence tiers — a replication failure (P0) costs more than'
        f' a slow query (P3). One penalty per tier; worst severity within the tier applies.</p>'
        f'<table style="width:100%;border-collapse:collapse;font-size:0.82rem;margin:8px 0">'
        f'<thead><tr style="color:var(--t2);border-bottom:1px solid var(--border)">'
        f'<th style="text-align:left;padding:3px 8px 3px 0">Tier</th>'
        f'<th style="text-align:left;padding:3px 8px">Consequence</th>'
        f'<th style="text-align:left;padding:3px 8px">This run</th>'
        f'<th style="text-align:right;padding:3px 0 3px 8px">Penalty</th>'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody>'
        f'</table>'
        f'<p class="rating-formula">100 &minus; {total_penalty} = <strong>{score}</strong></p>'
        f'</div>'
        f'</details>'
    )


def _fmt(v: object) -> str:
    if isinstance(v, float): return f"{v:,.1f}"
    if isinstance(v, int):   return f"{v:,}"
    return str(v)

# Signals where LOW value is the problem (matches llm_recommender._BELOW_THRESHOLD_IS_BAD)
_BELOW_THRESHOLD_IS_BAD = frozenset({
    "wt_cache_hit_ratio",   # low hit rate = reads hitting disk
    "tickets_reads",        # low remaining tickets = read exhaustion
    "tickets_writes",       # low remaining tickets = write stall
    "oplog_window_hours",   # short window = secondary sync risk
})


def _is_breached(sig) -> bool:
    """True if the signal value has crossed its threshold in the bad direction."""
    if sig.threshold is None:
        return False
    if not isinstance(sig.value, (int, float)) or not isinstance(sig.threshold, (int, float)):
        return False
    if sig.name in _BELOW_THRESHOLD_IS_BAD:
        return sig.value < sig.threshold
    return sig.value > sig.threshold


# ── sidebar ────────────────────────────────────────────────────────────────────

def _sidebar(report: HealthCheckReport, score: int) -> str:
    cluster  = report.cluster_name or (report.cluster_uri.split("@")[-1] if "@" in report.cluster_uri else report.cluster_uri)
    date_str = report.timestamp.strftime("%Y-%m-%d · %H:%M UTC")

    by_name  = {s.name: s for s in report.sections}
    n_issues = sum(1 for s in report.sections if s.severity != HealthSeverity.OK)

    def _dot(anchor: str, section_name: str | None) -> str:
        if section_name and section_name in by_name:
            return _DOT[by_name[section_name].severity]
        if anchor == "alerts":
            if n_issues == 0: return "d-gray"
            return "d-red" if any(s.severity == HealthSeverity.CRITICAL for s in report.sections) else "d-amber"
        if anchor == "recommendations":
            return "d-green" if report.recommendations else "d-gray"
        return "d-gray"

    groups_html: list[str] = []
    for group_name, items in _NAV_GROUPS:
        nav_items: list[str] = []
        for label, anchor, section_name in items:
            display = label
            if anchor == "alerts":
                display = f"Active alerts ({n_issues})" if n_issues else "Active alerts"
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

    r    = 18
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
      <svg width="48" height="48" viewBox="0 0 48 48">
        <circle cx="24" cy="24" r="{r}" fill="none" stroke="rgba(255,255,255,0.07)" stroke-width="3.5"/>
        <circle cx="24" cy="24" r="{r}" fill="none" stroke="{sev_color}" stroke-width="3.5"
          stroke-dasharray="{circ:.1f}" stroke-dashoffset="{off:.1f}" stroke-linecap="round"/>
      </svg>
      <div class="score-num" style="color:{sev_color}">{score}</div>
    </div>
    <div>
      <div class="score-info">Overall health</div>
      <div class="score-status">{sev_label} · {issue_str}</div>
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

_METRIC_TOOLTIPS: dict[str, str] = {
    # §2 Server Health
    "mongodb_version":          "MongoDB server version. Current supported releases: 7.0 (LTS), 8.0 (LTS). Versions 5.0 and earlier are end-of-life. Ensure all replica set members run the same version.",
    "uptime_hours":             "Time since mongod last started. A recent restart may indicate a crash or planned maintenance.",
    "filesystem_disk_used_gb":  "Disk space used as reported by MongoDB's filesystem view (fsUsedSize). On Linux production servers this matches OS-level usage reliably.",
    "filesystem_disk_used_pct": "Percentage of total disk used. Above 80% MongoDB may refuse writes. Above 90% is critical — free space immediately.",
    # §3 Replication Health
    "oplog_window_hours":       "How many hours of write history the oplog can hold. If a secondary falls behind by more than this window it must be re-synced from scratch. Below 24 h is a risk.",
    "member_count":             "Number of configured replica set members (primary + secondaries + arbiters). A minimum of 3 members with votes is required for automatic failover.",
    # §4 Storage & Capacity
    "mongodb_data_mb":          "Total uncompressed data size across all user collections. This is the logical size; on-disk storage is smaller due to WiredTiger compression.",
    "mongodb_index_mb":         "Total size of all indexes in memory. High index size relative to data size may indicate over-indexing.",
    "collections_analysed":     "Number of collections included in the storage analysis.",
    # §5 Query Performance
    "slow_query_count":         "Number of operations that exceeded the slow query threshold (default 5 ms). A high count indicates missing indexes or inefficient queries.",
    "collscan_count":           "Number of slow operations that used a COLLSCAN plan — meaning no index was used and the entire collection was scanned. Every COLLSCAN is a candidate for an index.",
    "sort_stage_count":         "Number of slow operations that required an in-memory sort stage (SORT plan). In-memory sorts are bounded by 100 MB; above that MongoDB aborts the query unless allowDiskUse is set.",
    "sort_spill_count":         "Number of slow operations where the in-memory sort exceeded the 100 MB limit and spilled to disk. Any non-zero value is a significant performance concern.",
    "max_execution_ms":         "Execution time of the single slowest query in this run. A one-off spike may be acceptable; a consistently high max indicates a problematic query pattern.",
    "avg_execution_ms":         "Average execution time of all slow queries. Values above 100 ms on a production cluster typically indicate index gaps or large full scans.",
    # §8 Operations
    "memory_resident_mb":       "RAM currently used by the mongod process. In production this should approach total server RAM — MongoDB keeps its working set in memory. Unexpectedly low values may mean the working set exceeds RAM and is being evicted.",
    "page_faults":              "Cumulative count of times MongoDB read a data page from disk because it was not in the WiredTiger cache. The rate between health check runs matters more than the total — a rising rate signals memory pressure.",
    "wt_cache_hit_ratio":       "Percentage of read operations served from WiredTiger's in-memory cache without touching disk. Below 95% means the working set is larger than the cache — consider adding RAM or reducing the working set.",
    "lock_wait_pct":            "Percentage of time operations spent waiting to acquire a global lock. Above 5% indicates write contention or long-running operations starving concurrent reads.",
    "cluster_targeting_ratio":  "Documents examined divided by documents returned across all queries since last restart. A ratio above 10 means queries are scanning far more data than needed — the primary cause is missing indexes. 1.0 is perfect (every scanned document is returned).",
    # §9 Connections & Concurrency
    "total_connections":        "Total current client connections across all replica set members. High connection counts consume memory (~1 MB per connection). Use connection pooling to reduce this.",
    "tickets_reads":            "WiredTiger read tickets available on the most constrained member. Tickets limit concurrent read operations into the storage engine. If this approaches 0, reads queue and latency spikes.",
    "tickets_writes":           "WiredTiger write tickets available on the most constrained member. If this approaches 0, writes queue and the cluster effectively stalls.",
    "lock_queue_total":         "Peak global lock queue depth — operations waiting for a lock grant. Sustained values above 5 indicate write-heavy workloads are blocking reads.",
    # §10 Infrastructure
    "cpu_user_pct":             "Normalised CPU time used by the mongod process itself (divided by CPU core count). Above 70% sustained means MongoDB is compute-bound — look for expensive aggregations or missing indexes.",
    "cpu_iowait_pct":           "CPU time the system spent waiting for disk I/O. Above 20% means the disk subsystem is a bottleneck — check IOPS capacity, disk queue depth, and whether the working set fits in memory.",
    "system_memory_used_pct":   "Percentage of total system RAM in use. Above 90% risks the OS swapping MongoDB's memory to disk, causing severe latency spikes.",
    "disk_iops_write":          "Write I/O operations per second on the primary's data partition. Compare against your disk's rated IOPS ceiling — sustained saturation causes write stalls.",
    "disk_write_latency_ms":    "Average write latency on the primary's data partition. Above 20 ms indicates I/O saturation or a slow disk subsystem; above 50 ms is a critical bottleneck.",
    # §5 Query Performance — BL-006
    "profiler_disabled_dbs":    "Number of databases where the MongoDB profiler is turned off (level 0). Slow query data cannot be captured when the profiler is disabled — enable it with db.setProfilingLevel(1, {slowms: 5}).",
    "profiler_high_slowms_dbs": "Number of databases where the profiler's slowms threshold exceeds 100 ms. Queries faster than this threshold are not captured, creating blind spots in performance analysis.",
    # §7 Unused Indexes — BL-007
    "redundant_indexes":        "Number of indexes whose key pattern is a left-prefix of another index on the same collection. These are fully redundant — the compound index satisfies all queries the shorter index could handle. Dropping them reduces write overhead and storage.",
}


_SIGNAL_LABELS: dict[str, str] = {
    # §1 Cluster Overview
    "database_count":             "Databases",
    "collection_count":           "Collections",
    # §4 Storage & Capacity
    "mongodb_data_mb":            "Data Size",
    "mongodb_index_mb":           "Index Size",
    "collections_analysed":       "Collections",
    # §2 Server Health
    "mongodb_version":            "Version",
    "uptime_hours":               "Uptime",
    "filesystem_disk_used_gb":    "Disk Used",
    "filesystem_disk_used_pct":   "Disk Used %",
    # §9 Connections & Concurrency
    "total_connections":          "Connections",
    "tickets_reads":              "Read Tickets",
    "tickets_writes":             "Write Tickets",
    "lock_queue_total":           "Lock Queue Depth",
    # §10 Infrastructure
    "cpu_user_pct":               "CPU User %",
    "cpu_iowait_pct":             "CPU I/O Wait %",
    "system_memory_used_pct":     "Memory Used %",
    "disk_iops_write":            "Disk Write IOPS",
    "disk_write_latency_ms":      "Disk Write Latency",
    # §7 Unused Indexes (BL-007)
    "redundant_indexes":          "Redundant Indexes",
    # §5 Query Performance (BL-006)
    "profiler_disabled_dbs":      "Profiler Off",
    "profiler_high_slowms_dbs":   "Profiler slowms > 100",
}


def _metric_grid(section: ReportSection) -> str:
    if not section.signals:
        return ""
    cards: list[str] = []
    for sig in section.signals:
        breached = _is_breached(sig)
        if breached:
            m_cls     = "m-crit" if section.severity == HealthSeverity.CRITICAL else "m-warn"
            val_color = _COLOR[section.severity]
        else:
            m_cls, val_color = "", "var(--t1)"

        unit_html  = f'<div class="metric-sub">{sig.unit}</div>' if sig.unit else '<div class="metric-sub"></div>'
        limit_html = (
            f'<div class="metric-limit">threshold {_fmt(sig.threshold)}{" " + sig.unit if sig.unit else ""}</div>'
            if sig.threshold is not None else ""
        )
        label = _SIGNAL_LABELS.get(sig.name, sig.name.replace("_", " ").title())
        # Tooltip: prefer LLM-generated on sig.tooltip, fall back to static dict
        tip_text = sig.tooltip or _METRIC_TOOLTIPS.get(sig.name, "")
        if tip_text:
            import html as _html
            safe = _html.escape(tip_text)
            info_html = (
                f'<span class="minfo" tabindex="0">'
                f'<input class="minfo-chk" type="checkbox" aria-hidden="true">'
                f'<span class="minfo-icon" aria-label="{safe}" role="img">i</span>'
                f'<span class="minfo-tip">{safe}</span>'
                f'</span>'
            )
        else:
            info_html = ""
        cards.append(
            f'<div class="metric {m_cls}">'
            f'<div class="metric-lbl">{label}{info_html}</div>'
            f'<div class="metric-val" style="color:{val_color}">{_fmt(sig.value)}</div>'
            f'{unit_html}'
            f'{limit_html}'
            f'</div>'
        )
    return f'<div class="metric-grid">{"".join(cards)}</div>'


# ── findings ──────────────────────────────────────────────────────────────────

def _findings_html(section: ReportSection) -> str:
    if not section.findings:
        return ""

    list_items: list[str] = []
    for i, line in enumerate(section.findings):
        stripped = line.strip()
        if not stripped:
            continue
        is_indent = line.startswith("  ")
        if is_indent:
            list_items.append(f'<li class="indent">{stripped}</li>')
        elif i == 0 and section.severity != HealthSeverity.OK:
            # First finding is the headline — render bold, no coloured box
            list_items.append(f'<li class="lead">{stripped}</li>')
        else:
            list_items.append(f'<li>{stripped}</li>')

    return f'<ul class="findings">{"".join(list_items)}</ul>'


# ── section card ─────────────────────────────────────────────────────────────

def _section_card(section: ReportSection, anchor_id: str, display_name: str | None = None) -> str:
    name      = display_name or section.name
    border_cls = _SECTION_BORDER[section.severity]
    return (
        f'<div class="section {border_cls}" id="{anchor_id}">'
        f'<div class="section-hd">'
        f'<span class="section-title">{name}</span>'
        f'<span class="tag {_TAG[section.severity]}">{_TAG_LABEL[section.severity]}</span>'
        f'</div>'
        f'{_metric_grid(section)}'
        f'{_findings_html(section)}'
        f'</div>'
    )


# ── active alerts ─────────────────────────────────────────────────────────────

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
        desc_lines = [l.strip() for l in s.findings[1:] if l.strip() and not l.startswith("  ")]
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

def _health_summary_html(report: "HealthCheckReport") -> str:
    """LLM-generated natural language health summary block."""
    if not report.health_summary:
        return ""
    import html as _html
    return (
        f'<div class="health-summary">'
        f'<span class="health-summary-label">AI Summary</span>'
        f'<p class="health-summary-text">{_html.escape(report.health_summary)}</p>'
        f'</div>'
    )


def _recommendations_html(report: "HealthCheckReport") -> str:
    recs = report.recommendations
    if not recs:
        return (
            '<div class="section" id="recommendations">'
            '<div class="section-hd">'
            '<span class="section-title">Action Plan</span>'
            '</div>'
            + _health_summary_html(report)
            + '<div class="no-recs">No actions required — cluster looks healthy.</div>'
            '</div>'
        )

    import html as _html

    _PRI_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
    rows: list[str] = []
    for rec in sorted(recs, key=lambda r: _PRI_ORDER.get(r.priority, 9)):
        pri_cls = _REC_PRI.get(rec.priority, "rp4")
        pri_lbl = _REC_LBL.get(rec.priority, rec.priority)
        is_llm  = rec.confidence == "llm"
        src_html = (
            '<span class="badge-ai">AI</span>'
            if is_llm else
            f'<span class="badge-rule">Rule</span>'
        )
        rows.append(
            f'<tr>'
            f'<td><span class="rec-p {pri_cls}">{pri_lbl}</span></td>'
            f'<td class="rec-target">{_html.escape(rec.collection)}</td>'
            f'<td><code class="rec-action">{_html.escape(rec.action)}</code></td>'
            f'<td class="rec-evidence-cell">{_html.escape(rec.evidence)}</td>'
            f'<td>{src_html}</td>'
            f'</tr>'
        )

    worst_pri = "tag-red" if any(r.priority == "high" for r in recs) else "tag-amber"
    n = len(recs)
    return (
        f'<div class="section" id="recommendations">'
        f'<div class="section-hd">'
        f'<span class="section-title">Action Plan</span>'
        f'<span class="tag {worst_pri}">{n} action{"s" if n != 1 else ""}</span>'
        f'</div>'
        + _health_summary_html(report)
        + f'<div class="cta-table-wrap">'
        f'<table class="cta-table">'
        f'<thead><tr>'
        f'<th>Priority</th><th>Target</th><th>Action</th><th>Evidence</th><th>Source</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
        f'</div>'
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

    def group_header(label: str) -> str:
        return (
            f'<div class="content-group">'
            f'<span class="content-group-label">{label}</span>'
            f'<span class="content-group-rule"></span>'
            f'</div>'
        )

    hr = '\n<hr class="divider">\n'

    return "".join([
        # Summary
        card("Cluster Overview"),
        hr,
        _alerts_section(report),
        # Availability
        group_header("Availability"),
        card("Replication Health"),
        hr,
        card("Connections & Concurrency"),
        # Resource Health
        group_header("Resource Health"),
        card("Server Health"),
        hr,
        card("Storage & Capacity"),
        hr,
        card("Infrastructure"),
        # Performance
        group_header("Performance"),
        card("Query Performance"),
        hr,
        card("Operations"),
        # Index Advisory
        group_header("Index Advisory"),
        card("Missing Indexes"),
        hr,
        card("Unused Indexes"),
    ])


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
}, { threshold: 0.2, rootMargin: '0px 0px -60% 0px' });

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
    score         = _health_score(report)
    cluster_label = report.cluster_name or (report.cluster_uri.split("@")[-1] if "@" in report.cluster_uri else report.cluster_uri)
    ts            = report.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
    ts_short      = report.timestamp.strftime("%Y-%m-%d %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MongoDB health report — {cluster_label}</title>
  <style>{_CSS}</style>
</head>
<body>

{_sticky_bar(cluster_label, report.overall_severity, ts_short)}

<div class="layout">

{_sidebar(report, score)}

<main class="main">

  <div class="report-header">
    <div class="report-title">MongoDB cluster health report</div>
    <div class="report-cluster">{cluster_label}</div>
    <div class="report-sub">{ts} &middot; Run&thinsp;{report.run_id} &middot; {len(report.sections)} sections &middot; {len(report.recommendations)} recommendation{"s" if len(report.recommendations) != 1 else ""}</div>
    <div class="report-sub" style="margin-top:4px;font-size:0.78rem;opacity:0.6;">{"Agent v" + report.agent_version if report.agent_version else ""}{(" &middot; OM " + report.om_version) if report.om_version else ""}</div>
  </div>

  {_overall_health_summary(report)}

  {_rating_explainer(report)}

  {_recommendations_html(report)}

  {_status_bar(report)}

  {_build_content(report)}

  <div class="report-footer">
    mongodb-dba-agent · {cluster_label} · {ts}
  </div>

</main>
</div>
<script>{_JS}</script>
</body>
</html>"""
