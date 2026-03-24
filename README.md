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

**One cluster** — add to `.env`:
```
AGENT_MONGO_CLUSTER=mongodb+srv://user:pass@your-cluster.mongodb.net/
```

**Multiple clusters (env var)** — add a comma-separated list to `.env`:
```
AGENT_MONGO_CLUSTERS=mongodb+srv://cluster1.mongodb.net/,mongodb+srv://cluster2.mongodb.net/,mongodb+srv://cluster3.mongodb.net/
```

When `AGENT_MONGO_CLUSTERS` is set, cluster names are auto-derived from hostnames. `run.sh` iterates the list and runs the agent once per cluster; each run produces a separate timestamped report in `reports/`.

**Multiple clusters (config file)** — register named clusters in `agent_config.yaml`:
```yaml
mongodb:
  agent_store: "mongodb://localhost:27017"
  monitored_clusters:
    - name: "production"
      uri: "mongodb+srv://user:pass@prod.mongodb.net/"
      tags: [production]
    - name: "staging"
      uri: "mongodb+srv://user:pass@staging.mongodb.net/"
      tags: [staging]
```

Then target a specific cluster by name:
```bash
./run.sh --cluster production --health-check
./run.sh --cluster staging "why is my database slow"
```

Omitting `--cluster` defaults to the first entry in the list.

---

### Step 5 — Run

Make the run script executable (once):
```bash
chmod +x run.sh
```

Then run the agent with any message:
```bash
./run.sh "check my cluster health"
./run.sh "why is my database slow"
./run.sh "what indexes does the users collection have"
```

The script reads your `.env` to detect the LLM provider and runs the right Docker command automatically. When the agent finishes, it prints the report path to the terminal.

## Connecting to a Remote Cluster

The agent only needs **network access to MongoDB** — it does not need to run on the
same host as the cluster. Two approaches cover most real-world scenarios:

---

### Approach A — SSH Tunnel (POC / demo, ~1 min setup)

Best for: initial assessment, proof-of-concept, customer demo where no software is
installed on the customer's server.

```
Your Laptop                        Customer Infrastructure
─────────────────────────────      ──────────────────────────────────
Agent runs here          ───────►  SSH bastion / jump host
  MONGO_MONITORED_URI=             ───────►  MongoDB Replica Set
  mongodb://localhost:27020/...              (internal network only)
```

**Step 1** — Open the tunnel (replace with your bastion host and MongoDB internal IP):
```bash
ssh -L 27020:<mongo-internal-ip>:27017 <user>@<bastion-host> -N &
```

**Step 2** — Point the agent at the tunnel:
```bash
export MONGO_MONITORED_URI="mongodb://localhost:27020/?replicaSet=<rsName>&directConnection=true"
source venv/bin/activate && python src/main_agentic.py --health-check
```

No software installed on the customer side. Kill the tunnel when done:
```bash
kill %1
```

---

### Approach B — Docker on Customer VM (persistent monitoring, ~10 min setup)

Best for: leaving a persistent monitoring agent on the customer's infrastructure after
the initial engagement, or any environment where Docker is available.

```
Customer VM (e.g. a monitoring host or jump box)
─────────────────────────────────────────────────
Docker container (agent + MCP server)
  │
  └──► MongoDB Replica Set (internal network)
```

**Step 1** — On the customer VM, create a credential file (never committed to git):
```bash
cat > .env << 'EOF'
MONGO_MONITORED_URI=mongodb://<host1>:27017,<host2>:27017,<host3>:27017/?replicaSet=<rsName>
AGENT_LLM_PROVIDER=anthropic          # or ollama, vertex_ai, bedrock, azure_openai
AGENT_ANTHROPIC_API_KEY=<key>         # set for chosen provider
EOF
chmod 600 .env
```

**Step 2** — Pull and run:
```bash
git clone https://github.com/BaiJieSEU/mongodb-agent-dba
cd mongodb-agent-dba
docker compose build
docker compose run --rm agent python src/main_agentic.py --health-check
```

Report is written to `reports/` on the host volume.

**To leave a scheduled agent running:**
```bash
# Run health check every hour (add to crontab)
0 * * * * cd /home/ubuntu/mongodb-agent-dba && \
  docker compose run --rm agent python src/main_agentic.py --health-check
```

---

### Comparison

| Approach | Setup time | Customer installs | Best for |
|---|---|---|---|
| SSH tunnel | ~1 min | Nothing | POC, demo, one-off assessment |
| Docker on VM | ~10 min | Docker only | Persistent monitoring, leave-behind |

---

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

# Target a specific named cluster (from monitored_clusters in config)
python src/main_agentic.py --health-check --cluster production
python src/main_agentic.py --cluster staging "my database is slow"

# Fleet health check — all clusters at once (produces a single tabbed HTML report)
# When more than one cluster is configured, --health-check without --cluster runs
# all clusters and produces a unified fleet_*.json + fleet_*.html + fleet_*.md report.
python src/main_agentic.py --health-check

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
| `AGENT_MONGO_CLUSTER` | For prod | URI of the single monitored cluster |
| `AGENT_MONGO_CLUSTERS` | For multi | Comma-separated URIs; names auto-derived from hostnames |
| `AGENT_ANTHROPIC_API_KEY` | If anthropic | Anthropic API key |
| `AGENT_AZURE_OPENAI_KEY` | If azure | Azure OpenAI key |
| `AWS_ACCESS_KEY_ID` | If bedrock | AWS credentials |

Full `config/agent_config.yaml` schema:

```yaml
mongodb:
  agent_store: "mongodb://localhost:27017"        # agent memory
  monitored_cluster: "mongodb://localhost:27018"  # backward-compat single cluster
  monitored_clusters:                             # named cluster list (BL-050)
    - name: "local-rs1"
      uri: "mongodb://localhost:27018"
      tags: [development]

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
├── docker-compose.yml                   # Three-service stack (agent, mongo-memory, ollama)
├── .env.example                         # All configurable env vars (copy to .env)
├── reports/                             # JSON + HTML health check output
├── run.sh                               # Run wrapper (detects LLM provider, loops clusters)
├── REQUIREMENTS.md                      # Product scope + capability assessment
└── BACKLOG.md                           # Prioritised roadmap
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
