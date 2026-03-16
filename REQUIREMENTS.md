# MongoDB DBA Agent — Product Requirements & Critical Analysis

Version: 0.2.0 | Date: 2026-03-16

---

## 1. What This System Does Today

The agent accepts a natural language query, classifies intent via LLM, selects MCP tools,
executes read-only operations against the monitored MongoDB cluster, and synthesises a
response enriched with memory of past investigations.

**Covered tasks (v0.2.0):**

| Task | How |
|---|---|
| Slow query identification | `find` on `system.profile`, filter by `millis` |
| Query execution plan analysis | MCP `explain` |
| Index inventory | MCP `collection-indexes` |
| Database / collection metadata | MCP `list-databases`, `list-collections` |
| Investigation memory | MongoDB TTL store, recurring-issue tracking |
| Natural language interface | LLM intent classification + response synthesis |

---

## 2. Critical Assessment: Can This Replace a Human DBA?

### Short answer: No — not yet, and not for the most consequential tasks.

The system is a capable **read-only diagnostic assistant** for a narrow set of reactive,
query-performance tasks. Below is an honest breakdown of what it can and cannot do compared
to a working DBA.

### 2.1 Where it competes with a human

| Capability | Human DBA | This agent | Notes |
|---|---|---|---|
| Identify slow queries from profiler | ✅ | ✅ | Equivalent on simple cases |
| Read and summarise an execution plan | ✅ | ⚠️ | Agent can read; nuanced plan interpretation still weak |
| Spot missing indexes | ✅ | ✅ | Works for single-field cases |
| Answer "what collections exist?" | ✅ | ✅ | Reliable |
| Remember patterns across sessions | ⚠️ (notes) | ✅ | Agent has structured persistent memory |
| Be available 24 / 7 at zero marginal cost | ❌ | ✅ | Clear advantage |

### 2.2 Where it falls short

**Reactive only — no proactive monitoring**
The agent only acts when queried. A DBA monitors dashboards, sets alerts, and acts
before users notice a problem. This agent has no scheduler, no alerting, no threshold
triggers.

**Read-only — cannot remediate**
All MCP operations are read-only. The agent can recommend `db.users.createIndex({email:1})`
but cannot create it. A human DBA executes the fix, coordinates with a change window,
and verifies the outcome.

**Shallow root-cause analysis**
The LLM reasons over text summaries of tool output, not the raw BSON. It misses:
- Lock contention and wait statistics (`db.currentOp()`, `serverStatus`)
- WiredTiger cache pressure and eviction
- Oplog lag and replication delay
- Long-running transactions blocking other operations
- Query plan cache poisoning

**No schema or data-model advice**
Suggesting that an `orders` collection should embed line-items vs. reference them, or that
a time-series collection would suit a use case better, requires workload understanding that
the agent does not yet build.

**No capacity planning**
The agent cannot project when storage runs out, when RAM becomes insufficient for the
working set, or when a shard needs rebalancing.

**No security or compliance posture**
User privilege audits, role reviews, TLS configuration, field-level encryption, and
audit log analysis are outside scope.

**No backup and recovery**
The agent has no knowledge of backup schedules, retention policies, point-in-time restore
windows, or oplog coverage.

**No operational context**
A human DBA knows that a deployment is happening tonight, that the quarterly batch job
runs on weekends, and that the `orders` collection spikes on Black Friday. The agent
knows only what it can query.

**LLM hallucination risk**
The agent may confidently recommend an index that already exists, misread an execution
plan, or suggest a MongoDB 4.x syntax on an 8.x server. All output must be reviewed
by a human before acting on it.

---

## 3. Task Scope — What Should Be Added

### 3.1 High-priority additions (reactive diagnostics, still read-only)

| Task | MCP / tool needed | Value |
|---|---|---|
| Current operations (`db.currentOp()`) | MCP `runCommand` | Identify running long queries in real time |
| Server status metrics | MCP `runCommand` | Cache hit ratio, connections, page faults |
| Replication lag | MCP `replSetGetStatus` | Detect secondaries falling behind |
| Collection stats (size, avg doc size) | MCP `collStats` | Guide sharding and TTL decisions |
| Aggregation pipeline analysis | MCP `explain` on aggregations | High-value, frequently slow |
| Lock / wait analysis | MCP `serverStatus` locks section | Critical for contention diagnosis |
| Index usage statistics | MCP `$indexStats` aggregation | Find unused indexes to drop |
| Duplicate / redundant index detection | derived from `collection-indexes` output | Common anti-pattern |
| Profiler level check | MCP `runCommand profile -1` | Warn if profiler is off |

