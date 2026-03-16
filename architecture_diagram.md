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
│                       MCP Tool Execution Layer                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  MCPClient  (src/utils/mcp_client.py)                          │   │
│  │  • Sync wrapper: background thread + asyncio.run()             │   │
│  │  • One MCP subprocess per investigation session                │   │
│  │  • call_tool(name, args)  /  list_tools()                      │   │
│  └──────────────────┬───────────────────────────────────────────────┘   │
│                     │ stdio                                             │
│                     ▼                                                   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  MongoDB MCP Server  (@mongodb-js/mongodb-mcp-server)          │   │
│  │  --readOnly  --connectionString mongodb://localhost:27018       │   │
│  │                                                                 │   │
│  │  list-collections   list-databases   find (system.profile)     │   │
│  │  explain            collection-indexes   connect                │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
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

## MCP Tool Mapping

The agent's logical tools map directly to MongoDB MCP Server operations:

| Agent Tool | MCP Operation | Purpose |
|---|---|---|
| `list_collections` | `list-collections` | Collections in a database |
| `list_databases` | `list-databases` | All available databases |
| `fetch_slow_queries` | `find` on `system.profile` | Profiler slow query data |
| `explain_query` | `explain` | Query execution plan |
| `check_indexes` | `collection-indexes` | Existing indexes on a collection |

The MCP Server runs with `--readOnly` — no writes to the monitored cluster.

### MCPClient Implementation
```
MCPClient(mongodb_uri, read_only=True)
  • __enter__: spawns MCP subprocess, waits for session ready
  • call_tool(name, args) → list[str]  (text content blocks)
  • list_tools() → list[str]
  • __exit__: sends stop sentinel, joins thread
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
- **mcp**: Python MCP client SDK (`mcp.ClientSession`, `mcp.client.stdio`)
- **PyMongo**: MongoDB driver (agent memory store only)
- **QWEN 2.5-coder:7b**: Local LLM for reasoning
- **Rich**: Console output formatting

### Infrastructure
- **MongoDB MCP Server** (`@mongodb-js/mongodb-mcp-server`): All database operations on monitored cluster
- **Node.js 18+**: Runtime for MongoDB MCP Server
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