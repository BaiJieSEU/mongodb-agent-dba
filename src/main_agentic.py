"""Main entry point for Agentic MongoDB DBA Agent"""

import argparse
import logging
import sys
from rich.console import Console
from rich.logging import RichHandler

from utils.config_loader import load_config
from utils.mongodb_client import MongoDBManager
from agent.intelligent_agentic_agent import IntelligentAgenticDBAAgent

# Setup rich console
console = Console()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)

logger = logging.getLogger(__name__)


def test_prerequisites(config, mongo_manager):
    """Test that all prerequisites are met"""
    console.print("🔍 Checking prerequisites...", style="blue")
    
    # Test agent store connection
    try:
        mongo_manager.test_agent_store_connection()
        logger.info("Connected to agent store: %s", config.mongodb.agent_store)
        logger.info("Agent store connection: OK")
    except Exception as e:
        console.print(f"❌ Cannot connect to agent store", style="red")
        console.print(f"   Connection string: {config.mongodb.agent_store}", style="red")
        console.print(f"   Error: {e}", style="red")
        return False
    
    # Test monitored cluster connection
    try:
        mongo_manager.test_monitored_cluster_connection()
        logger.info("Connected to monitored cluster: %s", config.mongodb.monitored_cluster)
        logger.info("Monitored cluster connection: OK")
    except Exception as e:
        console.print(f"❌ Cannot connect to monitored MongoDB cluster", style="red")
        console.print(f"   Connection string: {config.mongodb.monitored_cluster}", style="red")
        console.print(f"   Please ensure MongoDB is running on port 27018", style="red")
        return False
    
    # Test Ollama connection
    try:
        from langchain_ollama import OllamaLLM
        llm = OllamaLLM(base_url=config.ollama.base_url, model=config.ollama.model)
        # Test with a simple prompt
        response = llm.invoke("test")
        logger.info("HTTP Request: POST %s/api/generate \"HTTP/1.1 200 OK\"", config.ollama.base_url)
        console.print("✅ Ollama connection: OK", style="green")
    except Exception as e:
        console.print(f"❌ Cannot connect to Ollama", style="red")
        console.print(f"   URL: {config.ollama.base_url}", style="red")
        console.print(f"   Model: {config.ollama.model}", style="red")
        console.print(f"   Error: {e}", style="red")
        console.print(f"   Please ensure Ollama is running with: ollama serve", style="red")
        return False
    
    console.print("✅ All prerequisites met", style="green")
    return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Agentic MongoDB DBA Agent")
    parser.add_argument("query", help="Database issue description")
    parser.add_argument("--config", default="config/agent_config.yaml", help="Config file path")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        # Initialize MongoDB manager
        mongo_manager = MongoDBManager(
            config.mongodb.agent_store,
            config.mongodb.monitored_cluster
        )
        
        # Test prerequisites
        if not test_prerequisites(config, mongo_manager):
            console.print("\n❌ Prerequisites not met. Please fix the issues above and try again.", style="red")
            sys.exit(1)
        
        console.print("\n🤖 Starting Agentic MongoDB DBA Agent Investigation...", style="bold blue")
        
        # Display user request in a box
        console.print("\n" + "─" * 80)
        console.print(f"📝 USER REQUEST: {args.query}", style="bold cyan", justify="center")
        console.print("─" * 80)
        
        console.print("\n🧠 Agent is planning investigation strategy...", style="yellow")
        
        # Initialize and run the intelligent agentic agent
        agent = IntelligentAgenticDBAAgent(config, mongo_manager)
        
        # Execute investigation
        result = agent.investigate(args.query)
        
        # Display results
        console.print("\n" + "=" * 80, style="green")
        console.print(result)
        console.print("=" * 80, style="green")
        
    except KeyboardInterrupt:
        console.print("\n🛑 Investigation interrupted by user", style="yellow")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n❌ Error: {e}", style="red")
        if args.debug:
            logger.exception("Detailed error information")
        sys.exit(1)
    finally:
        # Cleanup
        try:
            if 'mongo_manager' in locals():
                mongo_manager.close_all_connections()
                logger.info("All MongoDB connections closed")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")


if __name__ == "__main__":
    main()