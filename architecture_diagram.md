# MongoDB DBA AI Agent - Architecture Diagram

## High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           User Interface Layer                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  👤 DBA/Engineer                                                        │
│      │                                                                  │
│      │ "Why is my database slow?"                                       │
│      │                                                                  │
│      ▼                                                                  │
│  ┌─────────────────┐                                                    │
│  │   CLI Interface │                                                    │
│  │  (src/main.py)  │                                                    │
│  └─────────────────┘                                                    │
└─────────────────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        AI Agent Orchestration Layer                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                   LangGraph Agent Orchestrator                 │   │
│  │                  (src/agent/slow_query_agent.py)               │   │
│  │                                                                 │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │   │
│  │  │ User Query  │─▶│ Investigation│─▶│ Tool        │─▶│ Report  │ │   │
│  │  │ Analysis    │  │ Planning     │  │ Execution   │  │ Generation│ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                │                                        │
│                                ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Local LLM (Ollama)                          │   │
│  │                   qwen2.5-coder:7b                             │   │
│  │                 (localhost:11434)                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Specialized Analysis Tools Layer                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌─────────┐│
│  │ SlowQueryFetcher│  │ QueryExplainer │  │ IndexChecker   │  │ Recommendation│
│  │                │  │                │  │                │  │ Generator │
│  │ • Time-anchored│  │ • explain()    │  │ • Index coverage│  │ • Specific│
│  │   queries      │  │   analysis     │  │   analysis     │  │   commands│
│  │ • Deduplication│  │ • Performance  │  │ • ESR rules    │  │ • Priority│
│  │ • Pattern      │  │   metrics      │  │ • Missing      │  │   classification│
│  │   grouping     │  │ • Stage        │  │   indexes      │  │ • Impact  │
│  │                │  │   identification│  │                │  │   prediction│
│  └────────────────┘  └────────────────┘  └────────────────┘  └─────────┘│
│         │                     │                     │               │  │
│         │                     │                     │               │  │
│         ▼                     ▼                     ▼               ▼  │
└─────────────────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          Data Sources Layer                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────┐              ┌─────────────────────┐          │
│  │   Agent Storage     │              │  Monitored Cluster  │          │
│  │  MongoDB (rs0)      │              │  MongoDB (rs1)      │          │
│  │  localhost:27017    │              │  localhost:27018    │          │
│  │                     │              │                     │          │
│  │ • Agent state       │              │ • system.profile    │          │
│  │ • Investigation     │              │ • Slow queries      │          │
│  │   history           │              │ • Performance data  │          │
│  │ • Configuration     │              │ • Index information │          │
│  └─────────────────────┘              └─────────────────────┘          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Detailed Component Architecture

### Agent Workflow Data Flow

```
                    User Query
                        │
                        ▼
    ┌─────────────────────────────────────────────────────────┐
    │               Intent Analysis                           │
    │  • Parse user request                                   │
    │  • Determine investigation strategy                     │
    │  • Set query parameters                                 │
    └─────────────────────────────────────────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────────────────────┐
    │             Slow Query Fetching                         │
    │  • Connect to monitored cluster profiler               │
    │  • Apply time-anchored window                           │
    │  • Fetch queries above threshold (5ms)                 │
    │  • Deduplicate similar patterns                         │
    └─────────────────────────────────────────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────────────────────┐
    │              Query Explanation                          │
    │  • Run explain() on each slow query                    │
    │  • Extract execution statistics                         │
    │  • Identify scan types (COLLSCAN vs IXSCAN)            │
    │  • Calculate efficiency metrics                         │
    └─────────────────────────────────────────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────────────────────┐
    │              Index Analysis                             │
    │  • Check existing index coverage                        │
    │  • Apply ESR optimization rules                         │
    │  • Suggest missing indexes                              │
    │  • Detect anti-patterns                                 │
    └─────────────────────────────────────────────────────────┘
                        │
                        ▼
    ┌─────────────────────────────────────────────────────────┐
    │           Recommendation Generation                     │
    │  • Create specific MongoDB commands                     │
    │  • Classify priority levels                             │
    │  • Predict performance improvements                     │
    │  • Format human-readable output                         │
    └─────────────────────────────────────────────────────────┘
                        │
                        ▼
                   Final Report
```

