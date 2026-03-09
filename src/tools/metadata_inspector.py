"""MongoDB metadata inspection tool"""

import logging
from typing import Dict, Any, List
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from utils.mongodb_client import MongoDBManager

logger = logging.getLogger(__name__)


class MetadataInspector:
    """Inspects MongoDB metadata like collections, databases, indexes"""
    
    def __init__(self, mongo_manager: MongoDBManager):
        self.mongo_manager = mongo_manager
    
    def get_collections_info(self, db_name: str) -> Dict[str, Any]:
        """Get comprehensive collection information"""
        try:
            with self.mongo_manager.get_monitored_db(db_name) as db:
                collections = db.list_collection_names()
                
                collection_details = []
                for coll_name in collections:
                    try:
                        coll = db[coll_name]
                        
                        # Get basic stats
                        stats = db.command("collStats", coll_name)
                        
                        # Get indexes
                        indexes = list(coll.list_indexes())
                        index_info = [
                            {
                                "name": idx.get("name", "unknown"),
                                "keys": dict(idx.get("key", {})),
                                "unique": idx.get("unique", False)
                            } for idx in indexes
                        ]
                        
                        collection_details.append({
                            "name": coll_name,
                            "count": stats.get("count", 0),
                            "size_bytes": stats.get("size", 0),
                            "avg_obj_size": stats.get("avgObjSize", 0),
                            "indexes": index_info,
                            "index_count": len(indexes)
                        })
                        
                    except Exception as e:
                        logger.warning(f"Failed to get details for collection {coll_name}: {e}")
                        collection_details.append({
                            "name": coll_name,
                            "error": str(e)
                        })
                
                return {
                    "database": db_name,
                    "collection_count": len(collections),
                    "collections": collection_details
                }
                
        except Exception as e:
            logger.error(f"Error getting collections info: {e}")
            return {"database": db_name, "error": str(e)}
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get information about available databases"""
        try:
            databases = self.mongo_manager.get_database_names()
            
            db_details = []
            for db_name in databases:
                try:
                    with self.mongo_manager.get_monitored_db(db_name) as db:
                        stats = db.command("dbStats")
                        collections = db.list_collection_names()
                        
                        db_details.append({
                            "name": db_name,
                            "collections": len(collections),
                            "data_size": stats.get("dataSize", 0),
                            "storage_size": stats.get("storageSize", 0),
                            "indexes": stats.get("indexes", 0)
                        })
                except Exception as e:
                    logger.warning(f"Failed to get stats for database {db_name}: {e}")
                    db_details.append({
                        "name": db_name,
                        "error": str(e)
                    })
            
            return {
                "database_count": len(databases),
                "databases": db_details
            }
            
        except Exception as e:
            logger.error(f"Error getting database info: {e}")
            return {"error": str(e)}


def create_metadata_inspector_tool(mongo_manager: MongoDBManager):
    """Create LangChain tool for metadata inspection"""
    
    class MetadataInput(BaseModel):
        action: str = Field(description="Action to perform: list_collections, list_databases, collection_details")
        database: str = Field(default="testdb", description="Database name for collection operations")
    
    inspector = MetadataInspector(mongo_manager)
    
    def inspect_metadata_tool(action: str, database: str = "testdb") -> str:
        """Inspect MongoDB metadata - collections, databases, schemas"""
        try:
            if action == "list_collections":
                result = inspector.get_collections_info(database)
                
                if "error" in result:
                    return f"Error getting collections: {result['error']}"
                
                output = f"📊 COLLECTIONS IN DATABASE '{database.upper()}'\n\n"
                output += f"Total collections: {result['collection_count']}\n\n"
                
                if result["collections"]:
                    for coll in result["collections"]:
                        if "error" in coll:
                            output += f"• {coll['name']}: ❌ {coll['error']}\n"
                        else:
                            output += f"• {coll['name']}: {coll['count']:,} documents, {coll['index_count']} indexes\n"
                            if coll.get('size_bytes', 0) > 0:
                                size_mb = coll['size_bytes'] / (1024 * 1024)
                                output += f"  Size: {size_mb:.2f} MB\n"
                else:
                    output += "No collections found.\n"
                
                return output
                
            elif action == "list_databases":
                result = inspector.get_database_info()
                
                if "error" in result:
                    return f"Error getting databases: {result['error']}"
                
                output = f"🏛️ MONGODB DATABASES\n\n"
                output += f"Total databases: {result['database_count']}\n\n"
                
                for db in result["databases"]:
                    if "error" in db:
                        output += f"• {db['name']}: ❌ {db['error']}\n"
                    else:
                        output += f"• {db['name']}: {db['collections']} collections, {db['indexes']} indexes\n"
                        if db.get('data_size', 0) > 0:
                            size_mb = db['data_size'] / (1024 * 1024)
                            output += f"  Data size: {size_mb:.2f} MB\n"
                
                return output
                
            elif action == "collection_details":
                result = inspector.get_collections_info(database)
                
                if "error" in result:
                    return f"Error getting collection details: {result['error']}"
                
                output = f"📋 DETAILED COLLECTION INFORMATION FOR '{database.upper()}'\n\n"
                
                for coll in result["collections"]:
                    if "error" in coll:
                        output += f"❌ {coll['name']}: {coll['error']}\n\n"
                        continue
                        
                    output += f"Collection: {coll['name']}\n"
                    output += f"• Documents: {coll['count']:,}\n"
                    
                    if coll.get('size_bytes', 0) > 0:
                        size_mb = coll['size_bytes'] / (1024 * 1024)
                        output += f"• Size: {size_mb:.2f} MB\n"
                        
                    if coll.get('avg_obj_size', 0) > 0:
                        output += f"• Avg document size: {coll['avg_obj_size']} bytes\n"
                    
                    output += f"• Indexes ({coll['index_count']}):\n"
                    for idx in coll['indexes']:
                        unique_str = " (unique)" if idx.get('unique') else ""
                        output += f"  - {idx['name']}: {idx['keys']}{unique_str}\n"
                    output += "\n"
                
                return output
                
            else:
                return f"Unknown action: {action}. Available actions: list_collections, list_databases, collection_details"
                
        except Exception as e:
            return f"Error in metadata inspection: {str(e)}"
    
    return StructuredTool(
        name="inspect_metadata",
        description="Inspect MongoDB metadata like collections, databases, and schemas. Use for questions about database structure, collection counts, or schema information.",
        func=inspect_metadata_tool,
        args_schema=MetadataInput
    )