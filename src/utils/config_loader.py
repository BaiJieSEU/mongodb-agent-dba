"""Configuration management — loads YAML then applies AGENT_* env var overrides."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class ClusterConfig(BaseModel):
    """A single monitored MongoDB cluster entry."""
    name: str
    uri: str
    tags: List[str] = []


class MongoDBConfig(BaseModel):
    agent_store: str
    monitored_cluster: str = ""      # backward-compat; kept in sync with clusters[0]
    monitored_clusters: List[ClusterConfig] = []

    def get_cluster(self, name: str) -> Optional[ClusterConfig]:
        """Return the ClusterConfig with the given name, or None."""
        for c in self.monitored_clusters:
            if c.name == name:
                return c
        return None


class OllamaProviderConfig(BaseModel):
    base_url: str = "http://localhost:11434"
    model: str = "qwen3:8b"
    temperature: float = 0.1


class AnthropicProviderConfig(BaseModel):
    model: str = "claude-sonnet-4-6"
    temperature: float = 0.1


class AzureOpenAIProviderConfig(BaseModel):
    endpoint: str = ""
    deployment: str = ""
    api_version: str = "2024-02-15-preview"
    temperature: float = 0.1


class BedrockProviderConfig(BaseModel):
    model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    region: str = "us-east-1"
    temperature: float = 0.1


class VertexAIProviderConfig(BaseModel):
    project: str = ""
    location: str = "us-central1"
    model: str = "gemini-2.0-flash-001"
    temperature: float = 0.1


class OMConfig(BaseModel):
    """Ops Manager API connection. Keys are env-only — never stored in YAML."""
    url: str = ""
    group_id: str = ""
    public_key: str = ""   # OM_API_PUBLIC_KEY
    private_key: str = ""  # OM_API_PRIVATE_KEY


class LLMConfig(BaseModel):
    provider: str = "ollama"
    ollama: OllamaProviderConfig = OllamaProviderConfig()
    anthropic: AnthropicProviderConfig = AnthropicProviderConfig()
    azure_openai: AzureOpenAIProviderConfig = AzureOpenAIProviderConfig()
    bedrock: BedrockProviderConfig = BedrockProviderConfig()
    vertex_ai: VertexAIProviderConfig = VertexAIProviderConfig()


class AgentConfig(BaseModel):
    slow_query_threshold_ms: int
    max_queries_to_analyze: int
    investigation_timeout: int
    llm_recommendations: bool = False   # BL-034: enrich health check recs with LLM


class ThresholdsConfig(BaseModel):
    """Health check severity thresholds (BL-021). All values have safe defaults."""
    # Query Performance
    slow_query_pct_warning: float   = 5.0
    slow_query_pct_critical: float  = 20.0
    slow_query_ms_warning: int      = 100
    slow_query_ms_critical: int     = 500
    # Replication Health
    oplog_window_warning_hours: int  = 24
    oplog_window_critical_hours: int = 4
    # Storage & Capacity
    disk_used_pct_warning: int  = 80
    disk_used_pct_critical: int = 90
    # Operations — WiredTiger cache
    cache_hit_ratio_warning: float  = 0.95
    cache_hit_ratio_critical: float = 0.80
    # Operations — lock contention
    lock_wait_pct_warning: float  = 5.0
    lock_wait_pct_critical: float = 20.0
    # Operations — query targeting
    query_targeting_warning: float  = 10.0
    query_targeting_critical: float = 100.0
    # Operations — memory
    memory_resident_warning_mb: int  = 4096
    memory_resident_critical_mb: int = 8192
    # Connections & Concurrency
    connections_warning: int  = 500
    tickets_warning: int      = 10
    lock_queue_warning: int   = 10
    # Infrastructure
    cpu_user_pct_warning: float              = 80.0
    cpu_iowait_pct_warning: float            = 10.0
    disk_write_latency_warning_ms: float     = 10.0
    system_memory_used_pct_warning: float    = 90.0
    # Index analysis
    full_scan_examined_min: int        = 1000
    full_scan_selectivity_max: float   = 0.01
    # Operations — plan cache (MongoDB 7.0+)
    plan_cache_hit_rate_warning: float  = 80.0
    plan_cache_hit_rate_critical: float = 50.0
    # Backup & Recovery (BL-106/107)
    backup_interval_hours: float = 24.0


class DemoConfig(BaseModel):
    users_count: int
    products_count: int
    orders_count: int


class AppConfig(BaseModel):
    mongodb: MongoDBConfig
    llm: LLMConfig
    agent: AgentConfig
    demo: DemoConfig
    logging: Dict[str, Any]
    ops_manager: OMConfig = OMConfig()
    thresholds: ThresholdsConfig = ThresholdsConfig()


def _apply_env_overrides(config: AppConfig) -> AppConfig:
    """Apply AGENT_* environment variable overrides after loading YAML."""
    data = config.model_dump()

    # MongoDB URIs
    # MONGO_MONITORED_URI / AGENT_MONGO_CLUSTER both override the single monitored cluster
    if v := os.getenv("MONGO_MONITORED_URI") or os.getenv("AGENT_MONGO_CLUSTER"):
        data["mongodb"]["monitored_cluster"] = v
        # Also replace clusters[0] so all code paths see the same URI
        if data["mongodb"].get("monitored_clusters"):
            data["mongodb"]["monitored_clusters"][0]["uri"] = v
        else:
            data["mongodb"]["monitored_clusters"] = [{"name": "remote", "uri": v, "tags": []}]
    if v := os.getenv("AGENT_MONGO_STORE"):
        data["mongodb"]["agent_store"] = v

    # Multi-cluster: AGENT_MONGO_CLUSTERS=uri1,uri2,uri3 (overrides monitored_clusters list)
    if v := os.getenv("AGENT_MONGO_CLUSTERS"):
        from urllib.parse import urlparse
        clusters = []
        for uri in [u.strip() for u in v.split(",") if u.strip()]:
            try:
                host = urlparse(uri).hostname or uri
                name = host.split(".")[0]
            except Exception:
                name = uri
            clusters.append({"name": name, "uri": uri, "tags": []})
        data["mongodb"]["monitored_clusters"] = clusters
        if clusters:
            data["mongodb"]["monitored_cluster"] = clusters[0]["uri"]

    # LLM provider selection
    if v := os.getenv("AGENT_LLM_PROVIDER"):
        data["llm"]["provider"] = v

    # Ollama overrides
    if v := os.getenv("AGENT_OLLAMA_URL"):
        data["llm"]["ollama"]["base_url"] = v
    if v := os.getenv("AGENT_OLLAMA_MODEL"):
        data["llm"]["ollama"]["model"] = v

    # Vertex AI overrides
    if v := os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("VERTEXAI_PROJECT"):
        data["llm"]["vertex_ai"]["project"] = v
    if v := os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("VERTEXAI_LOCATION"):
        data["llm"]["vertex_ai"]["location"] = v

    # Slow query threshold
    if v := os.getenv("AGENT_SLOW_QUERY_MS"):
        data["agent"]["slow_query_threshold_ms"] = int(v)

    # Ops Manager
    om = data.setdefault("ops_manager", {})
    if v := os.getenv("OM_URL"):
        om["url"] = v
    if v := os.getenv("OM_GROUP_ID"):
        om["group_id"] = v
    if v := os.getenv("OM_API_PUBLIC_KEY"):
        om["public_key"] = v
    if v := os.getenv("OM_API_PRIVATE_KEY"):
        om["private_key"] = v

    return AppConfig(**data)


def load_config(config_path: str = None) -> AppConfig:
    """Load configuration from YAML file then apply env var overrides."""
    if config_path is None:
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "agent_config.yaml"

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r") as f:
        data = yaml.safe_load(f)

    # Backward compat: old config had top-level `ollama:` instead of `llm:`
    if "llm" not in data and "ollama" in data:
        old = data.pop("ollama")
        data["llm"] = {
            "provider": "ollama",
            "ollama": old,
        }

    config = AppConfig(**data)
    config = _apply_env_overrides(config)

    # Synthesize monitored_clusters from monitored_cluster for backward-compat
    if not config.mongodb.monitored_clusters and config.mongodb.monitored_cluster:
        raw = config.model_dump()
        raw["mongodb"]["monitored_clusters"] = [
            {"name": "default", "uri": config.mongodb.monitored_cluster, "tags": []}
        ]
        config = AppConfig(**raw)

    # Keep monitored_cluster in sync with the first cluster's URI
    if config.mongodb.monitored_clusters and not config.mongodb.monitored_cluster:
        raw = config.model_dump()
        raw["mongodb"]["monitored_cluster"] = config.mongodb.monitored_clusters[0].uri
        config = AppConfig(**raw)

    return config


def get_project_root() -> Path:
    return Path(__file__).parent.parent.parent
