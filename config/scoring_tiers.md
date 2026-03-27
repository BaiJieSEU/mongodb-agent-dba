# MongoDB DBA Agent — Scoring & Ticket Tier Model

This file is the **authoritative reference** for the consequence-tier model used by the health check.
The corresponding Python dicts in `src/utils/html_reporter.py` must stay in sync with this table.

---

## 1. Tier Definitions

Tiers are ordered by **worst-case consequence if the issue is left unresolved**.

| Tier | Label         | Worst-case consequence |
|------|---------------|------------------------|
| P0   | Data Loss     | Permanent data loss or corruption — unrecoverable |
| P1   | Outage        | Cluster cannot serve reads or writes |
| P2   | Degraded      | Requests succeed but slowly or intermittently |
| P3   | Slow          | Queries are slow; availability not at risk |
| P4   | Observation   | No user impact; visibility / housekeeping only |

---

## 2. Section → Tier Mapping

| Health Check Section       | Tier | Worst-case consequence |
|----------------------------|------|------------------------|
| Replication Health         | P0   | Oplog gap → secondary can't resync → data permanently lost if primary fails |
| Server Health              | P1   | Disk full stops all writes; node failure = cluster unavailable |
| Storage & Capacity         | P1   | Disk exhaustion halts all writes |
| Operations                 | P2   | Ticket exhaustion / cache pressure → requests queue then fail |
| Connections & Concurrency  | P2   | Connection exhaustion / lock contention → requests rejected |
| Infrastructure             | P2   | CPU / IO saturation → requests succeed but slowly |
| Query Performance          | P3   | Slow queries degrade UX; cluster stays up |
| Missing Indexes            | P3   | Collection scans slow queries; no availability risk |
| Cluster Overview           | P4   | Informational only |
| Unused Indexes             | P4   | Storage waste; no operational impact |

---

## 3. Score Penalty Table

One penalty is applied **per tier**, based on the **worst severity** found across all sections
in that tier. Multiple CRITICAL sections in the same tier still count as one penalty.

| Tier | CRITICAL penalty | WARNING penalty |
|------|-----------------|-----------------|
| P0   | −50             | −20             |
| P1   | −40             | −15             |
| P2   | −25             | −10             |
| P3   | −15             | −5              |
| P4   | −5              | −2              |

**Score formula:** `score = max(0, 100 − sum(applied penalties))`

### Examples

| Cluster state | Score |
|---|---|
| All sections OK | 100 |
| Missing Indexes CRITICAL only (P3) | 85 |
| Query Performance WARNING (P3) + Missing Indexes CRITICAL (P3) | 85 (same tier — one penalty) |
| Server Health CRITICAL (P1) + Query WARNING (P3) | 55 |
| Replication CRITICAL (P0) + Query WARNING (P3) | 45 |
| Replication CRITICAL (P0) + Server Health CRITICAL (P1) | 10 |

---

## 4. Recommendation Priority Mapping

Recommendation `priority` (shown in the Action Plan table) equals the **consequence tier
of the section that produced the finding** — P0 through P4.

| Priority | Section(s) | When to act |
|---|---|---|
| P0 | Replication Health | Immediately — data loss risk |
| P1 | Server Health, Storage & Capacity | Today — service will go down |
| P2 | Operations, Connections & Concurrency, Infrastructure | This week — service is degraded |
| P3 | Query Performance, Missing Indexes | Next sprint — queries are slow |
| P4 | Cluster Overview, Unused Indexes | Backlog — housekeeping |

**Key rule:** Priority label is the same P0–P4 vocabulary used everywhere else in the
report — no separate "high/medium/low" scale. A Replication finding is always P0.
A Missing Indexes finding is always P3, regardless of how many collections are affected.

---

## 5. AI Summary Alignment

The LLM health summary must:
1. Lead with the **lowest-tier (highest-consequence) breach** present.
2. State the **specific business consequence** (data loss, writes failing, cluster unavailable).
3. Mention the score and which tier(s) drove the penalty.
4. Not elevate P3/P4 issues above P0/P1 issues.