### 3.2 Medium-priority (proactive, requires scheduling)

| Task | Approach |
|---|---|
| Scheduled health-check sweeps | Cron/scheduler calling `investigate()` on a cadence |
| Growth trend tracking | Periodic `collStats` snapshots stored in memory store |
| Index fragmentation monitoring | Periodic `validate` command summary |
| Slow-query regression detection | Compare current week's profiler data to last week |
| Alert on anomalies | Threshold checks after each scheduled sweep |

### 3.3 Write-capable tier (requires explicit human approval gate)

| Task | Risk level | Gate needed |
|---|---|---|
| Create recommended index | Medium — may lock large collections | Human approval + change-window check |
| Drop unused index | Low-medium | Human approval |
| Update profiler settings | Low | Human approval |
| Kill a runaway query | High — affects live traffic | Human approval with confirmation |
| Reindex a collection | High | Human approval |

---

## 4. Enhancement Roadmap

### 4.1 Architecture enhancements

**Multi-cluster support**
The current design is hard-coded to one monitored cluster URI. Parameterise the MCP
connection so the agent can switch between clusters within one session.

**Structured tool output parsing**
MCP returns plain-text blocks. The agent parses these with string operations, which
is fragile. Replace with a typed result schema so the LLM receives structured JSON,
reducing hallucination risk.

**Streaming / async responses**
Investigation currently blocks the CLI until all steps complete (can take 60+ seconds).
Stream intermediate results as each tool completes.

**Tool result caching**
`list-collections` and `collection-indexes` rarely change within an investigation.
Cache results for the duration of a session to avoid redundant MCP calls.

### 4.2 Intelligence enhancements

**Better LLM**
`qwen2.5-coder:7b` produces decent but inconsistent JSON. Options:
- Switch to `llama3.1:8b` or `mistral-nemo` locally
- Add Claude or GPT-4o as a configurable remote backend for higher-stakes reasoning

**ESR rule enforcement**
Index recommendations should explicitly validate Equality → Sort → Range field ordering.
Currently the LLM may suggest sub-optimal field order.

**Multi-step reasoning with tool chaining**
After `fetch_slow_queries` returns, the agent should automatically extract the top
offending collection and feed it as a parameter into `check_indexes` and `explain_query`,
rather than relying on the LLM to produce the right parameters on the first pass.

**Confidence scoring on recommendations**
Append a confidence level (high / medium / low) and the evidence behind each
recommendation so the human reviewer can triage quickly.

### 4.3 Operational enhancements

**Approval-gated write actions**
Introduce a second MCP client operating without `--readOnly`, guarded by an explicit
human confirmation step before execution. This would enable the agent to create indexes
after the human approves.

**Web UI / API**
Replace the CLI with a FastAPI backend and a lightweight frontend so multiple users
can query the agent concurrently and review investigation history.

**Alerting integration**
Post investigation summaries to Slack, PagerDuty, or email when a scheduled sweep
detects a new recurring issue or a threshold breach.

**MongoDB Atlas / Ops Manager integration**
Pull metrics from Atlas Data API or Ops Manager REST API as additional data sources,
complementing local profiler data.

**Audit trail**
Every recommendation made and every write executed (once write-capable tier is added)
should be logged immutably for compliance and post-incident review.

---

## 5. Honest Summary

This is a well-structured foundation for an AI-assisted DBA tool. For the specific
task of *reactive slow-query diagnosis on a single MongoDB cluster*, it is genuinely
useful and reduces the time a human needs to spend on first-pass triage.

It is not a DBA replacement. The tasks a DBA spends most of their time on —
capacity planning, change management, backup ownership, security posture, incident
command during an outage, and architectural guidance — are entirely outside the
current scope. The agent also cannot act on its own findings; every recommendation
requires human execution.

The correct framing is: **AI-augmented DBA**, not autonomous DBA. The agent handles
the repetitive read-and-diagnose loop so the human DBA can focus on remediation,
planning, and decisions that require context no tool can acquire automatically.
