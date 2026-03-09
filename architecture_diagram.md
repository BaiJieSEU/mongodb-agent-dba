# MongoDB DBA Agent — Architecture Documentation

## System Overview

Memory-enhanced agentic AI system for MongoDB database administration with intelligent reasoning capabilities.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          User Interface Layer                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  👤 DBA/Engineer                                                        │
│      │                                                                  │
│      │ "my database is slow" / "check slow queries"                     │
│      │                                                                  │
│      ▼                                                                  │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │                    CLI Interface                                │   │
│  │                 main_agentic.py                                │   │
│  │                                                                 │   │
│  │  • Rich console output                                          │   │
│  │  • Command-line argument parsing                                │   │
│  │  • Prerequisites checking                                       │   │
│  └───────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      AI Agent Intelligence Layer                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │              IntelligentAgenticDBAAgent                        │   │
│  │           (intelligent_agentic_agent.py)                       │   │
│  │                                                                 │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │   │
│  │  │   Intent    │─▶│   Memory    │─▶│    Tool     │─▶│Response │ │   │
│  │  │ Analysis    │  │  Context    │  │ Selection   │  │Synthesis│ │   │
│  │  │   (LLM)     │  │  Lookup     │  │   (LLM)     │  │  (LLM)  │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                │                                        │
│                                ▼                                        │
│  ┌───────────────────────────────────────────────────────────────────┐   │
│  │                     QWEN LLM Engine                            │   │
│  │                   qwen2.5-coder:7b                             │   │
│  │                  (Ollama: localhost:11434)                     │   │
│  └───────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       Database Analysis Tools Layer                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌─────────┐│
│  │SlowQueryFetcher│  │ QueryExplainer │  │ IndexChecker   │  │Metadata ││
│  │    (Tool)      │  │     (Tool)     │  │     (Tool)     │  │Inspector││
│  │                │  │                │  │                │  │ (Tool)  ││
│  │• Profiler data │  │• explain() API │  │• Index coverage│  │• Schema ││
│  │• Time windows  │  │• Performance   │  │• ESR analysis  │  │• Collections│
│  │• Deduplication │  │• Execution     │  │• Missing       │  │• Database││
│  │• Pattern match │  │  statistics    │  │  opportunities │  │  metadata││
│  │                │  │• Stage analysis│  │                │  │         ││
│  └────────────────┘  └────────────────┘  └────────────────┘  └─────────┘│
│         │                     │                     │               │  │
│         └─────────────────────┼─────────────────────┼───────────────┘  │
│                               ▼                     ▼                  │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            Data Storage Layer                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────┐  ┌─────────────────────────────┐│
│  │        Agent Memory Store           │  │     Monitored Cluster       ││
│  │      MongoDB (localhost:27017)     │  │   MongoDB (localhost:27018) ││
│  │                                     │  │                             ││
│  │  ┌─────────────────────────────────┐   │  │  ┌─────────────────────────┐ ││
│  │  │ agent_memory database       │   │  │  │    testdb database      │ ││
│  │  │                             │   │  │  │                         │ ││
│  │  │ • investigations (TTL:30d)  │   │  │  │ • users (50k docs)      │ ││
│  │  │ • performance_issues (90d)  │   │  │  │ • products (5k docs)    │ ││
│  │  │ • user_context              │   │  │  │ • system.profile        │ ││
│  │  │                             │   │  │  │                         │ ││
│  │  └─────────────────────────────────┘   │  │  └─────────────────────────┘ ││
│  └───────────────────────────────────────┘  └─────────────────────────────┘│
│                    ▲                                      ▲              │
│                    │                                      │              │
│                    └────── Memory Feedback Loop ──────────┘              │
└─────────────────────────────────────────────────────────────────────────┘
```

## Agentic Intelligence Components

### Intent Classification
The agent analyzes natural language input to determine investigation strategy:

- **DIRECT_ANSWER**: General questions ("what's your name")
- **DATABASE_METADATA**: Information requests ("how many collections")  
- **PERFORMANCE_ANALYSIS**: Performance issues ("database is slow")

### Memory System
MongoDB-based persistent learning across investigations:

```
agent_memory (localhost:27017)
├── investigations        # Complete investigation records (TTL: 30 days)
├── performance_issues    # Recurring slow query tracking (TTL: 90 days)  
└── user_context         # User preferences and patterns
```

### Dynamic Tool Selection
LLM reasons about which tools are needed based on:
- User intent classification
- Historical context from memory
- Question complexity analysis

## Investigation Workflow

```
                    User Query
                        │
                        ▼
    ┌─────────────────────────────────────────────────────────┐
    │               Intent Analysis                           │
    │  • Classify request type (LLM)                          │
    │  • Parse natural language intent                        │
    │  • Determine investigation scope                        │
    └─────────────────────────────────────────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────────────────────┐
    │             Memory Context Lookup                       │
    │  • Retrieve recent investigations                       │
    │  • Find recurring performance issues                    │
    │  • Build contextual background                          │
    └─────────────────────────────────────────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────────────────────┐
    │              Tool Selection & Execution                 │
    │  • Choose appropriate analysis tools (LLM)              │
    │  • Execute selected tools with parameters               │
    │  • Collect and process results                          │
    └─────────────────────────────────────────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────────────────────┐
    │           Response Generation & Memory Storage          │
    │  • Synthesize findings with context (LLM)               │
    │  • Generate memory-aware recommendations                │
    │  • Store investigation for future reference             │
    └─────────────────────────────────────────────────────────┘
                        │
                        ▼
                   Final Report
