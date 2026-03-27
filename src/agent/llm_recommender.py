"""LLM-driven recommendation enrichment for health check reports (BL-034).

Hybrid approach:
  1. Rule-based _build_recommendations() runs first — fast, deterministic, high-confidence.
  2. LLMRecommender.enrich() appends cross-section insights the rule engine misses.

The LLM receives clean structured JSON (section names, severities, signal values vs
thresholds, key findings, existing recommendations). It never touches raw MongoDB output.
All data collection remains deterministic; only recommendation synthesis is LLM-driven.

Failure contract: any exception in enrich() is caught and logged; the existing
rule-based recommendations are returned unchanged so the health check never breaks.
"""
from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, List

from models.health_check_report import HealthCheckReport, HealthSeverity, Recommendation, Signal

if TYPE_CHECKING:
    from utils.config_loader import AppConfig

logger = logging.getLogger(__name__)

# ── threshold direction ────────────────────────────────────────────────────────
# Signals where a value BELOW the threshold is the problem (low = bad).
# All other threshold signals: value ABOVE the threshold is the problem (high = bad).
_BELOW_THRESHOLD_IS_BAD = frozenset({
    "wt_cache_hit_ratio",   # low hit rate = reads hitting disk
    "tickets_reads",        # low remaining tickets = read exhaustion
    "tickets_writes",       # low remaining tickets = write stall
    "oplog_window_hours",   # short window = secondary sync risk
})


def _signal_breached(sig) -> bool:
    """True only if the signal has crossed its threshold in the bad direction."""
    if sig.threshold is None:
        return False
    if not isinstance(sig.value, (int, float)) or not isinstance(sig.threshold, (int, float)):
        return False
    if sig.name in _BELOW_THRESHOLD_IS_BAD:
        return sig.value < sig.threshold
    return sig.value > sig.threshold


# ── system prompt ──────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a senior MongoDB database reliability engineer reviewing a cluster health check.

You will receive a JSON health check report. Each signal includes a "status" field:
  "status": "breached"  — the metric has crossed its threshold in the BAD direction
  "status": "ok"        — the metric is healthy, regardless of its numeric distance from the threshold

CRITICAL RULES — violating these disqualifies your entire response:
1. Only recommend actions for signals where status="breached". A signal with
   status="ok" is HEALTHY. Do NOT act on it, mention it, or use it as supporting
   evidence — even if its value looks numerically far from the threshold.
   Example: memory_resident_mb=41, threshold=4096, status="ok" → healthy, ignore it.
2. Do NOT draw on general MongoDB knowledge to infer problems that are not evidenced
   by a breached signal in the data. If no memory/cache signal is breached, do not
   recommend memory tuning. If no disk signal is breached, do not recommend disk changes.
3. Do NOT recommend "investigate X" or "review X" where X is a metric with status="ok".
   If lock_wait_pct has status="ok", do NOT recommend investigating lock contention.
   If wt_cache_hit_ratio has status="ok", do NOT recommend reviewing cache settings.
   Each action must directly fix the specific breached signal(s) you cite as evidence.

Your task: produce ADDITIONAL recommendations that the rule engine missed.

Focus on:
- Cross-section patterns where MULTIPLE signals are status="breached" together
  (e.g. wt_cache_hit_ratio breached + collscan_count breached → memory/working set issue)
- Operational signals where status=breached: cache hit ratio, lock wait %, page faults,
  memory resident MB — these never produce rule-based recommendations today
- Replication risks: short oplog window combined with high write throughput
- Any CRITICAL or WARNING section with zero existing recommendations
- Prioritise by potential impact: data loss risk > performance > storage waste

Rules:
- Do NOT repeat any recommendation already in existing_recommendations
- Do NOT recommend actions for signals with status="ok"
- Every recommendation must cite specific observed signal values as evidence
- Every action must directly address the breached signal(s) cited — not tangential metrics
- "collection" field: use "db.collection" format for collection-level issues,
  or "cluster" for server-wide configuration issues
- "action" field: be specific and actionable — MongoDB shell commands, config parameter
  names, or clear investigation steps
- "confidence" field: always set to "llm"
- CRITICAL: your ENTIRE response must be a single valid JSON array.
  No preamble. No explanation. No markdown. No headers. Start with [ and end with ].
  If there is nothing to add, respond with exactly: []

