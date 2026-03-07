"""Configuration management"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any
from pydantic import BaseModel


class MongoDBConfig(BaseModel):
    agent_store: str
    monitored_cluster: str


class OllamaConfig(BaseModel):
    base_url: str
    model: str


class AgentConfig(BaseModel):
    slow_query_threshold_ms: int
    max_queries_to_analyze: int
    investigation_timeout: int


class DemoConfig(BaseModel):
    users_count: int
    products_count: int
    orders_count: int


class AppConfig(BaseModel):
    mongodb: MongoDBConfig
    ollama: OllamaConfig
    agent: AgentConfig
    demo: DemoConfig
    logging: Dict[str, Any]


def load_config(config_path: str = None) -> AppConfig:
    """Load configuration from YAML file"""
    if config_path is None:
        # Default to config/agent_config.yaml relative to project root
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "agent_config.yaml"
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)
    
    return AppConfig(**config_data)


def get_project_root() -> Path:
    """Get the project root directory"""
    return Path(__file__).parent.parent.parent