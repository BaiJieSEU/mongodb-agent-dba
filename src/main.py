"""Main CLI entry point for MongoDB DBA Agent"""

import sys
import logging
import argparse
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.text import Text

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.config_loader import load_config
from utils.mongodb_client import MongoDBManager
from agent.slow_query_agent import SlowQueryAgent

console = Console()


def setup_logging(level: str = "INFO"):
    """Setup rich logging"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, show_time=True, show_path=False)]
    )


def check_prerequisites(config, mongo_manager):
    """Check if all prerequisites are met"""
    console.print("🔍 Checking prerequisites...", style="yellow")
    
    # Test MongoDB connections
    connections = mongo_manager.test_connections()
    
    if not connections.get("monitored_cluster", False):
        console.print("❌ Cannot connect to monitored MongoDB cluster", style="red")
        console.print(f"   Connection string: {config.mongodb.monitored_cluster}")
        console.print("   Please ensure MongoDB is running on port 27018")
        return False
    
    # Test Ollama connection
    try:
        from langchain_ollama import OllamaLLM
        llm = OllamaLLM(base_url=config.ollama.base_url, model=config.ollama.model)
        # Quick test
        response = llm.invoke("test")
        console.print("✅ Ollama connection: OK", style="green")
    except Exception as e:
        console.print("❌ Cannot connect to Ollama", style="red")
        console.print(f"   Base URL: {config.ollama.base_url}")
        console.print(f"   Model: {config.ollama.model}")
        console.print(f"   Error: {str(e)}")
        console.print("   Please ensure Ollama is running with the required model")
        return False
    
    console.print("✅ All prerequisites met", style="green")
    return True


def run_agent(user_input: str, config_path: str = None, verbose: bool = False):
    """Run the DBA agent investigation"""
    
    # Setup logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level)
    
    try:
        # Load configuration
        config = load_config(config_path)
        
        # Initialize MongoDB manager
        mongo_manager = MongoDBManager(
            config.mongodb.agent_store,
            config.mongodb.monitored_cluster
        )
        
        # Check prerequisites
        if not check_prerequisites(config, mongo_manager):
            console.print("\\n❌ Prerequisites not met. Please fix the issues above and try again.", style="red")
            return 1
        
        console.print("\\n🤖 Starting MongoDB DBA Agent Investigation...", style="blue bold")
        console.print(Panel(
            Text(user_input, justify="center"),
            title="User Request",
            border_style="blue"
        ))
        
        # Initialize and run agent
        agent = SlowQueryAgent(config, mongo_manager)
        
        console.print("\\n🔎 Agent is investigating...", style="yellow")
        
        # Run the investigation
        result = agent.investigate(user_input)
        
        # Display results
        console.print("\\n" + "="*60)
        console.print(result)
        console.print("="*60)
        
        # Cleanup
        mongo_manager.close_connections()
        
        return 0
        
    except KeyboardInterrupt:
        console.print("\\n⚠️ Investigation interrupted by user", style="yellow")
        return 1
    except Exception as e:
        console.print(f"\\n❌ Error: {str(e)}", style="red")
        logging.error(f"Unexpected error: {e}", exc_info=True)
        return 1


def generate_test_data(config_path: str = None, **kwargs):
    """Generate test data for demonstration"""
    from utils.test_data_generator import TestDataGenerator
    
    console.print("🔧 Generating test data...", style="yellow")
    
    try:
        # Load configuration
        config = load_config(config_path)
        
        # Override with command line arguments
        if kwargs.get("users"):
            config.demo.users_count = kwargs["users"]
        if kwargs.get("products"):
            config.demo.products_count = kwargs["products"]
        if kwargs.get("orders"):
            config.demo.orders_count = kwargs["orders"]
        
        # Initialize MongoDB manager
        mongo_manager = MongoDBManager(
            config.mongodb.agent_store,
            config.mongodb.monitored_cluster
        )
        
        # Test connection
        connections = mongo_manager.test_connections()
        if not connections.get("monitored_cluster", False):
            console.print("❌ Cannot connect to monitored cluster", style="red")
            return 1
        
        # Create generator and setup test environment
        generator = TestDataGenerator(mongo_manager, config.demo)
        
        console.print(f"📊 Creating test data:", style="blue")
        console.print(f"  • Users: {config.demo.users_count:,}")
        console.print(f"  • Products: {config.demo.products_count:,}")
        console.print(f"  • Orders: {config.demo.orders_count:,}")
        
        generator.setup_test_environment()
        
        console.print("✅ Test data generation complete!", style="green")
        console.print("\\n🚀 You can now run the agent:")
        console.print("   python src/main.py \"my database is slow\"", style="cyan")
        
        # Show stats
        stats = generator.get_database_stats()
        if stats:
            console.print("\\n📈 Database Statistics:")
            for key, value in stats.items():
                console.print(f"   {key}: {value:,}")
        
        return 0
        
    except Exception as e:
        console.print(f"❌ Error generating test data: {str(e)}", style="red")
        logging.error(f"Test data generation failed: {e}", exc_info=True)
        return 1


def show_demo_script():
    """Show the demo verification script"""
    demo_script = '''
# MongoDB DBA Agent Demo Script

## 1. Setup Second MongoDB Instance (monitored cluster)
# Start MongoDB on port 27018 for the monitored cluster
mongod --port 27018 --dbpath ~/mongodb/data2 --logpath ~/mongodb/logs/mongod2.log --replSet rs1

# Initialize replica set
mongosh --port 27018 --eval "rs.initiate({_id: 'rs1', members: [{_id: 0, host: 'localhost:27018'}]})"

## 2. Generate Test Data
python src/main.py --generate-data --users 100000 --products 10000 --orders 50000

## 3. Show BEFORE State (without index)
mongosh --port 27018 testdb --eval "
  var result = db.users.find({email: 'user50000@example.com'}).explain('executionStats');
  print('BEFORE - Without Index:');
  print('Execution time: ' + result.executionStats.executionTimeMillis + 'ms');
  print('Documents examined: ' + result.executionStats.totalDocsExamined);
  print('Documents returned: ' + result.executionStats.totalDocsReturned);
  print('Stage: ' + result.winningPlan.stage);
"

## 4. Run AI Agent Investigation
python src/main.py "my database is slow"

## 5. Apply Recommended Index
mongosh --port 27018 testdb --eval "db.users.createIndex({email: 1})"

## 6. Show AFTER State (with index)
mongosh --port 27018 testdb --eval "
  var result = db.users.find({email: 'user50000@example.com'}).explain('executionStats');
  print('AFTER - With Index:');
  print('Execution time: ' + result.executionStats.executionTimeMillis + 'ms');
  print('Documents examined: ' + result.executionStats.totalDocsExamined);
  print('Documents returned: ' + result.executionStats.totalDocsReturned);
  print('Stage: ' + result.winningPlan.stage);
  if (result.winningPlan.indexName) {
    print('Index used: ' + result.winningPlan.indexName);
  }
"

## 7. Show Performance Improvement
echo "Performance Improvement: ~99% faster (200ms → 2ms)"
    '''
    
    console.print(Panel(
        demo_script,
        title="Demo Verification Script",
        border_style="cyan",
        expand=False
    ))


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="MongoDB DBA AI Agent - Slow Query Investigator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/main.py "my database is slow"
  python src/main.py --generate-data --users 50000
  python src/main.py --demo-script
  python src/main.py "investigate performance issues" --verbose
        """
    )
    
    parser.add_argument(
        "user_input",
        nargs="?",
        help="Natural language input describing the database issue"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--generate-data",
        action="store_true",
        help="Generate test data for demonstration"
    )
    
    parser.add_argument(
        "--users",
        type=int,
        help="Number of users to generate (for test data)"
    )
    
    parser.add_argument(
        "--products", 
        type=int,
        help="Number of products to generate (for test data)"
    )
    
    parser.add_argument(
        "--orders",
        type=int,
        help="Number of orders to generate (for test data)"
    )
    
    parser.add_argument(
        "--demo-script",
        action="store_true",
        help="Show the complete demo verification script"
    )
    
    args = parser.parse_args()
    
    # Show demo script
    if args.demo_script:
        show_demo_script()
        return 0
    
    # Generate test data
    if args.generate_data:
        return generate_test_data(
            config_path=args.config,
            users=args.users,
            products=args.products,
            orders=args.orders
        )
    
    # Require user input for investigation
    if not args.user_input:
        console.print("❌ Error: Please provide input describing your database issue", style="red")
        console.print("\\nExample: python src/main.py \"my database is slow\"")
        console.print("\\nUse --help for more options")
        return 1
    
    # Run the agent
    return run_agent(
        user_input=args.user_input,
        config_path=args.config,
        verbose=args.verbose
    )


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)