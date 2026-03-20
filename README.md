# MongoDB DBA Agent

AI-augmented MongoDB cluster health monitor. Runs a comprehensive 8-section health
check, produces JSON + HTML reports with prioritised recommendations, and answers
natural language queries — backed by persistent memory that learns from past
investigations.

## Current Capabilities (v0.5.0)

| Health check dimension | Status |
|---|---|
| Cluster overview (databases, collections) | ✅ |
| Server health (startup log, db stats) | ✅ |
| Replication health (oplog window, member state) | ✅ |
| Storage & capacity (data size, index size, growth) | ✅ |
| Query performance (slow queries, scan & sort detection) | ✅ |
| Missing index recommendations | ✅ |
| Unused index detection | ✅ |
| Operations (throughput, memory, cache hit ratio, lock wait) | ✅ |
| LLM-enriched cross-section recommendations | ✅ |
| HTML + JSON report output | ✅ |
| Agentic natural language investigation | ✅ |
| Configurable schedule (daemon mode) | 🔲 BL-011 |

## Quick Start

### Step 1 — Install Docker

The agent runs inside Docker, so Docker must be installed first.

**macOS / Windows** — Install Docker Desktop from docker.com. It includes everything needed.

**Linux (Ubuntu / Debian)**
```bash
curl -fsSL https://get.docker.com | sh
sudo apt-get install -y docker-compose-plugin
# Allow running docker without sudo (log out and back in after this):
sudo usermod -aG docker $USER
newgrp docker
```

**Linux (RHEL / CentOS / Amazon Linux 2023)**
```bash
sudo yum install -y docker docker-compose-plugin
sudo systemctl enable --now docker
# Allow running docker without sudo (log out and back in after this):
sudo usermod -aG docker $USER
newgrp docker
```

**Linux (Amazon Linux 2)**
```bash
sudo amazon-linux-extras install docker -y
sudo systemctl enable --now docker
# Install Compose plugin manually:
COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep tag_name | cut -d'"' -f4)
sudo curl -SL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-$(uname -m)" -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
# Allow running docker without sudo (log out and back in after this):
sudo usermod -aG docker $USER
newgrp docker
```

Verify the installation:
```bash
docker --version
docker compose version
```

---

### Step 2 — Download the app

Install git if not already present:
```bash
# Ubuntu / Debian
sudo apt-get install -y git

# RHEL / CentOS / Amazon Linux
sudo yum install -y git
```

The following command downloads the code into a new folder called `mongodb-agent-dba`:
```bash
git clone https://github.com/BaiJieSEU/mongodb-agent-dba
cd mongodb-agent-dba
```

Create your configuration file (this is where you will put your secrets):
```bash
cp .env.example .env
```

Build the Docker image:
```bash
docker compose build
```

---

### Step 3 — Choose and configure an LLM

The agent needs a language model to analyse data and generate recommendations.
Open `.env` in a text editor and add the lines for your chosen provider.

**Option A — Anthropic API**

Get your API key from console.anthropic.com → **API Keys**. Add to `.env`:
```
AGENT_LLM_PROVIDER=anthropic
AGENT_ANTHROPIC_API_KEY=<your Anthropic API key>
```

**Option B — Ollama (runs locally, no data sent to the cloud)**

Add to `.env`:
```
AGENT_LLM_PROVIDER=ollama
```

No API key needed. Start the Ollama container, then pull the model (~5 GB download):
```bash
docker compose --profile ollama up -d
docker exec -it ollama ollama pull qwen3:8b
```

**Option C — GCP Vertex AI**

Get your project ID from **GCP Console → project selector** (top of page).
Create a service account key from **IAM → Service Accounts → your account → Keys → Add Key**.
Add to `.env`:
```
AGENT_LLM_PROVIDER=vertex_ai
GOOGLE_CLOUD_PROJECT=<your GCP project ID>
GOOGLE_APPLICATION_CREDENTIALS=<path to your service account key JSON file>
```

**Option D — AWS Bedrock**

Get your credentials from **AWS Console → IAM → your user → Security credentials**.
The default model is `anthropic.claude-3-sonnet-20240229-v1:0`. Add to `.env`:
```
AGENT_LLM_PROVIDER=bedrock
AWS_ACCESS_KEY_ID=<your IAM access key ID>
AWS_SECRET_ACCESS_KEY=<your IAM secret access key>
AWS_DEFAULT_REGION=<region where Bedrock is enabled, e.g. us-east-1>
```