## Tool Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Tool Registry                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐    ┌──────────────────┐                  │
│  │  Tool Protocol   │    │  Tool Registry   │                  │
│  │  Interface       │◄──►│  Manager         │                  │
│  └──────────────────┘    └──────────────────┘                  │
│            │                       │                           │
│            ▼                       ▼                           │
│  ┌──────────────────┐    ┌──────────────────┐                  │
│  │ SlowQueryFetcher │    │ QueryExplainer   │                  │
│  │ Tool             │    │ Tool             │                  │
│  └──────────────────┘    └──────────────────┘                  │
│            │                       │                           │
│            ▼                       ▼                           │
│  ┌──────────────────┐    ┌──────────────────┐                  │
│  │ IndexChecker     │    │ Recommendation   │                  │
│  │ Tool             │    │ Generator Tool   │                  │
│  └──────────────────┘    └──────────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                     Application Layer                          │
│  • Python 3.11+                                                │
│  • Rich CLI for formatting                                     │
│  • Pydantic for data validation                                │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│                       AI/LLM Layer                             │
│  • LangGraph (workflow orchestration)                          │
│  • LangChain Core (tool integration)                           │
│  • Ollama (local LLM serving)                                  │
│  • qwen2.5-coder:7b (specialized code model)                   │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│                      Database Layer                            │
│  • PyMongo (MongoDB driver)                                    │
│  • MongoDB 8.0.4 (database engine)                             │
│  • Replica Sets (rs0, rs1)                                     │
│  • Profiler Collection (system.profile)                        │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                        │
│  • Local development environment                               │
│  • Docker containers (future)                                  │
│  • Kubernetes deployment (production)                          │
└─────────────────────────────────────────────────────────────────┘
```

## Security and Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      Security Boundaries                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Local Environment                          │   │
│  │                                                         │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │   │
│  │  │    User     │    │ AI Agent    │    │ Local LLM   │ │   │
│  │  │  Terminal   │◄──►│ Process     │◄──►│ (Ollama)    │ │   │
│  │  └─────────────┘    └─────────────┘    └─────────────┘ │   │
│  │                             │                           │   │
│  │                             ▼                           │   │
│  │  ┌─────────────┐    ┌─────────────┐                    │   │
│  │  │  MongoDB    │    │  MongoDB    │                    │   │
│  │  │ Agent Store │    │ Monitored   │                    │   │
│  │  │ (rs0:27017) │    │ (rs1:27018) │                    │   │
│  │  └─────────────┘    └─────────────┘                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  • No external API calls                                       │
│  • All data processing local                                   │
│  • Client data never leaves environment                        │
│  • Encrypted inter-service communication                       │
└─────────────────────────────────────────────────────────────────┘
```

## Future Production Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Enterprise Deployment                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │   Web Portal    │    │   API Gateway   │                    │
│  │   Dashboard     │◄──►│   Load Balancer │                    │
│  └─────────────────┘    └─────────────────┘                    │
│                                   │                            │
│                                   ▼                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │             Kubernetes Cluster                         │   │
│  │                                                         │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │ Agent Pod 1 │  │ Agent Pod 2 │  │ Agent Pod N │    │   │
│  │  │             │  │             │  │             │    │   │
│  │  │ • LangGraph │  │ • LangGraph │  │ • LangGraph │    │   │
│  │  │ • Local LLM │  │ • Cloud LLM │  │ • Custom LLM│    │   │
│  │  │ • Tools     │  │ • Tools     │  │ • Tools     │    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                   │                            │
│                                   ▼                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │               MongoDB Atlas / Ops Manager               │   │
│  │                                                         │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │ Cluster A   │  │ Cluster B   │  │ Cluster C   │    │   │
│  │  │ Production  │  │ Staging     │  │ Development │    │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```