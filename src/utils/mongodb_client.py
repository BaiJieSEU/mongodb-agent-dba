"""MongoDB client utilities"""

import logging
import re
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from contextlib import contextmanager


logger = logging.getLogger(__name__)


def _strip_replicaset(uri: str) -> str:
    """Remove replicaSet parameter from a MongoDB URI.

    When tunnelling via directConnection=true the node doesn't advertise its RS
    name, so PyMongo raises a ConfigurationError if replicaSet is also present.
    Stripping it lets PyMongo connect as a standalone direct connection.
    """
    parsed = urlparse(uri)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    if "replicaSet" not in qs:
        return uri
    qs.pop("replicaSet")
    new_query = urlencode(qs, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


class MongoDBManager:
    """Manages MongoDB connections for both agent store and monitored cluster"""

    def __init__(self, agent_store_uri: str, monitored_cluster_uri: str):
        self.agent_store_uri = agent_store_uri
        # Strip replicaSet when directConnection=true to avoid PyMongo mismatch
        if "directConnection=true" in monitored_cluster_uri:
            self.monitored_cluster_uri = _strip_replicaset(monitored_cluster_uri)
        else:
            self.monitored_cluster_uri = monitored_cluster_uri
        self._agent_store_client: Optional[MongoClient] = None
        self._monitored_client: Optional[MongoClient] = None
    
    @property
    def agent_store(self) -> MongoClient:
        """Get agent store MongoDB client"""
        if self._agent_store_client is None:
            self._agent_store_client = MongoClient(
                self.agent_store_uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000
            )
            # Test connection
            self._agent_store_client.admin.command('ping')
            logger.info(f"Connected to agent store: {self.agent_store_uri}")
        return self._agent_store_client
    
    @property
    def monitored_cluster(self) -> MongoClient:
        """Get monitored cluster MongoDB client"""
        if self._monitored_client is None:
            self._monitored_client = MongoClient(
                self.monitored_cluster_uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000
            )
            # Test connection
            self._monitored_client.admin.command('ping')
            logger.info(f"Connected to monitored cluster: {self.monitored_cluster_uri}")
        return self._monitored_client
    
    def ensure_profiler_enabled(self, db_name: str, level: int = 1, threshold_ms: int = None) -> bool:
        """Enable MongoDB profiler for slow query collection"""
        try:
            db = self.monitored_cluster[db_name]
            # Use provided threshold or default from config
            slowms = threshold_ms if threshold_ms is not None else self.config.agent.slow_query_threshold_ms
            # Set profiler level (0=off, 1=slow ops, 2=all ops)
            result = db.command("profile", level, slowms=slowms)
            logger.info(f"Profiler enabled for {db_name} with {slowms}ms threshold: {result}")
            return True
        except Exception as e:
            logger.error(f"Failed to enable profiler: {e}")
            return False
    
    def get_database_names(self) -> list:
        """Get list of database names (excluding system dbs)"""
        try:
            db_names = self.monitored_cluster.list_database_names()
            # Filter out system databases
            return [db for db in db_names if db not in ['admin', 'local', 'config']]
        except Exception as e:
            logger.error(f"Failed to get database names: {e}")
            return []
    
    def get_server_status(self) -> Optional[Dict[str, Any]]:
        """Return admin.command("serverStatus") from the monitored cluster.

        Read-only admin command — no writes.  Used by HealthCheckRunner §8.
        Returns None on any error so the caller can degrade gracefully.
        """
        try:
            result = self.monitored_cluster.admin.command("serverStatus")
            return result
        except Exception as e:
            logger.warning(f"serverStatus unavailable: {e}")
            return None

    def get_rs_status(self) -> Optional[Dict[str, Any]]:
        """Return admin.command("replSetGetStatus") from the monitored cluster.

        Read-only admin command — clusterMonitor role required.
        Returns None on standalone instances or insufficient privileges.
        Used by HealthCheckRunner §3 (BL-094).
        """
        try:
            result = self.monitored_cluster.admin.command("replSetGetStatus")
            return result
        except Exception as e:
            logger.debug("replSetGetStatus unavailable: %s", e)
            return None

    def get_current_op(self, running_longer_than_secs: int = 5) -> List[Dict[str, Any]]:
        """Return active operations running ≥ threshold seconds.

        Uses currentOp admin command — read-only, clusterMonitor role required.
        Returns [] on standalone instances, insufficient privileges, or any error.
        Used by HealthCheckRunner §8 (BL-097).
        """
        try:
            result = self.monitored_cluster.admin.command({
                "currentOp": 1,
                "active": True,
                "secs_running": {"$gte": running_longer_than_secs},
            })
            return result.get("inprog", [])
        except Exception as e:
            logger.debug("currentOp unavailable: %s", e)
            return []

    def test_connections(self) -> Dict[str, bool]:
        """Test both MongoDB connections"""
        results = {}
        
        # Test agent store
        try:
            self.agent_store.admin.command('ping')
            results['agent_store'] = True
            logger.info("Agent store connection: OK")
        except Exception as e:
            results['agent_store'] = False
            logger.error(f"Agent store connection failed: {e}")
        
        # Test monitored cluster
        try:
            self.monitored_cluster.admin.command('ping')
            results['monitored_cluster'] = True
            logger.info("Monitored cluster connection: OK")
        except Exception as e:
            results['monitored_cluster'] = False
            logger.error(f"Monitored cluster connection failed: {e}")
        
        return results
    
    def test_agent_store_connection(self):
        """Test agent store connection"""
        try:
            self.agent_store.admin.command('ping')
            return True
        except Exception as e:
            raise ConnectionFailure(f"Agent store connection failed: {e}")
    
    def test_monitored_cluster_connection(self):
        """Test monitored cluster connection"""
        try:
            self.monitored_cluster.admin.command('ping')
            return True
        except Exception as e:
            raise ConnectionFailure(f"Monitored cluster connection failed: {e}")
    
    def close_connections(self):
        """Close all MongoDB connections"""
        if self._agent_store_client:
            self._agent_store_client.close()
            self._agent_store_client = None
            
        if self._monitored_client:
            self._monitored_client.close()
            self._monitored_client = None
        
        logger.info("All MongoDB connections closed")
    
    def close_all_connections(self):
        """Alias for close_connections"""
        self.close_connections()

    @contextmanager
    def get_monitored_db(self, db_name: str):
        """Context manager for monitored database operations"""
        try:
            db = self.monitored_cluster[db_name]
            yield db
        except Exception as e:
            logger.error(f"Error accessing database {db_name}: {e}")
            raise


class ProfilerManager:
    """Manages MongoDB profiler operations"""
    
    def __init__(self, mongo_manager: MongoDBManager):
        self.mongo_manager = mongo_manager
    
    def enable_profiling(self, db_name: str, level: int = 1, slowms: int = 100) -> bool:
        """Enable profiling on specified database"""
        try:
            with self.mongo_manager.get_monitored_db(db_name) as db:
                result = db.command("profile", level, slowms=slowms)
                logger.info(f"Profiling enabled on {db_name}: level={level}, slowms={slowms}")
                return result.get('ok', 0) == 1
        except Exception as e:
            logger.error(f"Failed to enable profiling on {db_name}: {e}")
            return False
    
    def disable_profiling(self, db_name: str) -> bool:
        """Disable profiling on specified database"""
        try:
            with self.mongo_manager.get_monitored_db(db_name) as db:
                result = db.command("profile", 0)
                logger.info(f"Profiling disabled on {db_name}")
                return result.get('ok', 0) == 1
        except Exception as e:
            logger.error(f"Failed to disable profiling on {db_name}: {e}")
            return False
    
    def get_profile_status(self, db_name: str) -> Dict[str, Any]:
        """Get profiler status for database"""
        try:
            with self.mongo_manager.get_monitored_db(db_name) as db:
                result = db.command("profile", -1)
                return {
                    'level': result.get('was', 0),
                    'slowms': result.get('slowms', 100),
                    'enabled': result.get('was', 0) > 0
                }
        except Exception as e:
            logger.error(f"Failed to get profile status for {db_name}: {e}")
            return {'level': 0, 'slowms': 100, 'enabled': False}