**Option E — Azure OpenAI**

Get your credentials from **Azure Portal → your Azure OpenAI resource → Keys and Endpoint**. Add to `.env`:
```
AGENT_LLM_PROVIDER=azure_openai
AGENT_AZURE_OPENAI_KEY=<your API key>
AGENT_AZURE_OPENAI_ENDPOINT=<your endpoint, e.g. https://contoso.openai.azure.com/>
AGENT_AZURE_OPENAI_DEPLOYMENT=<your deployment name, e.g. gpt-4o>
```

---

### Step 4 — Connect to your MongoDB cluster

The agent analyses **one cluster per run**. Set its connection string in `.env`:
```
AGENT_MONGO_CLUSTER=mongodb+srv://user:pass@your-cluster.mongodb.net/
```

**Multiple clusters?** Run the agent once per cluster, overriding the connection string each time:
```bash
AGENT_MONGO_CLUSTER=mongodb+srv://cluster1.mongodb.net/ docker compose run --rm agent
AGENT_MONGO_CLUSTER=mongodb+srv://cluster2.mongodb.net/ docker compose run --rm agent
AGENT_MONGO_CLUSTER=mongodb+srv://cluster3.mongodb.net/ docker compose run --rm agent
```
Each run produces a separate timestamped report in `reports/`.

---

### Step 5 — Run

The agent has two modes. Choose one:

**Health check** — runs a full 8-section analysis and writes a report to `reports/`:

```bash
# Cloud LLM (Option A, C, D, or E):
docker compose run --rm agent python src/main_agentic.py --health-check

# Ollama (Option B):
docker compose --profile ollama run --rm agent python src/main_agentic.py --health-check
```

**Ask a question** — natural language investigation against your cluster:

```bash
# Cloud LLM (Option A, C, D, or E):
docker compose run --rm agent python src/main_agentic.py "my database is slow"

# Ollama (Option B):
docker compose --profile ollama run --rm agent python src/main_agentic.py "my database is slow"
```

When the agent finishes, find the report:
```bash
ls -t reports/*.html | head -1
```

**macOS** — open in browser:
```bash
open $(ls -t reports/*.html | head -1)
```

**Linux desktop** — open in browser:
```bash
xdg-open $(ls -t reports/*.html | head -1)
```

**Linux server (no GUI)** — copy the report to your local machine, then open it:
```bash
# Run this on your local machine, replacing SERVER_IP and /path/to/mongodb-agent-dba
scp user@SERVER_IP:/path/to/mongodb-agent-dba/reports/*.html .
```

## Developing Locally (without Docker)

For contributors working on the agent source code. Requires Python 3.10+, Node 18+,
two running MongoDB 8.0 instances (ports 27017 and 27018), and Ollama.

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
npm install -g @mongodb-js/mongodb-mcp-server

# Run health check
python src/main_agentic.py --health-check

# Run agentic investigation
python src/main_agentic.py "my database is slow"
```

LLM and MongoDB URIs are read from `config/agent_config.yaml` and overridden by
`AGENT_*` env vars (see `.env.example`).

## Usage

```bash
source venv/bin/activate

