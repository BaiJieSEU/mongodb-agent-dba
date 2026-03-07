# MongoDB DBA Agent — POC

## Problem Statement

Can Agentic AI replace human MongoDB DBAs for operational tasks 
in Enterprise Advanced environments?

This POC explores one specific workflow: autonomous slow query 
investigation — detecting issues, reasoning about root causes, 
and generating specific fix commands without human input.

The key question: does the agent reason dynamically like a DBA, 
or just follow a fixed script?

## 🎯 POC Objectives

**Primary Goal**: Demonstrate that an AI agent can perform MongoDB performance analysis while being:
- **Autonomous**: Self-directed investigation without human guidance
- **Available 24/7**: No human resource constraints  
- **Consistent quality**: Same analysis approach every time
- **Reasoning-based**: Dynamic problem solving, not scripted responses

## 🚀 Agent Capabilities

### Core Investigation Features
- **Autonomous Analysis**: Agent decides investigation strategy based on findings
- **Profiler Integration**: Automatically fetches slow queries from MongoDB profiler
- **Explain Analysis**: Runs `explain()` on problematic queries to identify bottlenecks
- **Index Optimization**: Detects missing indexes and suggests compound index strategies  
- **Pattern Recognition**: Identifies MongoDB anti-patterns ($where, unanchored regex, collection scans)

### Smart Recommendations
- **Specific Commands**: Copy-paste MongoDB commands, not vague advice
- **Performance Predictions**: Expected improvement assessments
- **Priority Classification**: Critical/High/Medium/Low based on impact

## 🏗 Technical Architecture

### System Overview
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ User Query      │───▶│ LangGraph Agent │───▶│ Analysis Report │
│ "DB is slow?"   │    │ + Local LLM     │    │ + Commands      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────────────────────────┐
                    │     Specialized Analysis Tools     │
                    ├─────────────────────────────────────┤
                    │ SlowQueryFetcher │ QueryExplainer  │
                    │ IndexChecker     │ RecommendationGen│
                    └─────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │ Agent Storage   │    │ Monitored DB    │
                    │ MongoDB:27017   │    │ MongoDB:27018   │
                    └─────────────────┘    └─────────────────┘
```

### Agent-Based Design
- **LangGraph Orchestrator**: Stateful workflow engine coordinating specialized tools
- **Local LLM**: Ollama with qwen2.5-coder:7b for MongoDB-specific code analysis
- **Specialized Tools**: 4 dedicated analyzers for different performance aspects
- **Dual MongoDB Setup**: Separate agent storage and monitored cluster

### Why This Architecture?
- **Data Sovereignty**: LLM runs locally, client data never leaves environment
- **Cost Efficiency**: No per-token charges for high-volume analysis
- **Modularity**: Easy to add new analysis tools or upgrade LLM models
- **Extensible**: Designed to support enterprise deployment patterns

> 📋 **Detailed Architecture**: See [architecture_diagram.md](architecture_diagram.md) for comprehensive system diagrams and component details.

## 📋 Prerequisites

1. **Python 3.11+**
2. **MongoDB 8.0.4** running on both ports 27017 and 27018
3. **Ollama** with qwen2.5-coder:7b model

## 🔧 Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup MongoDB Instances

```bash
# First instance (agent store) - already running on 27017
# Second instance (monitored cluster) 
mongod --port 27018 --dbpath ~/mongodb/data2 --logpath ~/mongodb/logs/mongod2.log --replSet rs1 --fork

# Initialize second replica set
mongosh --port 27018 --eval "rs.initiate({_id: 'rs1', members: [{_id: 0, host: 'localhost:27018'}]})"
```

### 3. Install and Setup Ollama

```bash
# Install Ollama (if not already installed)
# Download from: https://ollama.ai

# Pull the required model
ollama pull qwen2.5-coder:7b

# Start Ollama server
ollama serve
```

### 4. Generate Test Data

```bash
# Create test scenarios with 4 slow query patterns
python3 simulate_load.py
```

## 🎯 Usage Examples

### Basic Performance Investigation
```bash
# Comprehensive investigation with prioritized recommendations
python src/main.py "my database is slow"
```

### Query-Focused Analysis
```bash
# Shows detailed query information
python src/main.py "find the top 3 slow queries"
python src/main.py "check slow queries"
```

### Index-Specific Analysis
```bash
# Focus on index optimization opportunities
python src/main.py "check my indexes"
```

## 📁 Project Structure

```
mongo-dba-agent/
├── src/
│   ├── agent/
│   │   ├── slow_query_agent.py      # Main LangGraph agent
│   │   └── state.py                 # Agent state definitions
│   ├── tools/
│   │   ├── slow_query_fetcher.py    # MongoDB profiler analysis
│   │   ├── query_explainer.py       # Query execution analysis
│   │   ├── index_checker.py         # Index optimization analysis
│   │   └── recommendation_generator.py  # Actionable recommendations
│   ├── models/
│   │   └── query_models.py          # Data models
│   ├── utils/
│   │   ├── mongodb_client.py        # MongoDB connection management
│   │   ├── config_loader.py         # Configuration management
│   │   └── test_data_generator.py   # Test data creation
│   └── main.py                      # CLI entry point
├── config/
│   └── agent_config.yaml           # Configuration file
├── requirements.txt
└── README.md
```

## ⚙️ Configuration

Edit `config/agent_config.yaml`:

```yaml
mongodb:
  agent_store: "mongodb://localhost:27017"
  monitored_cluster: "mongodb://localhost:27018"
  
ollama:
  base_url: "http://localhost:11434"
  model: "qwen2.5-coder:7b"
  
agent:
  slow_query_threshold_ms: 100
  max_queries_to_analyze: 10
  investigation_timeout: 60
```


### 🚀 Next Steps for Production
1. **Enterprise Integration**: MongoDB Ops Manager / Atlas connectivity
2. **Multi-Database Support**: Analyze multiple clusters simultaneously  
3. **Advanced Models**: Integration with GPT-4o for complex scenarios
4. **Security Enhancement**: Enterprise authentication and audit logging
5. **Human-in-the-loop**: Approval workflow for index creation and schema changes

**POC Status**: 🔬 **In Progress** - MVP scope: slow query investigation

## 📝 License

MIT License - see LICENSE file for details.

