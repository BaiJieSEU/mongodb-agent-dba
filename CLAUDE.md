# MongoDB DBA Agent — Memory-Enhanced Agentic AI

This project is an agentic AI system for MongoDB database administration with persistent memory capabilities that learns from past investigations.

## Environment Setup

### MongoDB Dual-Instance Setup
- **Agent Memory Store**: Port 27017 (rs0) - Stores agent investigations and memory
- **Monitored Database**: Port 27018 (rs1) - Target database for analysis
- **MongoDB Version**: 8.0.4 Community Server
- **Installation Location**: `~/mongodb/`

### Configuration
- **Memory Store**: `~/mongodb/config/mongod.conf` (port 27017)
- **Monitored DB**: `~/mongodb/config/mongod2.conf` (port 27018)
- **Agent Config**: `config/agent_config.yaml`

## Development Rules
- Never claim success without running end-to-end tests
- After every change, verify with: `python src/main_agentic.py "my database is slow"`
- Test memory persistence across multiple investigations
- Ensure LLM reasoning drives tool selection (no hardcoded workflows)

## Current Implementation Status

### ✅ Completed: Agentic AI Architecture

**Core Intelligence:**
- **IntelligentAgenticDBAAgent** (`src/agent/intelligent_agentic_agent.py`)
  - Intent classification using LLM (DIRECT_ANSWER, DATABASE_METADATA, PERFORMANCE_ANALYSIS)
  - Dynamic tool selection based on semantic reasoning
  - Memory-aware response generation with historical context
  - No hardcoded rules - all decisions driven by LLM

**Memory System:**
- **AgentMemory** (`src/memory/agent_memory.py`)
  - MongoDB-based persistent storage with TTL expiration
  - Investigation history (30-day TTL)
  - Performance issue tracking (90-day TTL)
  - User context and pattern learning
  - Recurring issue detection

**Analysis Tools:**
- **SlowQueryFetcher** - Profiler data analysis with time windows and deduplication
- **QueryExplainer** - explain() analysis and execution statistics  
- **IndexChecker** - Index coverage analysis and ESR optimization
- **MetadataInspector** - Database and collection information

### ✅ CLI Interface
- **Main Entry Point**: `src/main_agentic.py`
- Rich console output with prerequisites checking
- Handles natural language queries
- Memory context integration

## Testing Protocol

### Current Test Cases
1. **Metadata Questions**:
   ```bash
   source venv/bin/activate && python src/main_agentic.py "how many collections do I have"
   ```
   Expected: Agent uses MetadataInspector tool, shows collection count

2. **Performance Analysis**:
   ```bash
   source venv/bin/activate && python src/main_agentic.py "my database is slow"
   ```
   Expected: Agent uses SlowQueryFetcher + QueryExplainer + IndexChecker, provides recommendations

3. **Memory Testing**:
   ```bash
   # Run first investigation
   python src/main_agentic.py "check slow queries"
   # Run second investigation - should reference previous findings
   python src/main_agentic.py "my users collection is still slow"
   ```
   Expected: Second investigation references past investigation in memory

4. **General Conversation**:
   ```bash
   python src/main_agentic.py "what's your name"
   ```
   Expected: Direct answer without database tools

### Prerequisites Verification
```bash
# Check MongoDB instances
lsof -i :27017  # Agent memory store
lsof -i :27018  # Monitored cluster

# Check Ollama
curl http://localhost:11434/api/tags

# Verify test data exists
python3 -c "
import pymongo
client = pymongo.MongoClient('mongodb://localhost:27018/')
db = client['testdb']
print(f'Users collection: {db.users.count_documents({})} documents')
print(f'Products collection: {db.products.count_documents({})} documents')
entries = list(db['system.profile'].find({'millis': {'\$gte': 5}}).limit(3))
print(f'Slow queries available: {len(entries)}')
"
```

## Quick Commands

### Start Both MongoDB Instances
```bash
export PATH="$HOME/mongodb/bin:$PATH"
# Start agent memory store
mongod --config ~/mongodb/config/mongod.conf

# Start monitored cluster  
mongod --config ~/mongodb/config/mongod2.conf --fork
```

### Setup Demo Data
```bash
python create_demo_scenario.py
```

### Test Agent
```bash
source venv/bin/activate
python src/main_agentic.py "my database is slow"
```

## Project Structure (Current)

