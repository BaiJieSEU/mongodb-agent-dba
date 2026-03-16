# MongoDB DBA Agent — Product Requirements

Version: 0.2.0 | Updated: 2026-03-16

---

## 1. Product Goal

> **The agent must be able to perform a comprehensive MongoDB cluster health check,
> produce a structured report with findings and recommendations, and run that check
> automatically on a configurable schedule.**

This is the north-star requirement. Every capability gap and backlog item below
should be evaluated against whether it moves the system closer to this goal.

---

## 2. What "Cluster Health Check" Means

A complete health check covers six dimensions. Each dimension has a set of
signals the agent must read and interpret.

### 2.1 Query Performance
| Signal | Source | Current support |
|---|---|---|
| Slow queries (≥ threshold ms) | `system.profile` | ✅ v0.2.0 |
| Query execution plans | MCP `explain` | ✅ v0.2.0 |
| Currently running long operations | `db.currentOp()` | ❌ missing |
| Aggregation pipeline efficiency | MCP `explain` on aggregations | ❌ missing |
| Query plan cache poisoning | `planCacheStats` | ❌ missing |

### 2.2 Index Health
| Signal | Source | Current support |
|---|---|---|
| Index inventory per collection | MCP `collection-indexes` | ✅ v0.2.0 |
| Missing indexes (from slow queries) | derived | ✅ basic |
| Unused indexes | `$indexStats` aggregation | ❌ missing |
| Duplicate / redundant indexes | derived from index list | ❌ missing |
| ESR ordering violations | LLM analysis of index fields | ⚠️ inconsistent |

### 2.3 Storage & Capacity
| Signal | Source | Current support |
|---|---|---|
| Collection sizes and doc counts | `collStats` / `dbStats` | ❌ missing |
| Storage engine cache hit ratio | `serverStatus.wiredTiger.cache` | ❌ missing |
| Disk usage vs. available | `dbStats.fsUsedSize` | ❌ missing |
| Collection growth trend (over time) | snapshot comparison in memory | ❌ missing |
| Large documents / oversized fields | sampling + doc size | ❌ missing |

### 2.4 Replication Health
| Signal | Source | Current support |
|---|---|---|
| Replica set member states | `replSetGetStatus` | ❌ missing |
| Replication lag (primary → secondary) | `replSetGetStatus.optimeDate` delta | ❌ missing |
| Oplog window (hours of oplog remaining) | `local.oplog.rs` stats | ❌ missing |
| Hidden / delayed members | `replSetGetStatus` members | ❌ missing |

### 2.5 Server & Connection Health
| Signal | Source | Current support |
|---|---|---|
| Active connections vs. pool limit | `serverStatus.connections` | ❌ missing |
| Lock wait time (global / collection) | `serverStatus.locks` | ❌ missing |
| Page faults and memory pressure | `serverStatus.extra_info` | ❌ missing |
| Profiler enabled and configured | `db.getProfilingStatus()` | ❌ missing |
| Server uptime and version | `serverStatus.uptime`, `buildInfo` | ❌ missing |

### 2.6 Security Posture (future scope)
| Signal | Source | Current support |
|---|---|---|
| Authentication enabled | `getCmdLineOpts` | ❌ out of scope |
| Users with excessive privileges | `db.getUsers()` | ❌ out of scope |
| TLS in use | `serverStatus.security` | ❌ out of scope |

---

## 3. Scheduling Requirement

The health check must be runnable in two modes:

**Interactive mode** (existing)
```bash
python src/main_agentic.py "run health check"
```
Produces a full report to stdout. Stores the run in memory.

**Scheduled mode** (to build)
```
# config/agent_config.yaml
schedule:
  enabled: true
  cron: "0 */6 * * *"   # every 6 hours
  report_output: file    # file | stdout | webhook
  alert_on_severity: warning  # info | warning | critical
```
The scheduler calls the same health-check pipeline, writes a timestamped report
to disk (or posts to a webhook), and stores the run in memory for trend comparison.

---

## 4. Current State vs. Goal

| Health check dimension | v0.2.0 coverage | Gap |
|---|---|---|
| Query performance | Partial (profiler only) | `currentOp`, aggregation plans, plan cache |
| Index health | Partial (inventory only) | Usage stats, duplicates, ESR validation |
| Storage & capacity | None | All signals missing |
| Replication health | None | All signals missing |
| Server & connections | None | All signals missing |
| Scheduling | None | Scheduler, report output, alerting |
| Security posture | None | Deferred — not in current scope |

---

## 5. Honest Assessment: AI-Augmented DBA, Not Autonomous DBA

### Where the agent adds clear value
- Runs continuously at zero marginal cost — a human DBA cannot check the cluster
  every 6 hours at 3am on a Saturday
- Builds institutional memory across investigations that a human DBA captures
  inconsistently in notes or runbooks
- Reduces first-pass triage time from 30 minutes to under 5
- Flags patterns ("this collection was slow last Tuesday too") that are easy to
  miss without structured history

### Where it cannot replace a human DBA

**It cannot remediate.**
The agent is read-only. It can identify that the `users` collection needs an index
on `email` and generate the exact `createIndex` command, but a human must execute it,
choose the right maintenance window, and verify the outcome.

**Root-cause analysis is shallow.**
The LLM reasons over text summaries. It will miss interactions between components —
for example, that cache eviction is being caused by a runaway aggregation that also
explains the replication lag. A human DBA with years of experience will spot that
chain; the agent currently cannot.

**It has no operational context.**
The agent does not know that a deployment is happening tonight, that the batch job
runs on weekends, or that this collection gets 10× traffic on the first of each month.
Without that context, some recommendations will be technically correct but operationally
wrong.

**LLM hallucination risk.**
The agent may recommend an index that already exists, mis-read an execution plan,
or generate MongoDB 4.x syntax on an 8.x server. Every recommendation that leads
to a write operation must be reviewed by a human before execution.

**It cannot handle incidents.**
A human DBA in an outage coordinates with developers, decides whether to roll back a
deployment, interprets cascading failures across multiple systems, and communicates
with stakeholders. None of this is in scope.

### Verdict
The correct framing is: **AI-augmented DBA**. The agent owns the observe-and-diagnose
loop (the repetitive, low-judgment work). The human DBA owns the decide-and-act loop
(the high-judgment, high-consequence work). Together they are more effective than either
alone.

---

## 6. Out of Scope (Current Product)

The following are explicitly excluded from this product's scope to maintain focus:

- Schema design and data-modelling advice
- Backup schedule management and restore testing
- Sharding topology changes and chunk balancing
- Security auditing, privilege reviews, TLS configuration
- Integration with application-layer metrics (APM, tracing)
- Multi-cloud / Atlas Serverless specifics
- Incident command and stakeholder communication