# Full cluster health check → reports/health_*.json + reports/health_*.html
python src/main_agentic.py --health-check
open $(ls -t reports/*.html | head -1)

# Natural language investigation
python src/main_agentic.py "my database is slow"
python src/main_agentic.py "what indexes does the users collection have"
python src/main_agentic.py "how many collections do I have"
```

## Configuration

Copy `.env.example` to `.env` and set at minimum:

| Variable | Required | Description |
|---|---|---|
| `AGENT_LLM_PROVIDER` | Yes | `ollama` \| `anthropic` \| `azure_openai` \| `bedrock` |
| `AGENT_MONGO_CLUSTER` | For prod | URI of the monitored cluster |
| `AGENT_ANTHROPIC_API_KEY` | If anthropic | Anthropic API key |
| `AGENT_AZURE_OPENAI_KEY` | If azure | Azure OpenAI key |
| `AWS_ACCESS_KEY_ID` | If bedrock | AWS credentials |

Full `config/agent_config.yaml` schema:

```yaml
mongodb:
  agent_store: "mongodb://localhost:27017"       # agent memory
  monitored_cluster: "mongodb://localhost:27018" # target cluster

llm:
  provider: "ollama"   # override: AGENT_LLM_PROVIDER

  ollama:
    base_url: "http://localhost:11434"
    model: "qwen3:8b"

  anthropic:
    model: "claude-sonnet-4-6"

  azure_openai:
    endpoint: ""
    deployment: ""

  bedrock:
    model_id: "anthropic.claude-3-sonnet-20240229-v1:0"
    region: "us-east-1"

agent:
  slow_query_threshold_ms: 5
  llm_recommendations: true   # LLM cross-section recommendation enrichment
```

All `agent_config.yaml` values can be overridden via `AGENT_*` env vars. See `.env.example`.

## Architecture

Two execution paths share the same config and MongoDB connection layer:

```
python src/main_agentic.py --health-check        → Deterministic 8-section pipeline
python src/main_agentic.py "my db is slow"       → LLM-driven agentic investigation
```

### Health Check Pipeline (deterministic)

```
HealthCheckRunner
  §1 Cluster Overview     → MCP: list-databases, list-collections
  §2 Server Health        → MCP: find on local.startup_log, db-stats
  §3 Replication Health   → MCP: find on local.system.replset, local.oplog.rs
  §4 Storage & Capacity   → MCP: db-stats, collection-storage-size, count
  §5 Query Performance    → MCP: find on system.profile (all discovered DBs)
  §6 Missing Indexes      → MCP: collection-indexes on top slow collections
  §7 Unused Indexes       → MCP: aggregate $indexStats (all DBs)
  §8 Operations           → Direct PyMongo: admin.command("serverStatus")
       ↓
  Rule-based recommendations
       ↓
  LLMRecommender.enrich()   (cross-section insights; fails silently)
       ↓
  reports/health_YYYY-MM-DD_HH-MM-SS.json
  reports/health_YYYY-MM-DD_HH-MM-SS.html
```

### Agentic Path (LLM-driven)

```
IntelligentAgenticDBAAgent
  classify_user_intent()        ← LLM
  get_investigation_context()   ← AgentMemory (past investigations)
  select_tools_intelligently()  ← LLM: ordered tool plan
  execute_tool()                ← MCPClient → MongoDB MCP Server (read-only)
  generate_final_response()     ← LLM + memory context
  store_investigation()         ← AgentMemory (TTL persistence)
```

### Infrastructure

| Component | Role | Port |
|---|---|---|
| MongoDB MCP Server | Read-only cluster tool execution | stdio |
| MongoDB — agent store | Investigation memory (TTL indexes) | 27017 |
| MongoDB — monitored cluster | Target cluster under analysis | 27018 |
| Ollama / Anthropic / Azure / Bedrock | LLM reasoning | 11434 or cloud |

## Project Structure

```
mongodb-agent-dba/
├── src/
│   ├── agent/
│   │   ├── health_check_runner.py        # Deterministic 8-section health check
│   │   ├── llm_recommender.py            # LLM cross-section recommendation enrichment
│   │   └── intelligent_agentic_agent.py  # LLM-driven agentic investigation
│   ├── memory/
│   │   └── agent_memory.py               # MongoDB-backed persistent memory (TTL)
│   ├── models/
│   │   └── health_check_report.py        # Typed report schema
│   └── utils/
│       ├── html_reporter.py              # Self-contained HTML report renderer
│       ├── mcp_client.py                 # Sync MCP client wrapper
│       ├── mongodb_client.py             # Agent store + serverStatus connection
│       ├── config_loader.py              # YAML config + AGENT_* env var overrides
│       └── llm_factory.py               # Multi-provider LLM builder
├── config/
│   └── agent_config.yaml                # Runtime configuration
├── Dockerfile                           # Python 3.11 + Node 20 + MCP server
├── docker-compose.yml                   # Four-service stack with profiles
├── .env.example                         # All configurable env vars (copy to .env)
├── reports/                             # JSON + HTML health check output
├── REQUIREMENTS.md                      # Product scope + capability assessment
├── BACKLOG.md                           # Prioritised roadmap
└── create_demo_scenario.py              # Generates testdb with slow queries
```

## Memory System

Investigations persist in the `agent_memory` database (port 27017):

| Collection | Content | TTL |
|---|---|---|
| `investigations` | Full investigation records | 30 days |
| `performance_issues` | Recurring slow query tracking | 90 days |
| `user_context` | Patterns and preferences | — |

The agentic path references this history in new investigations — "I see this
collection was slow last week too…" — and tracks recurring issues across sessions.

## License

MIT