Output format (your full response must look exactly like this):
[
  {
    "priority": "P0 | P1 | P2 | P3 | P4",
    "collection": "string",
    "action": "string",
    "evidence": "string — cite specific signal values from the report",
    "confidence": "llm"
  }
]

Priority mapping (use the consequence tier of the section that drives this recommendation):
  P0 — Server Health / Replication: availability or data-loss risk
  P1 — Storage & Capacity / Operations: write stalls, ticket exhaustion, cache pressure
  P2 — Connections & Concurrency / Infrastructure: resource pressure heading toward outage
  P3 — Query Performance / Missing Indexes: slow queries, collection scans
  P4 — Cluster Overview / Unused Indexes: observability, storage waste
"""

# ── report serialiser ──────────────────────────────────────────────────────────

def _report_to_prompt_json(report: HealthCheckReport) -> str:
    """Serialise report to compact JSON for the LLM prompt.

    Only includes WARNING/CRITICAL sections — OK sections have no actionable signals.
    Limits to signals that breach their threshold (or all signals if none do).
    Keeps first 3 non-empty finding lines per section to stay within model context.
    """
    sections = []
    for s in report.sections:
        if s.severity == HealthSeverity.OK:
            continue  # nothing to act on
        # Prefer signals that are actually breached; fall back to all if none are
        breached_sigs = [sig for sig in s.signals if _signal_breached(sig)]
        sig_list = breached_sigs if breached_sigs else s.signals[:6]
        key_findings = [f.strip() for f in s.findings if f.strip()][:3]

        def _sig_dict(sig) -> dict:
            d = sig.to_dict()
            d["status"] = "breached" if _signal_breached(sig) else "ok"
            return d

        sections.append({
            "name": s.name,
            "severity": s.severity.value,
            "signals": [_sig_dict(sig) for sig in sig_list],
            "key_findings": key_findings,
        })

    existing = [
        {
            "priority": r.priority,
            "collection": r.collection,
            "action": r.action,
        }
        for r in report.recommendations
    ]

    return json.dumps({
        "cluster_uri": report.cluster_uri,
        "overall_severity": report.overall_severity.value,
        "sections": sections,
        "existing_recommendations": existing,
    }, indent=2, default=str)


# ── response parser ────────────────────────────────────────────────────────────

_VALID_PRIORITIES = {"P0", "P1", "P2", "P3", "P4"}


def _parse_llm_response(raw: str) -> List[Recommendation]:
    """Extract a JSON array from the LLM response and parse into Recommendation objects.

    Handles:
    - Responses wrapped in markdown code fences (```json ... ```)
    - Extra text before/after the JSON array
    - Missing or invalid fields (skipped gracefully)
    """
    text = raw.strip()

    # Strip qwen3 / chain-of-thought <think>...</think> blocks before parsing
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # Strip markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    # Find the outermost JSON array
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        logger.warning("LLM response contained no JSON array — raw: %.200s", text)
        return []

    try:
        items = json.loads(match.group())
    except json.JSONDecodeError as exc:
        logger.warning("LLM JSON parse error: %s — raw: %.200s", exc, text)
        return []

    recs: List[Recommendation] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        priority = str(item.get("priority", "P3")).upper().strip()
        if priority not in _VALID_PRIORITIES:
            priority = "P3"
        collection = str(item.get("collection", "cluster")).strip()
        action     = str(item.get("action",     "")).strip()
        evidence   = str(item.get("evidence",   "")).strip()
        if not action:
            continue  # skip empty / malformed entries
        recs.append(Recommendation(
            priority=priority,
            collection=collection,
            action=action,
            evidence=evidence,
            confidence="llm",
        ))
    return recs


# ── public class ───────────────────────────────────────────────────────────────

_LLM_ENRICHMENT_TIMEOUT_S = 60   # give the LLM up to 60 s; skip enrichment if exceeded
_TOOLTIP_TIMEOUT_S        = 45   # separate timeout for signal tooltip enrichment


class LLMRecommender:
    """Enriches rule-based health check recommendations with LLM cross-section reasoning."""

    def __init__(self, config: "AppConfig"):
        from utils.llm_factory import build_llm
        self._llm = build_llm(config)

    def enrich(self, report: HealthCheckReport) -> List[Recommendation]:
        """Return report.recommendations + any new LLM-generated ones.

        The report must already have rule-based recommendations attached
        (health_check_runner calls _build_recommendations first, then this).

        Runs in a background thread with a hard timeout so a slow or unresponsive
        LLM never blocks the health check pipeline.  On timeout or any failure,
        returns report.recommendations unchanged — enrichment is always best-effort.
        """
        import concurrent.futures

        def _invoke() -> List[Recommendation]:
            summary  = _report_to_prompt_json(report)
            prompt   = f"{_SYSTEM_PROMPT}\n\nHealth Check Report:\n{summary}"
            raw      = self._llm.invoke(prompt)
            new_recs = _parse_llm_response(raw)
            if new_recs:
                logger.info("LLM enrichment produced %d additional recommendation(s)", len(new_recs))
            else:
                logger.info("LLM enrichment: no additional recommendations")
            return report.recommendations + new_recs

        import threading

        result_box: list = [None]
        error_box:  list = [None]

        def _run() -> None:
            try:
                result_box[0] = _invoke()
            except Exception as exc:
                error_box[0] = exc

        # daemon=True: thread is killed automatically when the main process exits,
        # so a slow LLM never keeps the process alive after the report is saved.
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=_LLM_ENRICHMENT_TIMEOUT_S)

        if t.is_alive():
            logger.warning(
                "LLM enrichment timed out after %ds — using rule-based recommendations only",
                _LLM_ENRICHMENT_TIMEOUT_S,
            )
            return report.recommendations
        if error_box[0] is not None:
            logger.warning("LLM recommendation enrichment failed (non-fatal): %s", error_box[0])
            return report.recommendations
        return result_box[0]

    def generate_health_summary(self, report: HealthCheckReport) -> str:
        """Return a 2–3 sentence consequence-focused summary of the cluster's health.

        Framed around what will happen to the business if each issue is ignored,
        prioritised by ticket tier (P0 = data loss / outage risk first).
        The summary explicitly states the score and names the tier(s) that drove the penalty.
        Falls back to a deterministic template on timeout or LLM error (BL-090).
        """
        import threading, re as _re
        from utils.html_reporter import SECTION_TIER, _TIER_LABEL, _health_score, _TIER_PENALTY

        _TIER_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
        _CONSEQUENCE = {
            "P0": "risks data loss or cluster outage",
            "P1": "risks write failures or data unavailability",
            "P2": "risks performance degradation toward outage",
            "P3": "degrades query performance but cluster stays up",
            "P4": "reduces observability only",
        }

        score = _health_score(report)

        # Build tier → worst severity and penalty breakdown for the prompt
        tier_severity: dict[str, str] = {}
        for s in report.sections:
            tier = SECTION_TIER.get(s.name, "P4")
            sev  = s.severity.value
            prev = tier_severity.get(tier, "ok")
            if sev == "critical" or (sev == "warning" and prev == "ok"):
                tier_severity[tier] = sev

        penalty_lines = []
        for tier in ["P0", "P1", "P2", "P3", "P4"]:
            sev = tier_severity.get(tier, "ok")
            if sev != "ok":
                p = _TIER_PENALTY[tier][sev]
                penalty_lines.append(
                    f"  {tier} ({_TIER_LABEL[tier]}): {sev.upper()} → −{p} pts"
                )

        # Issue list sorted P0 → P4, only non-OK sections
        issues = []
        for s in sorted(report.sections, key=lambda x: _TIER_ORDER.get(SECTION_TIER.get(x.name, "P4"), 4)):
            if s.severity.value == "ok":
                continue
            tier = SECTION_TIER.get(s.name, "P4")
            issues.append(
                f"[{tier} – {_TIER_LABEL[tier]}] {s.name}: {s.severity.value.upper()} "
                f"— {_CONSEQUENCE[tier]}"
            )

        # Deterministic fallback: used when LLM times out or returns empty (BL-090)
        def _fallback_summary() -> str:
            if not issues:
                return f"Cluster health score: {score}/100 — all sections healthy."
            top = issues[0]  # highest-consequence issue
            parts = [f"Health score {score}/100."]
            parts.append(top.replace("[", "").replace("]", " —"))
            if len(issues) > 1:
                parts.append(
                    f"{len(issues) - 1} additional issue(s) in lower-consequence tiers also require attention."
                )
            return " ".join(parts)

        if not issues:
            return _fallback_summary()

        prompt = (
            "You are a senior MongoDB DBA writing a 2-sentence plain-English health "
            "summary for a cluster report. The audience is a software engineering manager "
            "— not a DBA.\n\n"
            "Rules:\n"
            "- EXACTLY 2 sentences. No more.\n"
            "- Sentence 1: state the health score (X/100), name the highest-consequence issue, "
            "and state the specific business risk if not fixed "
            "(data loss, writes failing, cluster unavailable, failover broken, etc.).\n"
            "- Sentence 2: briefly mention other issues or top action if relevant. "
            "Do NOT re-explain the score or the penalty breakdown.\n"
            "- Be direct and specific. No bullet points. No headers. No markdown.\n\n"
            f"Cluster: {report.cluster_name or report.cluster_uri}\n"
            f"Health score: {score}/100 (started at 100, deductions below)\n"
            f"Score breakdown:\n" + "\n".join(penalty_lines) + "\n"
            f"\nIssues (sorted by consequence):\n"
            + "\n".join(f"  {i}" for i in issues)
            + (
                f"\nTop recommended actions:\n"
                + "\n".join(f"  - {r.action}" for r in report.recommendations[:2])
                if report.recommendations else ""
            )
            + "\n\nWrite the summary now (2–3 sentences):"
        )

        result_box: list = [None]

        def _run() -> None:
            try:
                raw = self._llm.invoke(prompt)
                raw = _re.sub(r"<think>.*?</think>", "", raw, flags=_re.DOTALL).strip()
                raw = _re.sub(r"[#*`]", "", raw).strip()
                result_box[0] = raw
            except Exception as exc:
                logger.warning("Health summary generation failed (non-fatal): %s", exc)

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=30)

        if t.is_alive():
            logger.warning("Health summary timed out — using fallback summary")
            return _fallback_summary()
        return result_box[0] or _fallback_summary()

    def enrich_signal_tooltips(self, report: HealthCheckReport) -> None:
        """Generate LLM contextual interpretations for breached signals and write them
        to Signal.tooltip in-place.  Falls back silently on timeout or error.

        Only breached signals are enriched — healthy signals already have good static
        tooltips from _METRIC_TOOLTIPS.  One LLM call handles all breached signals
        to avoid multiple round-trips.
        """
        import threading
        from utils.html_reporter import _METRIC_TOOLTIPS, _SIGNAL_LABELS

        # Collect all breached signals across sections
        breached: list[dict] = []
        signal_refs: list[Signal] = []
        for section in report.sections:
            for sig in section.signals:
                if _signal_breached(sig):
                    label = _SIGNAL_LABELS.get(sig.name, sig.name.replace("_", " ").title())
                    static_def = _METRIC_TOOLTIPS.get(sig.name, "")
                    breached.append({
                        "signal_name": sig.name,
                        "display_label": label,
                        "value": sig.value,
                        "unit": sig.unit,
                        "threshold": sig.threshold,
                        "section": section.name,
                        "static_definition": static_def,
                    })
                    signal_refs.append(sig)

        if not breached:
            logger.info("Signal tooltip enrichment: no breached signals — skipping LLM call")
            return

        prompt = (
            "You are a senior MongoDB DBA. For each breached metric below, write one concise "
            "sentence (max 25 words) explaining what this specific observed value means for this "
            "cluster — not a generic definition. Cite the actual number. Be direct.\n\n"
            "Return a JSON array with one object per metric, in the same order:\n"
            '[{"signal_name": "...", "interpretation": "..."}]\n\n'
            "Metrics:\n"
            + json.dumps(breached, indent=2)
        )

        result_box: list = [None]
        error_box:  list = [None]

        def _run() -> None:
            try:
                raw = self._llm.invoke(prompt)
                raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw).strip()
                match = re.search(r"\[.*\]", raw, re.DOTALL)
                if match:
                    result_box[0] = json.loads(match.group())
            except Exception as exc:
                error_box[0] = exc

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=_TOOLTIP_TIMEOUT_S)

        if t.is_alive():
            logger.warning("Signal tooltip enrichment timed out — using static tooltips only")
            return
        if error_box[0]:
            logger.warning("Signal tooltip enrichment failed (non-fatal): %s", error_box[0])
            return
        if not result_box[0]:
            return

        # Map results back to Signal objects by signal_name
        by_name = {item["signal_name"]: item.get("interpretation", "") for item in result_box[0] if isinstance(item, dict)}
        for sig in signal_refs:
            interp = by_name.get(sig.name, "")
            if interp:
                sig.tooltip = interp
                logger.info("Signal tooltip enriched: %s → %s", sig.name, interp)
