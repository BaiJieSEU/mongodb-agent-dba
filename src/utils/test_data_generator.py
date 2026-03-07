"""Test data generator for creating slow query scenarios"""

import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from faker import Faker
from utils.mongodb_client import MongoDBManager
from utils.config_loader import DemoConfig

logger = logging.getLogger(__name__)
fake = Faker()


class TestDataGenerator:
    """Generates test data and slow query scenarios"""
    
    def __init__(self, mongo_manager: MongoDBManager, demo_config: DemoConfig):
        self.mongo_manager = mongo_manager
        self.demo_config = demo_config
        self.db_name = "testdb"
    
    def setup_test_environment(self):
        """Set up the complete test environment with data and slow query scenarios"""
        logger.info("Setting up test environment")
        
        # Create test data
        self.create_users_collection()
        self.create_products_collection()
        self.create_orders_collection()
        
        # Create slow query scenarios
        self.create_slow_query_scenarios()
        
        logger.info("Test environment setup complete")
    
    def create_users_collection(self):
        """Create users collection with test data (missing email index)"""
        logger.info(f"Creating users collection with {self.demo_config.users_count:,} users")
        
        try:
            with self.mongo_manager.get_monitored_db(self.db_name) as db:
                users_coll = db.users
                
                # Drop existing collection and indexes
                users_coll.drop()
                
                # Generate user documents
                users = []
                for i in range(self.demo_config.users_count):
                    user = {
                        "user_id": i + 1,
                        "email": f"user{i+1}@example.com",
                        "name": fake.name(),
                        "age": random.randint(18, 80),
                        "status": random.choice(["active", "inactive", "pending"]),
                        "created_at": fake.date_time_between(start_date="-2y", end_date="now"),
                        "profile": {
                            "city": fake.city(),
                            "country": fake.country(),
                            "preferences": {
                                "newsletter": random.choice([True, False]),
                                "notifications": random.choice([True, False])
                            }
                        },
                        "tags": random.sample(["premium", "vip", "regular", "new", "loyal"], random.randint(1, 3))
                    }
                    users.append(user)
                    
                    # Insert in batches
                    if len(users) == 1000:
                        users_coll.insert_many(users)
                        users.clear()
                
                # Insert remaining users
                if users:
                    users_coll.insert_many(users)
                
                logger.info(f"Created {self.demo_config.users_count:,} users")
                
                # Intentionally do NOT create index on email field to demonstrate missing index scenario
                
        except Exception as e:
            logger.error(f"Error creating users collection: {e}")
    
    def create_products_collection(self):
        """Create products collection with test data"""
        logger.info(f"Creating products collection with {self.demo_config.products_count:,} products")
        
        try:
            with self.mongo_manager.get_monitored_db(self.db_name) as db:
                products_coll = db.products
                
                # Drop existing collection
                products_coll.drop()
                
                categories = ["electronics", "clothing", "books", "home", "sports", "toys", "food"]
                
                products = []
                for i in range(self.demo_config.products_count):
                    product = {
                        "product_id": i + 1,
                        "name": fake.catch_phrase(),
                        "description": fake.text(max_nb_chars=200),
                        "category": random.choice(categories),
                        "price": round(random.uniform(10.0, 1000.0), 2),
                        "inventory": random.randint(0, 1000),
                        "rating": round(random.uniform(1.0, 5.0), 1),
                        "reviews_count": random.randint(0, 500),
                        "created_at": fake.date_time_between(start_date="-1y", end_date="now"),
                        "tags": random.sample(["new", "popular", "sale", "featured", "bestseller"], random.randint(0, 3)),
                        "specifications": {
                            "weight": f"{random.randint(1, 50)} kg",
                            "dimensions": f"{random.randint(10, 100)}x{random.randint(10, 100)} cm",
                            "color": fake.color_name()
                        }
                    }
                    products.append(product)
                    
                    # Insert in batches
                    if len(products) == 1000:
                        products_coll.insert_many(products)
                        products.clear()
                
                # Insert remaining products
                if products:
                    products_coll.insert_many(products)
                
                # Create suboptimal index (category, price) when queries often filter by (price, category)
                products_coll.create_index([("category", 1), ("price", 1)])
                
                logger.info(f"Created {self.demo_config.products_count:,} products")
                
        except Exception as e:
            logger.error(f"Error creating products collection: {e}")
    
    def create_orders_collection(self):
        """Create orders collection with test data"""
        logger.info(f"Creating orders collection with {self.demo_config.orders_count:,} orders")
        
        try:
            with self.mongo_manager.get_monitored_db(self.db_name) as db:
                orders_coll = db.orders
                
                # Drop existing collection
                orders_coll.drop()
                
                statuses = ["pending", "processing", "shipped", "delivered", "cancelled"]
                
                orders = []
                for i in range(self.demo_config.orders_count):
                    # Create order with 1-5 products
                    num_items = random.randint(1, 5)
                    total = 0
                    items = []
                    
                    for _ in range(num_items):
                        product_id = random.randint(1, min(self.demo_config.products_count, 1000))
                        quantity = random.randint(1, 3)
                        price = round(random.uniform(10.0, 500.0), 2)
                        total += price * quantity
                        
                        items.append({
                            "product_id": product_id,
                            "quantity": quantity,
                            "price": price
                        })
                    
                    order = {
                        "order_id": i + 1,
                        "user_id": random.randint(1, min(self.demo_config.users_count, 10000)),
                        "items": items,
                        "total": round(total, 2),
                        "status": random.choice(statuses),
                        "created_at": fake.date_time_between(start_date="-6M", end_date="now"),
                        "shipping_address": {
                            "street": fake.street_address(),
                            "city": fake.city(),
                            "country": fake.country(),
                            "zip_code": fake.zipcode()
                        },
                        "payment_method": random.choice(["credit_card", "paypal", "bank_transfer"])
                    }
                    orders.append(order)
                    
                    # Insert in batches
                    if len(orders) == 1000:
                        orders_coll.insert_many(orders)
                        orders.clear()
                
                # Insert remaining orders
                if orders:
                    orders_coll.insert_many(orders)
                
                # Create index on created_at for date range queries
                orders_coll.create_index([("created_at", 1)])
                
                logger.info(f"Created {self.demo_config.orders_count:,} orders")
                
        except Exception as e:
            logger.error(f"Error creating orders collection: {e}")
    
    def create_slow_query_scenarios(self):
        """Execute queries that will appear in the profiler as slow queries"""
        logger.info("Creating slow query scenarios")
        
        try:
            # Enable profiler
            self.mongo_manager.ensure_profiler_enabled(self.db_name, level=1)
            
            with self.mongo_manager.get_monitored_db(self.db_name) as db:
                
                # Scenario 1: Missing index on email field
                logger.info("Creating missing index scenario")
                users_coll = db.users
                for i in range(5):  # Execute multiple times to show up in profiler
                    email = f"user{random.randint(1, min(1000, self.demo_config.users_count))}@example.com"
                    result = list(users_coll.find({"email": email}))
                    time.sleep(0.1)  # Small delay
                
                # Scenario 2: Inefficient regex pattern
                logger.info("Creating inefficient regex scenario")
                products_coll = db.products
                for i in range(3):
                    # Regex without anchor - will scan entire collection
                    result = list(products_coll.find({"name": {"$regex": ".*phone.*", "$options": "i"}}))
                    time.sleep(0.1)
                
                # Scenario 3: Large result set without limit
                logger.info("Creating no-limit scenario")
                orders_coll = db.orders
                for i in range(2):
                    # Query that returns many documents without limit
                    result = list(orders_coll.find({"status": "pending"}))
                    time.sleep(0.1)
                
                # Scenario 4: Wrong index order
                logger.info("Creating wrong index order scenario")
                for i in range(3):
                    # Query filters by price first, then category
                    # But index is (category, price) which is suboptimal
                    result = list(products_coll.find({
                        "price": {"$gt": 100, "$lt": 500},
                        "category": "electronics"
                    }))
                    time.sleep(0.1)
                
                # Scenario 5: $where clause (if we want to demonstrate this)
                logger.info("Creating $where clause scenario")
                for i in range(2):
                    # JavaScript evaluation - very inefficient
                    result = list(users_coll.find({
                        "$where": "this.age > 25 && this.status == 'active'"
                    }))
                    time.sleep(0.1)
                
                # Wait a moment for profiler to capture all operations
                time.sleep(1)
                
                logger.info("Slow query scenarios created successfully")
                
        except Exception as e:
            logger.error(f"Error creating slow query scenarios: {e}")
    
    def run_verification_queries(self):
        """Run queries to verify the scenarios work as expected"""
        logger.info("Running verification queries")
        
        try:
            with self.mongo_manager.get_monitored_db(self.db_name) as db:
                
                # Test the missing index scenario
                print("\\n=== VERIFICATION: Missing Index Scenario ===")
                users_coll = db.users
                
                # Query without index
                start_time = time.time()
                result = list(users_coll.find({"email": "user500@example.com"}).explain("executionStats"))
                end_time = time.time()
                
                exec_stats = result[0]["executionStats"]
                print(f"Execution time: {(end_time - start_time)*1000:.1f}ms")
                print(f"Documents examined: {exec_stats['totalDocsExamined']:,}")
                print(f"Documents returned: {exec_stats['totalDocsReturned']}")
                print(f"Stage: {result[0]['winningPlan']['stage']}")
                
                # Show what happens with index
                print("\\n--- Creating index for comparison ---")
                users_coll.create_index([("email", 1)])
                
                start_time = time.time()
                result = list(users_coll.find({"email": "user500@example.com"}).explain("executionStats"))
                end_time = time.time()
                
                exec_stats = result[0]["executionStats"]
                print(f"Execution time with index: {(end_time - start_time)*1000:.1f}ms")
                print(f"Documents examined: {exec_stats['totalDocsExamined']:,}")
                print(f"Documents returned: {exec_stats['totalDocsReturned']}")
                print(f"Stage: {result[0]['winningPlan']['stage']}")
                
                # Remove the index to restore slow query scenario
                users_coll.drop_index([("email", 1)])
                print("Index removed to maintain slow query scenario")
                
        except Exception as e:
            logger.error(f"Error in verification: {e}")
    
    def cleanup_test_data(self):
        """Remove all test data"""
        logger.info("Cleaning up test data")
        
        try:
            with self.mongo_manager.get_monitored_db(self.db_name) as db:
                # Drop collections
                db.users.drop()
                db.products.drop()
                db.orders.drop()
                
                # Clear profiler collection
                db["system.profile"].drop()
                
                logger.info("Test data cleanup complete")
                
        except Exception as e:
            logger.error(f"Error cleaning up test data: {e}")
    
    def get_database_stats(self):
        """Get statistics about the test database"""
        try:
            with self.mongo_manager.get_monitored_db(self.db_name) as db:
                stats = {
                    "users_count": db.users.count_documents({}),
                    "products_count": db.products.count_documents({}),
                    "orders_count": db.orders.count_documents({}),
                    "profile_entries": db["system.profile"].count_documents({})
                }
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}


