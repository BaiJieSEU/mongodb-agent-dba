"""Self-contained HTML report renderer for HealthCheckReport (BL-060) — v6.

Design philosophy — "book, not dashboard":
  - Monochrome: severity conveyed by typography (bold, weight, words), not color
  - One accent: score ring only. Everything else is grayscale.
  - Clean metric cards, neutral tags, plain alert boxes
  - Information density through layout and spacing, not decoration
"""
from __future__ import annotations

import math
from models.health_check_report import (
    HealthCheckReport, HealthSeverity, ReportSection, worst_severity,
)

# ── severity maps ──────────────────────────────────────────────────────────────

_COLOR = {
    HealthSeverity.OK:       "var(--t3)",
    HealthSeverity.WARNING:  "var(--t2)",
    HealthSeverity.CRITICAL: "var(--t1)",
}
# Score ring — the ONE place color is used
_RING_COLOR = {
    HealthSeverity.OK:       "var(--ring-ok)",
    HealthSeverity.WARNING:  "var(--ring-warn)",
    HealthSeverity.CRITICAL: "var(--ring-crit)",
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
    "Cluster Overview":          ("sec-overview",       "Cluster Overview"),
    "Server Health":             ("sec-server",         "Server health"),
    "Replication Health":        ("sec-replication",    "Replication health"),
    "Storage & Capacity":        ("sec-storage",        "Storage"),
    "Backup & Recovery":         ("sec-backup",         "Backup & recovery"),
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
        ("Connections", "sec-connections", "Connections & Concurrency"),
    ]),
    ("Resource Health", [
        ("Server health",    "sec-server",  "Server Health"),
        ("Storage",          "sec-storage", "Storage & Capacity"),
        ("Backup & recovery","sec-backup",  "Backup & Recovery"),
        ("Infrastructure",   "sec-infra",   "Infrastructure"),
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

  /* Monochrome — single accent for score ring only */
  --accent: #60a5fa;
  --red:    var(--t1);
  --amber:  var(--t2);
  --green:  var(--t3);
  --blue:   var(--accent);

  --red-bg:    transparent;
  --amber-bg:  transparent;
  --green-bg:  transparent;
  --blue-bg:   rgba(96,165,250,0.06);

  --red-border:   var(--border);
  --amber-border: var(--border);
  --green-border: var(--border);
  --blue-border:  rgba(96,165,250,0.25);

  /* Score ring colors — the ONE place color is used */
  --ring-crit: #e74c3c;
  --ring-warn: #e8a838;
  --ring-ok:   #4fc964;
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

.nav-dot { width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0; }
.d-red, .d-amber { background: var(--t2); }
.d-green { background: var(--border-em); }
.d-gray  { background: var(--border); }

/* ── Sidebar group severity chip (BL-125) ── */
.nav-group-chip {
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: 700; font-family: var(--mono);
  min-width: 16px; height: 16px; border-radius: 8px; padding: 0 4px;
  margin-left: 6px; vertical-align: middle;
}
.ngc-red, .ngc-amber { background: var(--surface2); color: var(--t2); border: 1px solid var(--border); }
.ngc-green { background: transparent; }

/* ── Score ring at top of sidebar (BL-113) ── */
.sidebar-score {
  padding: 14px 18px 14px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 8px;
  display: flex; align-items: center; gap: 12px;
}
.score-ring { position: relative; width: 56px; height: 56px; flex-shrink: 0; }
.score-ring svg { transform: rotate(-90deg); }
.score-num {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 700;
}
.score-info   { font-size: 12px; color: var(--t2); font-weight: 500; }
.score-status { font-size: 12px; color: var(--t3); margin-top: 2px; }

/* ── Alert jump link (BL-111) ── */
.alert-jump {
  display: inline-block; margin-top: 6px;
  font-size: 11px; color: var(--t3); text-decoration: none;
  font-family: var(--mono);
}
.alert-jump:hover { color: var(--blue); }

/* ── Main ── */
.main { flex: 1; padding: 36px 48px; max-width: 1040px; }

/* ── Report header ── */
.report-header {
  margin-bottom: 28px; padding-bottom: 22px; border-bottom: 1px solid var(--border);
}
.report-title { font-size: 18px; font-weight: 600; color: var(--t1); margin-bottom: 3px; }
.report-cluster { font-size: 14px; font-weight: 600; color: var(--t2); margin-bottom: 6px; }
.report-sub   { font-size: 12px; color: var(--t3); }

/* ── Executive summary card (BL-124) ── */
.exec-summary {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 10px; padding: 20px 24px; margin-bottom: 12px;
  display: grid; grid-template-columns: auto 1fr; gap: 20px; align-items: center;
}
.exec-score-block { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.exec-ring { position: relative; width: 72px; height: 72px; flex-shrink: 0; }
.exec-ring svg { transform: rotate(-90deg); }
.exec-ring-num {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; font-weight: 800; font-family: var(--mono);
}
.exec-ring-label { font-size: 10px; color: var(--t3); text-transform: uppercase; letter-spacing: .06em; font-weight: 600; }
.exec-details { display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-start; }
.exec-kpi { display: flex; flex-direction: column; min-width: 90px; }
.exec-kpi-val { font-size: 20px; font-weight: 700; font-family: var(--mono); line-height: 1.1; }
.exec-kpi-lbl { font-size: 11px; color: var(--t3); margin-top: 3px; letter-spacing: .02em; }
.exec-chips { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
.exec-chip {
  font-size: 11px; font-family: var(--mono); font-weight: 600;
  padding: 2px 8px; border-radius: 10px; display: inline-flex; align-items: center; gap: 4px;
}
.exec-chip-ok, .exec-chip-warn, .exec-chip-crit {
  background: var(--surface2); color: var(--t2); border: 1px solid var(--border);
}
.exec-top-risk {
  font-size: 12px; color: var(--t2); line-height: 1.5;
  padding: 6px 10px; background: var(--surface2); border-left: 2px solid var(--border-em);
  border-radius: 4px; max-width: 340px;
}
.exec-top-risk.no-risk {
  background: var(--surface2); border-left-color: var(--border-em);
}
@media (max-width: 820px) {
  .exec-summary { grid-template-columns: 1fr; }
  .exec-score-block { flex-direction: row; gap: 12px; }
}

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
.c-red, .c-amber, .c-green, .c-dim { color: var(--t1); }

/* ── Section card ── */
.section {
  scroll-margin-top: 68px;
  border-left: 3px solid transparent;
  padding-left: 14px;
  margin-left: -14px;
  margin-bottom: 4px;
}
.section.s-warn { border-left-color: var(--border-em); }
.section.s-crit { border-left-color: var(--t3); }

.section-hd {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 6px;
}
.section-title { font-size: 15px; font-weight: 600; color: var(--t1); }
.section-icon { font-size: 15px; flex-shrink: 0; }
/* BL-127: section description line */
.section-desc {
  font-size: 12px; color: var(--t3); margin-bottom: 14px; line-height: 1.4;
}

.tag { font-size: 11px; padding: 2px 8px; border-radius: 3px; font-family: var(--mono); font-weight: 600;
  background: var(--surface2); color: var(--t2); border: 1px solid var(--border); text-transform: uppercase; letter-spacing: .03em; }
.tag-red, .tag-amber, .tag-green, .tag-gray { background: var(--surface2); color: var(--t2); border: 1px solid var(--border); }

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
.alert-red, .alert-amber, .alert-green {
  background: var(--surface2); border-color: var(--border-em);
}
.alert-title { font-size: 13px; font-weight: 600; margin-bottom: 4px; color: var(--t1); }
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

/* ── Timeline findings for WARN/CRIT sections (BL-130) ── */
.findings-timeline { margin-top: 10px; padding-left: 6px; border-left: 2px solid var(--border); }
.findings-timeline .ft-item {
  position: relative; padding: 6px 0 6px 14px; font-size: 13px; color: var(--t2); line-height: 1.6;
}
.findings-timeline .ft-item::before {
  content: ""; position: absolute; left: -6px; top: 12px;
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--border-em); border: 2px solid var(--surface);
}
.findings-timeline.ftl-crit { border-left-color: var(--t3); }
.findings-timeline.ftl-crit .ft-item::before { background: var(--t2); }
.findings-timeline.ftl-warn { border-left-color: var(--border-em); }
.findings-timeline.ftl-warn .ft-item::before { background: var(--t3); }
.findings-timeline .ft-item.ft-lead { color: var(--t1); font-weight: 500; }
.findings-timeline .ft-item.ft-indent {
  padding-left: 1.8rem; color: var(--t3);
  font-family: var(--mono); font-size: 12px; line-height: 1.5;
}
.findings-timeline .ft-item.ft-indent::before { display: none; }

/* ── Metric grid ── */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 8px; margin-bottom: 16px;
}
.metric {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 7px; padding: 14px 16px;
  transition: border-color 0.15s, transform 0.12s, box-shadow 0.15s;
}
.metric:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  border-color: var(--border-em);
}
.metric.m-crit, .metric.m-warn { border-color: var(--border-em); background: var(--surface2); }
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
  color: var(--t1); border-color: var(--t2);
}
.minfo-tip {
  visibility: hidden; opacity: 0;
  position: absolute; bottom: calc(100% + 8px); left: 50%; transform: translateX(-50%);
  background: var(--surface2); border: 1px solid var(--border-em);
  color: var(--t1); font-size: 12px; line-height: 1.5;
  padding: 8px 12px; border-radius: 6px;
  width: 260px; white-space: normal; z-index: 100;
  box-shadow: 0 4px 16px rgba(0,0,0,0.15);
  pointer-events: none;
  transition: opacity 0.15s;
}
.minfo-tip::after {
  content: ""; position: absolute; top: 100%; left: 50%; transform: translateX(-50%);
  border: 5px solid transparent; border-top-color: var(--border-em);
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

/* ── Copy-to-clipboard button (BL-110) ── */
.copy-wrap { position: relative; display: block; margin: 6px 0 8px; }
.copy-btn {
  position: absolute; top: 5px; right: 6px;
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 3px; padding: 1px 6px;
  font-size: 11px; color: var(--t3); cursor: pointer;
  font-family: var(--mono); line-height: 1.6;
  transition: color 0.12s, border-color 0.12s;
  user-select: none; pointer-events: all;
}
.copy-btn:hover { color: var(--blue); border-color: var(--blue); }
.copy-btn.copied { color: var(--green); border-color: var(--green-border); }
.copy-wrap .rec-action {
  margin: 0; padding-right: 52px;
}

/* ── Tier header rows in Action Plan (BL-116) ── */
.tier-header td {
  background: var(--surface2); padding: 6px 10px;
  font-size: 11px; color: var(--t3); font-weight: 600;
  letter-spacing: 0.04em; text-transform: uppercase;
}

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
.rp0 { background: var(--surface2); color: var(--t1); border: 1px solid var(--border-em); font-weight: 700; }
.rp1 { background: var(--surface2); color: var(--t1); border: 1px solid var(--border); font-weight: 700; }
.rp2 { background: var(--surface2); color: var(--t2); border: 1px solid var(--border); }
.rp3 { background: var(--surface2); color: var(--t3); border: 1px solid var(--border); }
.rp4 { background: var(--surface2); color: var(--t3); border: 1px solid var(--border); }
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
.badge-ai, .badge-rule {
  font-size: 11px; font-family: var(--mono); font-weight: 600;
  padding: 2px 6px; border-radius: 3px;
  background: var(--surface2); color: var(--t3); border: 1px solid var(--border);
}
.no-recs { font-size: 13px; color: var(--t3); padding: 16px 0; }

/* ── Health summary ── */
.health-summary {
  background: var(--surface2); border: 1px solid var(--border);
  border-left: 3px solid var(--border-em); border-radius: 6px;
  padding: 14px 16px; margin-bottom: 18px;
}
.health-summary-label {
  display: block; font-size: 11px; font-family: var(--mono); font-weight: 600;
  color: var(--t3); text-transform: uppercase; letter-spacing: .06em; margin-bottom: 8px;
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

/* ── Collapsible details panel (BL-083 / BL-117 accessibility fix) ── */
.findings-details { margin-top: 6px; }
.findings-details > summary {
  cursor: pointer; list-style: none;
  font-size: 11px; color: var(--t3); padding: 3px 0;
  user-select: none; letter-spacing: 0.01em;
  display: flex; align-items: center; gap: 4px;
}
.findings-details > summary::-webkit-details-marker { display: none; }
.findings-details > summary::marker { content: ""; }
.findings-details > summary .det-arrow { font-size: 9px; transition: transform 0.15s; }
.findings-details[open] > summary .det-arrow { transform: rotate(90deg); }
.findings-details > summary:hover { color: var(--t2); }
.findings-details > .findings { margin-top: 6px; }

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

/* ── Trend arrows (BL-114) — monochrome ── */
.trend { font-size: 11px; font-weight: 700; margin-left: 4px; color: var(--t3); }
.trend-up-bad, .trend-down-bad, .trend-up-good, .trend-down-good, .trend-stable { color: var(--t3); }

/* ── Headroom progress bar (BL-120) ── */
.headroom-bar-wrap { margin-top: 6px; }
.headroom-bar {
  height: 3px; border-radius: 2px; width: 100%;
  background: var(--border);
  overflow: hidden;
}
.headroom-fill {
  height: 100%; border-radius: 2px; transition: width 0.3s;
}
.hf-safe   { background: var(--border-em); }
.hf-mid    { background: var(--t3); }
.hf-near   { background: var(--t2); }
.headroom-label { font-size: 10px; color: var(--t3); margin-top: 2px; }

/* ── Collapsed placeholder stub (BL-121) ── */
.placeholder-stub {
  font-size: 12px; color: var(--t3); font-style: italic;
  padding: 8px 0; display: flex; align-items: center; gap: 8px;
}
.placeholder-stub .pl-expand {
  color: var(--blue); text-decoration: none; font-style: normal;
  font-size: 11px; font-family: var(--mono);
}
.placeholder-stub .pl-expand:hover { text-decoration: underline; }
.placeholder-full { display: none; }
.placeholder-full.open { display: block; }

/* ── Light mode (BL-118) ── */
@media (prefers-color-scheme: light) {
  :root:not([data-theme="dark"]) {
    --bg:        #f8fafc;
    --surface:   #ffffff;
    --surface2:  #f1f5f9;
    --border:    rgba(0,0,0,0.09);
    --border-em: rgba(0,0,0,0.18);
    --t1: #0f172a;
    --t2: #475569;
    --t3: #94a3b8;
    --accent: #2563eb;
    --red:    var(--t1);
    --amber:  var(--t2);
    --green:  var(--t3);
    --blue:   var(--accent);
    --red-bg: transparent; --amber-bg: transparent; --green-bg: transparent;
    --blue-bg: rgba(37,99,235,0.05);
    --red-border: var(--border); --amber-border: var(--border); --green-border: var(--border);
    --blue-border: rgba(37,99,235,0.20);
    --ring-crit: #dc2626; --ring-warn: #d97706; --ring-ok: #059669;
  }
}
:root[data-theme="light"] {
  --bg:        #f8fafc;
  --surface:   #ffffff;
  --surface2:  #f1f5f9;
  --border:    rgba(0,0,0,0.09);
  --border-em: rgba(0,0,0,0.18);
  --t1: #0f172a;
  --t2: #475569;
  --t3: #94a3b8;
  --accent: #2563eb;
  --red:    var(--t1);
  --amber:  var(--t2);
  --green:  var(--t3);
  --blue:   var(--accent);
  --red-bg: transparent; --amber-bg: transparent; --green-bg: transparent;
  --blue-bg: rgba(37,99,235,0.05);
  --red-border: var(--border); --amber-border: var(--border); --green-border: var(--border);
  --blue-border: rgba(37,99,235,0.20);
  --ring-crit: #dc2626; --ring-warn: #d97706; --ring-ok: #059669;
}
/* Theme toggle — pill switch */
.sidebar-footer {
  margin-top: auto; padding: 12px 16px; border-top: 1px solid var(--border);
  display: flex; align-items: center; gap: 10px;
}
.sidebar-footer .toggle-label { font-size: 11px; color: var(--t3); }
.pill-toggle {
  position: relative; width: 40px; height: 22px; flex-shrink: 0; cursor: pointer;
  background: var(--border-em); border-radius: 11px; border: none; padding: 0;
  transition: background 0.2s;
}
.pill-toggle::after {
  content: ''; position: absolute; top: 3px; left: 3px;
  width: 16px; height: 16px; border-radius: 50%;
  background: var(--bg); transition: transform 0.2s;
}
[data-theme="light"] .pill-toggle { background: var(--t3); }
[data-theme="light"] .pill-toggle::after { transform: translateX(18px); }

/* ── Print / Save as PDF (BL-119) ── */
@media print {
  .sidebar, .sticky-bar, .cluster-tabs, .pill-toggle, .sidebar-footer { display: none !important; }
  .layout { display: block !important; }
  .main { max-width: none !important; padding: 16px !important; }
  body { background: #fff !important; color: #000 !important; font-size: 11px; }
  .section { border-left: 2px solid #ccc !important; page-break-inside: avoid; }
  .metric { background: #f8f8f8 !important; border-color: #ddd !important; }
  .metric-val { color: #000 !important; }
  .metric-grid { grid-template-columns: repeat(3, 1fr) !important; }
  .tag { background: #f0f0f0 !important; color: #333 !important; }
  .alert { background: #f8f8f8 !important; }
  .exec-summary { background: #f8f8f8 !important; }
  .cta-table-wrap { overflow: visible !important; }
  .cta-table { font-size: 10px !important; }
  .rec-item { page-break-inside: avoid; }
  .report-footer { color: #666 !important; border-top-color: #ccc !important; }
  a[href]::after { content: ""; }
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
    "Backup & Recovery":         "P1",   # BL-106/107
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
    sev_label = _TAG_LABEL[severity]
    return (
        f'<div class="sticky-bar">'
        f'<span class="sticky-cluster">{cluster_label}</span>'
        f'<span class="sticky-sep">·</span>'
        f'<span class="sticky-sev">{sev_label}</span>'
        f'<span class="sticky-ts">{ts}</span>'
        f'</div>'
    )


def _overall_health_summary(report: HealthCheckReport) -> str:
    """Executive summary card — BL-124 (replaces BL-080 overall-health bar)."""
    score     = _health_score(report)
    sev_color = _RING_COLOR[report.overall_severity]
    n_ok   = sum(1 for s in report.sections if s.severity == HealthSeverity.OK)
    n_warn = sum(1 for s in report.sections if s.severity == HealthSeverity.WARNING)
    n_crit = sum(1 for s in report.sections if s.severity == HealthSeverity.CRITICAL)
    n_recs = len(report.recommendations)

    # Score ring (72px)
    r    = 28
    circ = 2 * math.pi * r
    off  = circ * (1 - score / 100)

    # Section breakdown chips
    chips = []
    if n_crit: chips.append(f'<span class="exec-chip exec-chip-crit">{n_crit} critical</span>')
    if n_warn: chips.append(f'<span class="exec-chip exec-chip-warn">{n_warn} warning</span>')
    if n_ok:   chips.append(f'<span class="exec-chip exec-chip-ok">{n_ok} healthy</span>')

    # Top risk
    top_risk = None
    top_rank = 999
    for s in report.sections:
        if s.severity == HealthSeverity.OK:
            continue
        tier = SECTION_TIER.get(s.name, "P4")
        rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}.get(tier, 4)
        if rank < top_rank:
            top_rank = rank
            top_risk = s
    if top_risk:
        tier = SECTION_TIER.get(top_risk.name, "P4")
        first_finding = top_risk.findings[0].strip() if top_risk.findings else top_risk.name
        risk_html = f'<div class="exec-top-risk"><strong>{top_risk.name}</strong> ({tier}) — {first_finding}</div>'
    else:
        risk_html = '<div class="exec-top-risk no-risk">No risks detected — all sections healthy</div>'

    return (
        f'<div class="exec-summary">'
        f'<div class="exec-score-block">'
        f'<div class="exec-ring">'
        f'<svg width="72" height="72" viewBox="0 0 72 72">'
        f'<circle cx="36" cy="36" r="{r}" fill="none" stroke="rgba(255,255,255,0.07)" stroke-width="5"/>'
        f'<circle cx="36" cy="36" r="{r}" fill="none" stroke="{sev_color}" stroke-width="5"'
        f' stroke-dasharray="{circ:.1f}" stroke-dashoffset="{off:.1f}" stroke-linecap="round"/>'
        f'</svg>'
        f'<div class="exec-ring-num" style="color:{sev_color}">{score}</div>'
        f'</div>'
        f'<div class="exec-ring-label">Health score</div>'
        f'</div>'
        f'<div class="exec-details">'
        f'<div class="exec-kpi"><div class="exec-kpi-val">{n_recs}</div><div class="exec-kpi-lbl">Actions required</div></div>'
        f'{risk_html}'
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
    "wt_cache_hit_ratio",      # low hit rate = reads hitting disk
    "tickets_reads",           # low remaining tickets = read exhaustion
    "tickets_writes",          # low remaining tickets = write stall
    "oplog_window_hours",      # short window = secondary sync risk
    "oplog_window_for_pitr",   # short window = PITR gap between backups
    "plan_cache_hit_rate_pct", # low hit rate = frequent re-planning
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

    ring_color = _RING_COLOR[report.overall_severity]
    sev_label  = _TAG_LABEL[report.overall_severity]
    issue_str  = f"{n_issues} issue{'s' if n_issues != 1 else ''}" if n_issues else "All clear"

    r    = 21
    circ = 2 * math.pi * r
    off  = circ * (1 - score / 100)

    return f"""<nav class="sidebar">
  <div class="sidebar-top">
    <div class="sidebar-cluster">{cluster}</div>
    <div class="sidebar-meta">{date_str}</div>
  </div>
  <div class="sidebar-score">
    <div class="score-ring">
      <svg width="56" height="56" viewBox="0 0 56 56">
        <circle cx="28" cy="28" r="{r}" fill="none" stroke="rgba(255,255,255,0.07)" stroke-width="4"/>
        <circle cx="28" cy="28" r="{r}" fill="none" stroke="{ring_color}" stroke-width="4"
          stroke-dasharray="{circ:.1f}" stroke-dashoffset="{off:.1f}" stroke-linecap="round"/>
      </svg>
      <div class="score-num" style="color:{ring_color}">{score}</div>
    </div>
    <div>
      <div class="score-info">Overall health</div>
      <div class="score-status">{sev_label} · {issue_str}</div>
    </div>
  </div>
{"".join(groups_html)}
  <div class="sidebar-footer">
    <span class="toggle-label">Dark</span>
    <button class="pill-toggle" onclick="toggleTheme()" title="Toggle light/dark mode"></button>
    <span class="toggle-label">Light</span>
  </div>
</nav>"""


# ── status bar ─────────────────────────────────────────────────────────────────

_STATUS_SLOTS = [
    ("database_count",            "Databases"),
    ("collection_count",          "Collections"),
    ("slow_query_count",          "Slow queries"),
    ("under_indexed_collections", "Missing indexes"),
    ("unused_indexes",            "Unused indexes"),
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
    "exact_duplicates":         "Number of indexes with identical key names and sort directions on the same collection. Exact duplicates are 100% redundant — they consume the same write overhead twice with zero read benefit. Drop the duplicate immediately.",
    # §8 Operations — BL-098/099/103/107
    "network_bytes_in_mb":      "Cumulative bytes received by this mongod since last restart. Useful for trending — a sudden spike may indicate a new client sending large batches or a misconfigured query returning excessive data.",
    "network_bytes_out_mb":     "Cumulative bytes sent by this mongod since last restart. A value much larger than bytes-in typically means large result sets are being returned — check for queries missing projections or returning unbounded arrays.",
    "plan_cache_hit_rate_pct":  "Percentage of query executions that reused a cached plan vs re-planned from scratch. Below 80% means MongoDB is spending significant CPU re-optimising queries on every execution — look for rapidly changing data distributions or frequent index modifications.",
    # §9 Backup & Recovery — BL-106/107
    "backup_cursor_open":       "1 = an active backup cursor is open (a backup process is running). 0 = no backup cursor detected. A value of 0 does not confirm no backups exist, but it does mean no backup is active right now — verify your backup schedule externally (cron jobs, snapshot scripts, etc.).",
    "oplog_window_for_pitr":    "Current oplog window (hours) compared to your configured backup interval. The oplog must cover at least the backup interval to guarantee point-in-time recovery (PITR) between any two backup snapshots. If the oplog is shorter than the interval, there is a gap where PITR is impossible.",
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
    "exact_duplicates":           "Exact Duplicates",
    # §5 Query Performance (BL-006)
    "profiler_disabled_dbs":      "Profiler Off",
    "profiler_high_slowms_dbs":   "Profiler slowms > 100",
    "slow_aggregation_count":     "Slow Aggregations",
    "profiler_slowms":            "Profiler Threshold",
    "slow_query_pct":             "Slow Query %",
    "slow_query_count":           "Slow Queries",
    "total_profiled":             "Total Profiled",
    # §8 Operations
    "network_bytes_in_mb":        "Network In",
    "network_bytes_out_mb":       "Network Out",
    "plan_cache_hit_rate_pct":    "Plan Cache Hit Rate",
    "long_running_ops_count":     "Long-Running Ops",
    "longest_op_sec":             "Longest Op",
    # §9 Backup & Recovery
    "backup_cursor_open":         "Backup Cursor Active",
    "oplog_window_for_pitr":      "Oplog PITR Coverage",
    # §3 Replication
    "members_up":                 "Members Up",
    "members_down":               "Members Down",
    "replication_lag_max_sec":    "Max Replication Lag",
    # §4 Storage
    "index_to_data_ratio":        "Index / Data Ratio",
    "collections_analysed":       "Collections",
}


def _trend_html(sig) -> str:
    """BL-114: render a trend arrow for a signal with trend data."""
    if not sig.trend or sig.trend == "stable":
        if sig.trend == "stable":
            return '<span class="trend trend-stable" title="Stable vs baseline">→</span>'
        return ""
    higher_is_worse = sig.name not in _BELOW_THRESHOLD_IS_BAD
    if sig.trend == "up":
        cls = "trend-up-bad" if higher_is_worse else "trend-up-good"
        title = "Higher than baseline"
        arrow = "↑"
    else:  # down
        cls = "trend-down-good" if higher_is_worse else "trend-down-bad"
        title = "Lower than baseline"
        arrow = "↓"
    return f'<span class="trend {cls}" title="{title}">{arrow}</span>'


def _headroom_html(sig) -> str:
    """BL-120: progress bar showing safe distance to threshold on non-breached metrics."""
    if sig.threshold is None or _is_breached(sig):
        return ""
    if not isinstance(sig.value, (int, float)) or not isinstance(sig.threshold, (int, float)):
        return ""
    if sig.threshold == 0:
        return ""

    if sig.name in _BELOW_THRESHOLD_IS_BAD:
        # lower-is-worse: headroom = how far value is above the threshold
        # e.g. oplog 37.8h with threshold 24h → (37.8-24)/24 = 57% above
        margin = (sig.value - sig.threshold) / sig.threshold
        headroom_pct = max(int(margin * 100), 0)
        # Bar fill: 100% = right at threshold (danger), 0% = far above (safe)
        pct = max(0, min(int(100 - margin * 100), 100))
        if headroom_pct > 200:
            label = f">{200}% above threshold"
        else:
            label = f"{headroom_pct}% above threshold"
    else:
        # higher-is-worse: bar fills toward threshold
        pct = min(int((sig.value / sig.threshold) * 100), 99)
        headroom_pct = 100 - pct
        label = f"{headroom_pct}% headroom"

    fill_cls = "hf-safe" if pct < 60 else ("hf-mid" if pct < 80 else "hf-near")
    return (
        f'<div class="headroom-bar-wrap">'
        f'<div class="headroom-bar"><div class="headroom-fill {fill_cls}" style="width:{pct}%"></div></div>'
        f'<div class="headroom-label">{label}</div>'
        f'</div>'
    )


def _metric_grid(section: ReportSection) -> str:
    if not section.signals:
        return ""
    cards: list[str] = []
    for sig in section.signals:
        breached = _is_breached(sig)
        # Monochrome: breached metrics get emphasized border, not color
        m_cls = ("m-crit" if breached else "")
        val_color = "var(--t1)"

        unit_html  = f'<div class="metric-sub">{sig.unit}</div>' if sig.unit else '<div class="metric-sub"></div>'
        limit_html = (
            f'<div class="metric-limit">threshold {_fmt(sig.threshold)}{" " + sig.unit if sig.unit else ""}</div>'
            if sig.threshold is not None else ""
        )
        label = _SIGNAL_LABELS.get(sig.name, sig.name.replace("_", " ").title())
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
            f'<div class="metric-val" style="color:{val_color}">{_fmt(sig.value)}{_trend_html(sig)}</div>'
            f'{unit_html}'
            f'{limit_html}'
            f'{_headroom_html(sig)}'
            f'</div>'
        )
    return f'<div class="metric-grid">{"".join(cards)}</div>'


# ── findings ──────────────────────────────────────────────────────────────────

def _findings_list(lines: list[str], first_is_lead: bool = False) -> str:
    """Render a list of finding strings as an HTML <ul class="findings">."""
    items: list[str] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        is_indent = line.startswith("  ")
        if is_indent:
            items.append(f'<li class="indent">{stripped}</li>')
        elif i == 0 and first_is_lead:
            items.append(f'<li class="lead">{stripped}</li>')
        else:
            items.append(f'<li>{stripped}</li>')
    return f'<ul class="findings">{"".join(items)}</ul>' if items else ""


# ── section meta: icons + descriptions (BL-127) ──────────────────────────────

_SECTION_ICON: dict[str, str] = {}

_SECTION_DESC: dict[str, str] = {
    "Cluster Overview":          "Databases and collections discovered in this cluster",
    "Server Health":             "MongoDB version, uptime, and disk utilization",
    "Replication Health":        "Replica set topology, member lag, and oplog coverage",
    "Storage & Capacity":        "Data size, index size, and per-collection storage breakdown",
    "Backup & Recovery":         "Backup cursor status and oplog point-in-time recovery window",
    "Query Performance":         "Slow queries, COLLSCAN operations, and profiler configuration",
    "Missing Indexes":           "Collections with slow queries that lack supporting indexes",
    "Unused Indexes":            "Indexes with zero reads since last restart — candidates for removal",
    "Operations":                "Memory, cache, lock contention, and long-running operations",
    "Connections & Concurrency": "Active connections, WiredTiger tickets, and lock queue depth",
    "Infrastructure":            "CPU, I/O wait, system memory, and disk IOPS (requires Ops Manager)",
}


# ── section card (BL-083) ──────────────────────────────────────────────────────

def _section_card(section: ReportSection, anchor_id: str, display_name: str | None = None) -> str:
    """Render one section card with a collapsible Details panel (BL-083).

    Summary findings (non-indented) are always visible.
    Detail findings (leading spaces) are wrapped in <details open> when the
    section is WARNING/CRITICAL and <details> (collapsed) when OK.
    """
    name       = display_name or section.name
    border_cls = _SECTION_BORDER[section.severity]

    # Split findings: summary (non-indented) stays above fold; detail (indented) goes into <details>
    summary_lines: list[str] = []
    detail_lines:  list[str] = []
    for line in section.findings:
        if not line.strip():
            continue
        if line.startswith("  "):
            detail_lines.append(line)
        else:
            summary_lines.append(line)

    is_warn_or_crit = section.severity != HealthSeverity.OK

    # BL-130: use timeline layout for WARN/CRIT summary findings, bullet list for OK
    if is_warn_or_crit and summary_lines:
        tl_cls = "ftl-crit" if section.severity == HealthSeverity.CRITICAL else "ftl-warn"
        tl_items = []
        for i, line in enumerate(summary_lines):
            item_cls = "ft-lead" if i == 0 else ""
            tl_items.append(f'<div class="ft-item {item_cls}">{line.strip()}</div>')
        summary_html = f'<div class="findings-timeline {tl_cls}">{"".join(tl_items)}</div>'
    else:
        summary_html = _findings_list(summary_lines, first_is_lead=is_warn_or_crit)

    if detail_lines:
        open_attr  = " open" if is_warn_or_crit else ""
        n_det = len(detail_lines)
        det_label = f"{n_det} detail{'s' if n_det != 1 else ''}"
        detail_html = (
            f'<details class="findings-details"{open_attr}>'
            f'<summary><span class="det-arrow">▶</span>{det_label}</summary>'
            f'{_findings_list(detail_lines)}'
            f'</details>'
        )
    else:
        detail_html = ""

    # BL-127: icon + description
    icon_html = _SECTION_ICON.get(section.name, "")
    if icon_html:
        icon_html = f'<span class="section-icon">{icon_html}</span>'
    desc = _SECTION_DESC.get(section.name, "")
    desc_html = f'<div class="section-desc">{desc}</div>' if desc else ""

    return (
        f'<div class="section {border_cls}" id="{anchor_id}">'
        f'<div class="section-hd">'
        f'{icon_html}'
        f'<span class="section-title">{name}</span>'
        f'<span class="tag {_TAG[section.severity]}">{_TAG_LABEL[section.severity]}</span>'
        f'</div>'
        f'{desc_html}'
        f'{_metric_grid(section)}'
        f'{summary_html}'
        f'{detail_html}'
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
        anchor, display = _SECTION_META.get(s.name, ("", s.name))
        cls   = _ALERT[s.severity]
        first = s.findings[0].strip() if s.findings else "See section for details."
        desc_lines = [l.strip() for l in s.findings[1:] if l.strip() and not l.startswith("  ")]
        body_html = (
            f'<div class="alert-body">{desc_lines[0]}</div>'
            if desc_lines else ""
        )
        jump_html = (
            f'<a class="alert-jump" href="#{anchor}">View section</a>'
            if anchor else ""
        )
        boxes.append(
            f'<div class="alert {cls}">'
            f'<div class="alert-title">{display} — {first}</div>'
            f'{body_html}'
            f'{jump_html}'
            f'</div>'
        )

    action_guide = (
        f'<div style="font-size:11px;color:var(--t3);margin-bottom:12px;font-family:var(--mono);">'
        f'<span style="color:var(--red)">Critical</span> = act today &nbsp;·&nbsp; '
        f'<span style="color:var(--amber)">Warning</span> = act this week'
        f'</div>'
    )
    return (
        f'<div class="section" id="alerts">'
        f'<div class="section-hd">'
        f'<span class="section-title">Active alerts</span>'
        f'<span class="tag {_TAG[worst]}">{n} issue{"s" if n != 1 else ""}</span>'
        f'</div>'
        + action_guide
        + "".join(boxes)
        + "</div>"
    )


# ── placeholder section ───────────────────────────────────────────────────────

def _placeholder_section(anchor_id: str, title: str, unavailable: list[str], backlog_id: str) -> str:
    """BL-121: collapsed single-line stub; expands to full detail on click."""
    items_html = "".join(f'<li>{m}</li>' for m in unavailable)
    uid = anchor_id.replace("-", "_")
    return (
        f'<div class="section" id="{anchor_id}">'
        f'<div class="section-hd">'
        f'<span class="section-title" style="color:var(--t3);font-weight:400">{title}</span>'
        f'<span class="tag tag-gray">Not configured</span>'
        f'</div>'
        f'<div class="placeholder-stub">'
        f'Requires Ops Manager — metrics not available.'
        f'<a class="pl-expand" href="#" onclick="togglePlaceholder(\'{uid}\');return false;">Show details</a>'
        f'</div>'
        f'<div class="placeholder-full" id="ph_{uid}">'
        f'<div class="placeholder">'
        f'<div class="placeholder-title">Metrics not accessible without Ops Manager:</div>'
        f'<ul class="placeholder-list">{items_html}</ul>'
        f'<div class="placeholder-ref">Configure: <code>ops_manager.url</code> + API keys in agent_config.yaml</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )


# ── recommendations ───────────────────────────────────────────────────────────

def _health_summary_html(report: "HealthCheckReport") -> str:
    """LLM-generated natural language health summary block."""
    if not report.health_summary:
        return ""
    import html as _html
    return (
        f'<div class="health-summary">'
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

    sorted_recs = sorted(recs, key=lambda r: _PRI_ORDER.get(r.priority, 9))

    # BL-126: inline priority badge per row — no tier-header separator rows
    rows: list[str] = []
    for rec in sorted_recs:
        pri_cls = _REC_PRI.get(rec.priority, "rp4")
        rows.append(
            f'<tr>'
            f'<td><span class="rec-p {pri_cls}">{rec.priority}</span></td>'
            f'<td><code class="rec-action">{_html.escape(rec.action)}</code></td>'
            f'<td class="rec-evidence-cell">{_html.escape(rec.evidence)}</td>'
            f'</tr>'
        )

    worst_pri = "tag-red" if any(r.priority in ("P0", "P1") for r in recs) else "tag-amber"
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
        f'<th>Priority</th><th>Action</th><th>Rationale</th>'
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

    # Cluster Overview — section card only, no separate KPI strip (signals are in the metric grid)
    cluster_overview_html = card("Cluster Overview") if "Cluster Overview" in by_name else ""

    return "".join([
        cluster_overview_html,
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
        card("Backup & Recovery"),
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
}, { threshold: 0.15, rootMargin: '0px 0px -55% 0px' });

sections.forEach(s => observer.observe(s));
navLinks.forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    const t = document.querySelector(link.getAttribute('href'));
    if (t) t.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
});

// BL-110: copy-to-clipboard for Action Plan commands
function copyAction(btn, text) {
  if (!navigator.clipboard) return;
  navigator.clipboard.writeText(text).then(function() {
    btn.textContent = '✓ Copied';
    btn.classList.add('copied');
    setTimeout(function() {
      btn.textContent = 'Copy';
      btn.classList.remove('copied');
    }, 1500);
  });
}

// BL-118: light/dark theme toggle
function toggleTheme() {
  var root = document.documentElement;
  var current = root.getAttribute('data-theme');
  var next = current === 'light' ? 'dark' : 'light';
  root.setAttribute('data-theme', next);
  try { localStorage.setItem('dba-theme', next); } catch(e) {}
}
(function() {
  try {
    var saved = localStorage.getItem('dba-theme');
    if (saved) document.documentElement.setAttribute('data-theme', saved);
  } catch(e) {}
})();

// BL-121: placeholder section expand/collapse
function togglePlaceholder(uid) {
  var el = document.getElementById('ph_' + uid);
  if (!el) return;
  el.classList.toggle('open');
  var link = el.previousElementSibling && el.previousElementSibling.querySelector('.pl-expand');
  if (link) link.textContent = el.classList.contains('open') ? 'Hide details' : 'Show details';
}
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
    <div class="report-sub">{ts}{f" &middot; completed in {report.elapsed_seconds:.0f}s" if report.elapsed_seconds else ""}</div>
  </div>

  {_recommendations_html(report)}

  {_build_content(report)}

  <div class="report-footer">
    mongodb-dba-agent · {cluster_label} · {ts}
  </div>

</main>
</div>
<script>{_JS}</script>
</body>
</html>"""
