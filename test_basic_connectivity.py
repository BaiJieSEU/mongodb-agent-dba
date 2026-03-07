#!/usr/bin/env python3
"""Basic connectivity test for MongoDB instances"""

import sys
try:
    from pymongo import MongoClient
    from pymongo.errors import ServerSelectionTimeoutError
except ImportError:
    print("❌ pymongo not installed. Run: pip3 install pymongo")
    sys.exit(1)

def test_mongodb_connection(uri, name):
    """Test MongoDB connection"""
    print(f"Testing {name} ({uri})...")
    
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # Test connection
        client.admin.command('ping')
        print(f"✅ {name}: Connected successfully")
        
        # Get database list
        dbs = client.list_database_names()
        print(f"   Databases: {dbs}")
        
        # Test replica set status if applicable
        try:
            rs_status = client.admin.command("replSetGetStatus")
            print(f"   Replica Set: {rs_status['set']} (members: {len(rs_status['members'])})")
        except:
            print("   Replica Set: Not configured or not primary")
        
        client.close()
        return True
        
    except ServerSelectionTimeoutError:
        print(f"❌ {name}: Connection timeout")
        return False
    except Exception as e:
        print(f"❌ {name}: {str(e)}")
        return False

def test_profiler_setup(uri, db_name="testdb"):
    """Test profiler setup on monitored cluster"""
    print(f"\\nTesting profiler setup on {db_name}...")
    
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        db = client[db_name]
        
        # Enable profiler
        result = db.command("profile", 1, slowms=100)
        print(f"✅ Profiler enabled: {result}")
        
        # Check profiler status
        status = db.command("profile", -1)
        print(f"   Profiler level: {status.get('was', 0)}")
        print(f"   Slow threshold: {status.get('slowms', 100)}ms")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Profiler setup failed: {str(e)}")
        return False

def create_sample_data(uri, db_name="testdb"):
    """Create a small sample dataset for testing"""
    print(f"\\nCreating sample data in {db_name}...")
    
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        db = client[db_name]
        
        # Create a small users collection
        users_coll = db.users
        users_coll.drop()  # Clean start
        
        # Insert sample users (without email index)
        users = [
            {"user_id": i, "email": f"user{i}@example.com", "name": f"User {i}", "age": 20 + i % 40}
            for i in range(1, 1001)  # 1000 users
        ]
        users_coll.insert_many(users)
        print(f"✅ Created {len(users)} sample users")
        
        # Test a slow query (should scan all documents)
        print("\\nTesting slow query (email lookup without index)...")
        import time
        start_time = time.time()
        result = list(users_coll.find({"email": "user500@example.com"}))
        end_time = time.time()
        
        print(f"   Query result: {len(result)} documents found")
        print(f"   Query time: {(end_time - start_time)*1000:.1f}ms")
        
        # Run explain to see execution plan
        explain_result = users_coll.find({"email": "user500@example.com"}).explain()
        print(f"   Explain result keys: {list(explain_result.keys())}")
        
        if "executionStats" in explain_result:
            exec_stats = explain_result["executionStats"]
            print(f"   Documents examined: {exec_stats.get('totalDocsExamined', 'Unknown')}")
        
        if "winningPlan" in explain_result:
            print(f"   Execution stage: {explain_result['winningPlan'].get('stage', 'Unknown')}")
        elif "queryPlanner" in explain_result and "winningPlan" in explain_result["queryPlanner"]:
            print(f"   Execution stage: {explain_result['queryPlanner']['winningPlan'].get('stage', 'Unknown')}")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Sample data creation failed: {str(e)}")
        return False

def main():
    """Main test function"""
    print("🔍 MongoDB DBA Agent - Basic Connectivity Test\\n")
    
    # Test connections
    agent_store_ok = test_mongodb_connection("mongodb://localhost:27017", "Agent Store")
    monitored_ok = test_mongodb_connection("mongodb://localhost:27018", "Monitored Cluster")
    
    if not (agent_store_ok and monitored_ok):
        print("\\n❌ MongoDB connectivity issues detected")
        print("Please ensure both MongoDB instances are running:")
        print("  - Port 27017: Agent store (rs0)")
        print("  - Port 27018: Monitored cluster (rs1)")
        return 1
    
    # Test profiler setup
    profiler_ok = test_profiler_setup("mongodb://localhost:27018")
    
    if not profiler_ok:
        print("\\n⚠️  Profiler setup issues - slow queries may not be captured")
    
    # Create sample data
    data_ok = create_sample_data("mongodb://localhost:27018")
    
    if data_ok:
        print("\\n🎉 Basic setup validation completed successfully!")
        print("\\nNext steps:")
        print("1. Install required Python packages (Python 3.11+ recommended)")
        print("2. Setup Ollama with qwen2.5-coder:7b model")
        print("3. Run: python src/main.py 'my database is slow'")
    else:
        print("\\n❌ Setup validation failed")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)