```
mongo-dba-agent/
├── src/
│   ├── agent/
│   │   └── intelligent_agentic_agent.py  # Core agentic AI agent
│   ├── memory/
│   │   ├── __init__.py
│   │   └── agent_memory.py               # MongoDB memory system
│   ├── tools/
│   │   ├── slow_query_fetcher.py         # Profiler analysis
│   │   ├── query_explainer.py            # explain() analysis  
│   │   ├── index_checker.py              # Index optimization
│   │   ├── metadata_inspector.py         # Database metadata
│   │   └── recommendation_generator.py   # Legacy (not used in agentic)
│   ├── models/
│   │   └── query_models.py               # Data structures
│   ├── utils/
│   │   ├── mongodb_client.py             # Database connections
│   │   └── config_loader.py              # Configuration
│   └── main_agentic.py                   # CLI entry point
├── config/
│   └── agent_config.yaml                # System configuration
├── create_demo_scenario.py              # Test data generator
├── requirements.txt                     # Dependencies
├── README.md                            # User documentation
├── architecture_diagram.md              # Technical documentation
└── CLAUDE.md                           # Development context (this file)
```

## Key Features Implemented

### 1. True Agentic Behavior
- **No Hardcoded Workflows**: LLM decides which tools to use based on user intent
- **Semantic Understanding**: Classifies intent without rigid rules
- **Adaptive Responses**: Different output formats for different question types

### 2. Memory Enhancement
- **Persistent Learning**: Stores investigations in MongoDB with TTL
- **Context Building**: References past investigations in new responses
- **Pattern Recognition**: Detects recurring performance issues
- **Historical Awareness**: "I see you asked about this before..." type responses

### 3. Intelligence Examples
```bash
# Metadata question → Uses MetadataInspector
"how many collections do I have"

# Performance question → Uses SlowQueryFetcher + QueryExplainer + IndexChecker  
"my database is slow"

# General question → Direct LLM response, no tools
"what's your name"

# Follow-up with memory → References past investigation
"is my users collection still slow?"
```

## Technology Stack (Actual)

### Core Technologies
- **Python 3.11+**: Application runtime
- **LangChain + Ollama**: LLM integration for reasoning
- **QWEN 2.5-coder:7b**: Local LLM model
- **PyMongo**: MongoDB driver
- **Rich**: Console formatting

### Infrastructure  
- **MongoDB 8.0.4**: Dual-instance setup
- **Ollama**: Local LLM serving
- **YAML**: Configuration management

## Development Notes

### What Makes This "Agentic"
1. **LLM-Driven Decisions**: No if/else logic for tool selection
2. **Natural Language Understanding**: Parses human intent semantically
3. **Memory Integration**: Learns from past interactions
4. **Adaptive Planning**: Investigation strategy varies by question complexity

### Memory System Benefits
- **Learning Over Time**: Agent gets smarter with more investigations
- **Recurring Issue Detection**: "I've seen this pattern before..."
- **Context Continuity**: References past work in recommendations
- **Pattern Recognition**: Builds knowledge base of database issues

### Future Enhancements
- **Multi-Database Support**: Extend to multiple monitored clusters
- **Remote LLM Integration**: Add GPT/Claude options alongside local LLM
- **MongoDB Enterprise**: Integrate with Ops Manager and Atlas
- **Web Interface**: Replace CLI with dashboard

## Troubleshooting

### Agent Not Starting
1. Check MongoDB instances: `lsof -i :27017 && lsof -i :27018`
2. Check Ollama: `curl http://localhost:11434/api/tags`
3. Check Python environment: `source venv/bin/activate`

### Memory Not Working
1. Verify agent store connection: MongoDB on port 27017
2. Check agent_memory database exists
3. Look for TTL collections: investigations, performance_issues, user_context

### No Slow Queries Found
1. Generate test data: `python create_demo_scenario.py`
2. Verify profiler enabled: Check system.profile collection on port 27018
3. Lower threshold in config: `slow_query_threshold_ms: 1`

## Current Status: Production Ready POC

**✅ Agentic Intelligence**: LLM-driven reasoning and tool selection working
**✅ Memory System**: Persistent learning with MongoDB storage functional
**✅ Analysis Tools**: All 4 tools integrated and working
**✅ Natural Language**: Intent classification and conversation handling
**✅ Demo Scenarios**: Reproducible test cases with real performance improvements

**Foundation established for memory-enhanced AI assistants that improve database operations through persistent learning.**