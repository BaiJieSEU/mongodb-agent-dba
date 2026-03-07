#!/usr/bin/env python3
"""Create a realistic demo scenario for showcasing the DBA agent"""

import random
import time
from pymongo import MongoClient

def create_substantial_test_data():
    """Create more substantial test data for realistic demo"""
    print("🔧 Setting up realistic demo scenario...")
    
    client = MongoClient("mongodb://localhost:27018", serverSelectionTimeoutMS=5000)
    db = client.testdb
    
    # Enable profiler
    db.command("profile", 1, slowms=100)
    
    # Create users collection (50,000 users - enough to show real performance impact)
    print("Creating users collection...")
    users_coll = db.users
    users_coll.drop()
    
    # Insert users in batches
    batch_size = 1000
    total_users = 50000
    
    for batch_start in range(0, total_users, batch_size):
        users_batch = []
        for i in range(batch_start, min(batch_start + batch_size, total_users)):
            user = {
                "user_id": i + 1,
                "email": f"user{i+1}@example.com",
                "name": f"User {i+1}",
                "age": random.randint(18, 80),
                "status": random.choice(["active", "inactive", "pending"]),
                "created_at": time.time() - random.randint(0, 86400 * 365),  # Random date within last year
                "profile": {
                    "city": f"City{random.randint(1, 100)}",
                    "country": f"Country{random.randint(1, 20)}",
                    "preferences": {
                        "newsletter": random.choice([True, False]),
                        "notifications": random.choice([True, False])
                    }
                }
            }
            users_batch.append(user)
        
        users_coll.insert_many(users_batch)
        if (batch_start + batch_size) % 10000 == 0:
            print(f"   Inserted {batch_start + batch_size:,} users...")
    
    print(f"✅ Created {total_users:,} users (intentionally without email index)")
    
    # Create some slow query scenarios
    print("\\nExecuting slow queries to populate profiler...")
    
    # Multiple slow email lookups
    for i in range(5):
        email = f"user{random.randint(1000, 49000)}@example.com"
        start_time = time.time()
        result = list(users_coll.find({"email": email}))
        end_time = time.time()
        print(f"   Email lookup {i+1}: {(end_time-start_time)*1000:.1f}ms")
        time.sleep(0.5)  # Small delay to ensure separate profiler entries
    
    # Create products for regex scenario
    print("\\nCreating products collection...")
    products_coll = db.products
    products_coll.drop()
    
    products = []
    product_names = [
        "iPhone 14", "Samsung Galaxy", "MacBook Pro", "Dell Laptop", 
        "Sony Headphones", "Nike Shoes", "Adidas Sneakers", "Apple Watch",
        "Google Pixel", "Microsoft Surface", "HP Printer", "Canon Camera"
    ]
    
    for i in range(5000):
        product = {
            "product_id": i + 1,
            "name": f"{random.choice(product_names)} {random.randint(1, 100)}",
            "category": random.choice(["electronics", "clothing", "books", "home"]),
            "price": round(random.uniform(10.0, 1000.0), 2),
            "description": f"High quality {random.choice(product_names).lower()}"
        }
        products.append(product)
    
    products_coll.insert_many(products)
    print(f"✅ Created {len(products):,} products")
    
    # Execute inefficient regex queries
    print("\\nExecuting inefficient regex queries...")
    for i in range(3):
        start_time = time.time()
        result = list(products_coll.find({"name": {"$regex": ".*phone.*", "$options": "i"}}))
        end_time = time.time()
        print(f"   Regex query {i+1}: {(end_time-start_time)*1000:.1f}ms, found {len(result)} products")
        time.sleep(0.5)
    
    client.close()
    print("\\n🎉 Demo scenario setup complete!")

def show_before_after_demo():
    """Demonstrate the before/after scenario"""
    print("\\n" + "="*60)
    print("DEMO VERIFICATION - BEFORE/AFTER INDEX CREATION")
    print("="*60)
    
    client = MongoClient("mongodb://localhost:27018", serverSelectionTimeoutMS=5000)
    db = client.testdb
    users_coll = db.users
    
    test_email = "user25000@example.com"
    
    print(f"\\n=== BEFORE: Query without index ===")
    print(f"Query: db.users.find({{email: '{test_email}'}})")
    
    # Run query and measure time
    start_time = time.time()
    result = list(users_coll.find({"email": test_email}))
    end_time = time.time()
    query_time = (end_time - start_time) * 1000
    
    # Get explain plan
    explain_result = users_coll.find({"email": test_email}).explain()
    exec_stats = explain_result["executionStats"]
    winning_plan = explain_result["queryPlanner"]["winningPlan"]
    
    print(f"Results:")
    print(f"  • Execution time: {query_time:.1f}ms")
    print(f"  • Documents examined: {exec_stats['totalDocsExamined']:,}")
    print(f"  • Documents returned: {exec_stats.get('totalDocsReturned', len(result))}")
    print(f"  • Execution stage: {winning_plan['stage']}")
    print(f"  • Index used: None (full collection scan)")
    
    print(f"\\n=== Creating recommended index ===")
    print(f"Command: db.users.createIndex({{email: 1}})")
    
    # Create the index
    users_coll.create_index([("email", 1)])
    print("✅ Index created successfully")
    
    print(f"\\n=== AFTER: Query with index ===")
    print(f"Query: db.users.find({{email: '{test_email}'}})")
    
    # Run same query with index
    start_time = time.time()
    result = list(users_coll.find({"email": test_email}))
    end_time = time.time()
    query_time_with_index = (end_time - start_time) * 1000
    
    # Get explain plan with index
    explain_result = users_coll.find({"email": test_email}).explain()
    exec_stats = explain_result["executionStats"]
    winning_plan = explain_result["queryPlanner"]["winningPlan"]
    
    print(f"Results:")
    print(f"  • Execution time: {query_time_with_index:.1f}ms")
    print(f"  • Documents examined: {exec_stats['totalDocsExamined']:,}")
    print(f"  • Documents returned: {exec_stats.get('totalDocsReturned', len(result))}")
    print(f"  • Execution stage: {winning_plan['stage']}")
    if "indexName" in winning_plan:
        print(f"  • Index used: {winning_plan['indexName']}")
    elif "inputStage" in winning_plan and winning_plan["inputStage"]["stage"] == "IXSCAN":
        print(f"  • Index used: {winning_plan['inputStage'].get('indexName', 'email_1')}")
    
    # Calculate improvement
    improvement = ((query_time - query_time_with_index) / query_time) * 100
    speedup = query_time / query_time_with_index
    
    print(f"\\n=== PERFORMANCE IMPROVEMENT ===")
    print(f"  • Time reduction: {query_time:.1f}ms → {query_time_with_index:.1f}ms")
    print(f"  • Performance improvement: {improvement:.1f}%")
    print(f"  • Speedup factor: {speedup:.0f}x faster")
    
    # Remove index to restore demo scenario
    users_coll.drop_index([("email", 1)])
    print(f"\\n(Index removed to restore demo scenario)")
    
    client.close()

def main():
    """Main demo setup function"""
    print("MongoDB DBA Agent - Demo Scenario Setup")
    
    try:
        # Test connection first
        client = MongoClient("mongodb://localhost:27018", serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        client.close()
        
        # Create substantial test data
        create_substantial_test_data()
        
        # Show before/after demonstration
        show_before_after_demo()
        
        print("\\n🚀 Ready for agent demonstration!")
        print("\\nNext steps:")
        print("1. Ensure Ollama is running with qwen2.5-coder:7b")
        print("2. Run: python src/main.py 'my database is slow'")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("Please ensure MongoDB is running on port 27018")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)