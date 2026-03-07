# MongoDB DBA Agent - Demo-Robust Time Window Solution

## Problem Statement

**Original Issue**: Agent stability was compromised by time-dependent query fetching logic that would fail when triggered after slow queries "aged out" of the time window.

### Specific Problems:
1. **Time-dependent failures**: Agent using `datetime.utcnow() - timedelta(hours=N)` would find 0 queries if triggered hours/days later
2. **Fragile demos**: Test scenarios would become unusable over time
3. **Inconsistent results**: Same database state would yield different agent results based on when agent was triggered
4. **Duplicate query noise**: Multiple identical query patterns cluttered the analysis

## Solution: Recent Query Anchored Time Window + Deduplication

### Core Innovation
Instead of looking back N hours from "now", the agent now:
1. 🔍 **Finds the most recent slow query** in profiler (regardless of absolute time)
2. ⏰ **Anchors a relative time window** backwards from that point
3. 🔄 **Deduplicates similar patterns** to show diverse query types
4. 📊 **Returns consistent results** regardless of when agent is triggered

### Implementation Details

#### 1. Recent Query Anchored Logic

```python
# OLD APPROACH (Fragile)
end_time = datetime.utcnow()
start_time = end_time - timedelta(hours=hours_back)

# NEW APPROACH (Demo-Robust)  
most_recent_query = db["system.profile"].find_one(
    {"millis": {"$gte": threshold_ms}},
    sort=[("ts", -1)]  # Most recent first
)
anchor_time = most_recent_query.get("ts")
start_time = anchor_time - timedelta(hours=hours_back)
end_time = anchor_time
```

#### 2. Query Deduplication System

**Pattern Grouping**: Queries are grouped by normalized patterns:
- `collection:users|operation:query|query:{email:eq}` 
- `collection:users|operation:query|query:$where`
- `collection:users|operation:query|query:{age:$gt,status:eq}`

**Representative Selection**: From each pattern group, the slowest query is selected as the representative.

**Benefits**:
- Eliminates redundant `{email: "user123@example.com"}` vs `{email: "user456@example.com"}` 
- Shows diverse query performance issues
- Reduces noise while preserving critical patterns

#### 3. Implementation Files

**Modified Files**:
- `src/tools/slow_query_fetcher.py` - Core logic implementation
- `src/agent/slow_query_agent.py` - Agent integration with 2-hour window
- `test_delayed_execution.py` - Comprehensive test cases

## Verification Results

### ✅ Stability Tests Passed

**Recent Query Anchor Logic**: ✅ PASS
- Successfully identifies most recent slow query as anchor point
- Correctly calculates relative 2-hour time window
- Finds queries regardless of absolute timestamps

**Time Independence**: ✅ PASS  
- Agent finds same slow queries regardless of current system time
- Works with queries from hours or days ago

**Deduplication**: ✅ PASS
- Successfully groups similar query patterns
- Reduces result set while preserving diversity
- Shows effectiveness metrics: `Deduplication: X -> Y queries across Z patterns`

### 📊 Agent Output Example

```
INFO     Using time window: 2026-03-06 19:42:23.933000 to 2026-03-06 21:42:23.933000 (anchored to most recent query)             
INFO     Deduplication: 1 -> 1 queries across 1 patterns             
INFO     Found 1 slow queries in testdb (after deduplication)
```

## Technical Benefits

### 🎯 Demo Robustness
- **Agent works consistently** whether triggered immediately or days later
- **Test scenarios remain valid** indefinitely
- **Predictable results** for demonstrations and troubleshooting

### 🔍 Better Analysis Quality
- **Eliminates duplicate noise** - shows one representative per pattern
- **Preserves query diversity** - different problem types still surface
- **Focuses on worst cases** - slowest query from each pattern group

### 📈 Performance Improvements
- **Reduced result processing** - fewer duplicate queries to analyze  
- **Faster deduplication** - pattern-based grouping vs content comparison
- **Cleaner recommendations** - avoids suggesting same fix multiple times

## Configuration

**Default Settings**:
- `hours_back: 2` - Relative time window from most recent slow query
- `threshold_ms: 5` - Minimum execution time to consider "slow"
- `limit: 50` - Maximum deduplicated queries to return

**Adjustable Parameters**:
```yaml
agent:
  slow_query_threshold_ms: 5
  max_queries_to_analyze: 10
  investigation_timeout: 60
```

## Future Enhancements

### Planned Improvements
1. **Configurable deduplication sensitivity** - Allow fine-tuning of pattern matching
2. **Temporal query distribution** - Show how query patterns change over time  
3. **Multi-database correlation** - Find patterns across database clusters
4. **Performance trend analysis** - Track query degradation over the relative window

### Advanced Deduplication Features
1. **Query frequency weighting** - Prioritize patterns that occur frequently
2. **Performance impact scoring** - Weight by total time consumed vs individual execution time
3. **Index utilization correlation** - Group queries by index usage patterns

## Testing Scenarios

### Scenario Validation Matrix

| Test Case | Expected Behavior | Status |
|-----------|------------------|---------|
| **Fresh Queries** | Finds recent slow queries | ✅ PASS |
| **3-Day Delay** | Same results as fresh execution | ✅ PASS |
| **Mixed Time Ranges** | Uses most recent as anchor | ✅ PASS |
| **Deduplication** | Groups identical patterns | ✅ PASS |
| **Empty Profiler** | Graceful handling, no errors | ✅ PASS |

### Test Commands

```bash
# Test current logic
source venv/bin/activate && python src/main.py "check slow queries"

# Test deduplication and time windows  
python test_delayed_execution.py

# Verify profiler data
python3 simulate_load.py
```

## Summary

The new **Recent Query Anchored Time Window + Deduplication** approach transforms the MongoDB DBA Agent from a time-dependent tool into a robust, demo-ready system that provides consistent analysis regardless of when it's triggered.

**Key Achievement**: The agent now finds the same performance issues whether you run it immediately after generating slow queries or 30 days later, making it reliable for demos, production troubleshooting, and automated monitoring.