```

## Tool Architecture

### SlowQueryFetcher Tool
```python
# Analyzes MongoDB profiler data
• Connects to monitored cluster profiler
• Applies configurable time windows  
• Deduplicates similar query patterns
• Returns structured slow query data
```

### QueryExplainer Tool  
```python
# Runs explain() analysis on queries
• Executes db.collection.explain() 
• Extracts execution statistics
• Identifies scan types and efficiency
• Analyzes query execution stages
```

### IndexChecker Tool
```python
# Analyzes index coverage and optimization
• Compares queries against existing indexes
• Applies ESR (Equality, Sort, Range) rules
• Suggests missing index opportunities  
• Detects index anti-patterns
```

### MetadataInspector Tool
```python
# Provides database and collection information
• Retrieves collection statistics
• Analyzes schema patterns
• Reports database metadata
• Supports information queries
```

## Memory Enhancement Features

### Persistent Learning
- **Investigation History**: Tracks all past investigations with TTL expiration
- **Pattern Recognition**: Identifies recurring performance issues
- **Context Building**: Uses historical data to inform new investigations

### Intelligent Recommendations  
- **Memory-Aware Responses**: References past investigations in recommendations
- **Recurring Issue Detection**: Highlights problems seen before
- **Learning Over Time**: Provides increasingly intelligent suggestions

## Technology Stack

### Core Technologies
- **Python 3.11+**: Application runtime
- **LangChain-Ollama**: LLM integration  
- **PyMongo**: MongoDB driver
- **QWEN 2.5-coder:7b**: Local LLM for reasoning
- **Rich**: Console output formatting

### Infrastructure
- **MongoDB 8.0+**: Dual-instance setup (memory + monitored)
- **Ollama**: Local LLM serving
- **YAML Configuration**: Flexible system configuration

## Security & Data Flow

### Local-First Design
- **No External APIs**: All processing happens locally
- **Encrypted Storage**: MongoDB connections use local security
- **Data Isolation**: Memory and monitored databases separated  
- **No Cloud Dependencies**: Complete local operation

### Data Flow Security
```
User Input → Local LLM → Local Tools → Local MongoDB → Local Response
     ▲                                                        │
     └─────────────── No external data transmission ──────────┘
```

## Configuration

### System Configuration
```yaml
mongodb:
  agent_store: "mongodb://localhost:27017"
  monitored_cluster: "mongodb://localhost:27018"
  
ollama:
  base_url: "http://localhost:11434"
  model: "qwen2.5-coder:7b"
  
agent:
  slow_query_threshold_ms: 5
  max_queries_to_analyze: 10
```

### Memory Settings
```yaml
memory:
  investigation_ttl_days: 30
  performance_issue_ttl_days: 90
  max_context_investigations: 5
```

## Production Considerations

### Scalability Extensions
- **Multi-Database Support**: Extend to multiple monitored clusters
- **Remote LLM Integration**: Add cloud LLM options (GPT, Claude)
- **MongoDB Enterprise**: Integrate with Ops Manager and Atlas
- **Web Interface**: Replace CLI with web dashboard

### Enterprise Features
- **Role-Based Access**: Authentication and authorization
- **Audit Logging**: Track all agent investigations  
- **Alert Integration**: Connect to monitoring systems
- **Batch Processing**: Scheduled performance analysis

Foundation architecture for memory-enhanced AI assistants that improve database operations over time.