def main():
    """Standalone script to generate test data"""
    import argparse
    from utils.config_loader import load_config
    from utils.mongodb_client import MongoDBManager
    
    parser = argparse.ArgumentParser(description="Generate test data for MongoDB DBA Agent")
    parser.add_argument("--users", type=int, help="Number of users to create")
    parser.add_argument("--products", type=int, help="Number of products to create")
    parser.add_argument("--orders", type=int, help="Number of orders to create")
    parser.add_argument("--cleanup", action="store_true", help="Clean up existing test data")
    parser.add_argument("--verify", action="store_true", help="Run verification queries")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    # Override demo config with command line args
    if args.users:
        config.demo.users_count = args.users
    if args.products:
        config.demo.products_count = args.products
    if args.orders:
        config.demo.orders_count = args.orders
    
    # Initialize MongoDB manager
    mongo_manager = MongoDBManager(
        config.mongodb.agent_store,
        config.mongodb.monitored_cluster
    )
    
    # Test connections
    connections = mongo_manager.test_connections()
    if not connections["monitored_cluster"]:
        print("Error: Cannot connect to monitored cluster")
        return
    
    # Create generator
    generator = TestDataGenerator(mongo_manager, config.demo)
    
    if args.cleanup:
        generator.cleanup_test_data()
        print("Test data cleaned up")
        return
    
    if args.stats:
        stats = generator.get_database_stats()
        print("Database Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value:,}")
        return
    
    if args.verify:
        generator.run_verification_queries()
        return
    
    # Generate test data
    print(f"Generating test data:")
    print(f"  Users: {config.demo.users_count:,}")
    print(f"  Products: {config.demo.products_count:,}")
    print(f"  Orders: {config.demo.orders_count:,}")
    
    generator.setup_test_environment()
    
    print("\\nTest data generation complete!")
    print("\\nYou can now run the DBA agent to investigate slow queries:")
    print("  python src/main.py \"my database is slow\"")


if __name__ == "__main__":
    main()