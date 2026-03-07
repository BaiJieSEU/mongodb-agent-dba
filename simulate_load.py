#!/usr/bin/env python3
"""
MongoDB Load Simulator
Generates various slow query scenarios for DBA agent testing
"""

import pymongo
import random
import time
from datetime import datetime


class MongoLoadSimulator:
    def __init__(self, connection_uri="mongodb://localhost:27018/"):
        """Initialize connection to MongoDB cluster"""
        self.client = pymongo.MongoClient(connection_uri)
        self.db = self.client['testdb']
        self.users = self.db['users']
        
        # Enable profiler for all operations with 5ms threshold
        self.db.command('profile', 2, slowms=5)
        print("✅ Profiler enabled with 5ms threshold")
    
    def ensure_test_data(self, count=50000):
        """Ensure we have test data with proper fields for scenarios"""
        current_count = self.users.count_documents({})
        if current_count >= count:
            print(f"✅ Test data already exists: {current_count} users")
            return
        
        print(f"📝 Creating {count} test users...")
        
        # Drop existing data to ensure clean state
        self.users.drop()
        
        # Create test users with fields for all scenarios
        users_batch = []
        statuses = ["active", "inactive"]
        
        for i in range(count):
            user = {
                "user_id": i,
                "email": f"user{i}@example.com",
                "name": f"User {i}",
                "age": random.randint(18, 80),
                "status": random.choice(statuses),
                "created_at": datetime.utcnow(),
                "last_login": datetime.utcnow()
            }
            users_batch.append(user)
            
            # Insert in batches for performance
            if len(users_batch) >= 1000:
                self.users.insert_many(users_batch)
                users_batch = []
                print(f"  Inserted {i+1}/{count} users", end='\r')
        
        # Insert remaining users
        if users_batch:
            self.users.insert_many(users_batch)
        
        print(f"\n✅ Created {count} test users")
    
    def scenario_1_missing_email_index(self):
        """
        Scenario 1: Missing Email Index
        - No index on email field
        - Query by email causes full collection scan
        """
        print("\n🔍 Running Scenario 1: Missing Email Index")
        
        # Ensure no email index exists
        indexes = list(self.users.list_indexes())
        for idx in indexes:
            if 'email' in idx.get('key', {}):
                self.users.drop_index(idx['name'])
                print(f"  Dropped existing email index: {idx['name']}")
        
        # Run slow queries that need email index
        test_emails = [
            f"user{random.randint(0, 49999)}@example.com" 
            for _ in range(3)
        ]
        
        for email in test_emails:
            start = time.time()
            result = list(self.users.find({"email": email}))
            duration = (time.time() - start) * 1000
            print(f"  Query email={email}: {len(result)} results in {duration:.1f}ms")
            time.sleep(0.1)  # Small delay between queries
    
    def scenario_2_wrong_compound_index_order(self):
        """
        Scenario 2: Wrong Compound Index Order
        - Create compound index with wrong field order: {age: 1, status: 1}
        - Query with status first: {status: "active", age: {$gt: 30}}
        - This forces MongoDB to scan many index entries
        """
        print("\n🔍 Running Scenario 2: Wrong Compound Index Order")
        
        # Drop any existing indexes on age/status
        indexes = list(self.users.list_indexes())
        for idx in indexes:
            key = idx.get('key', {})
            if 'age' in key or 'status' in key:
                if idx['name'] != '_id_':  # Don't drop the _id index
                    self.users.drop_index(idx['name'])
                    print(f"  Dropped existing index: {idx['name']}")
        
        # Create compound index in WRONG order (age first, status second)
        self.users.create_index([("age", 1), ("status", 1)])
        print("  Created compound index: {age: 1, status: 1}")
        
        # Run queries that would benefit from {status: 1, age: 1} instead
        age_thresholds = [25, 30, 35, 40, 45]
        
        for age_threshold in age_thresholds:
            start = time.time()
            # Query with status first (poor index usage)
            result = list(self.users.find({
                "status": "active",
                "age": {"$gt": age_threshold}
            }))
            duration = (time.time() - start) * 1000
            print(f"  Query status=active, age>{age_threshold}: {len(result)} results in {duration:.1f}ms")
            time.sleep(0.1)
    
    def scenario_3_where_disables_index(self):
        """
        Scenario 3: $where Clause Disables Index
        - Create email index
        - Use $where clause which forces full collection scan despite index existing
        """
        print("\n🔍 Running Scenario 3: $where Disables Index")
        
        # Ensure email index exists
        try:
            self.users.create_index("email")
            print("  Created email index")
        except pymongo.errors.DuplicateKeyError:
            print("  Email index already exists")
        
        # Run queries using $where which disables index usage
        test_emails = [
            f"user{random.randint(0, 49999)}@example.com" 
            for _ in range(3)
        ]
        
        for email in test_emails:
            start = time.time()
            # Use $where which forces COLLSCAN despite email index existing
            result = list(self.users.find({
                "$where": f"this.email == '{email}'"
            }))
            duration = (time.time() - start) * 1000
            print(f"  $where email='{email}': {len(result)} results in {duration:.1f}ms")
            time.sleep(0.1)
    
    def scenario_4_low_selectivity_index(self):
        """
        Scenario 4: Low Selectivity Index
        - Create index on status field (only has 2 values: active/inactive)
        - Query by status examines many documents even with index
        - Low selectivity makes index less effective
        """
        print("\n🔍 Running Scenario 4: Low Selectivity Index")
        
        # Create status index (low selectivity - only 2 possible values)
        try:
            self.users.create_index("status")
            print("  Created status index (low selectivity)")
        except pymongo.errors.DuplicateKeyError:
            print("  Status index already exists")
        
        # Check distribution of status values
        active_count = self.users.count_documents({"status": "active"})
        inactive_count = self.users.count_documents({"status": "inactive"})
        total = active_count + inactive_count
        print(f"  Status distribution: active={active_count} ({active_count/total*100:.1f}%), inactive={inactive_count} ({inactive_count/total*100:.1f}%)")
        
        # Run queries on low-selectivity field
        statuses = ["active", "inactive"]
        
        for status in statuses * 2:  # Run each status query twice
            start = time.time()
            result = list(self.users.find({"status": status}))
            duration = (time.time() - start) * 1000
            print(f"  Query status='{status}': {len(result)} results in {duration:.1f}ms")
            time.sleep(0.1)
    
    def run_all_scenarios(self):
        """Run all slow query scenarios"""
        print("🚀 MongoDB Load Simulator - Generating Slow Query Scenarios")
        print("=" * 65)
        
        # Ensure test data exists
        self.ensure_test_data()
        
        # Run all scenarios
        self.scenario_1_missing_email_index()
        self.scenario_2_wrong_compound_index_order() 
        self.scenario_3_where_disables_index()
        self.scenario_4_low_selectivity_index()
        
        print("\n" + "=" * 65)
        print("✅ All scenarios completed!")
        
        # Show summary
        self.show_profiler_summary()
    
    def show_profiler_summary(self):
        """Show summary of captured slow queries"""
        print("\n📊 Profiler Summary:")
        
        # Count slow queries by type
        slow_queries = list(self.db['system.profile'].find({
            'millis': {'$gte': 5}
        }).sort('ts', -1).limit(20))
        
        print(f"  Total slow queries captured: {len(slow_queries)}")
        
        # Group by query patterns
        patterns = {}
        for query in slow_queries:
            command = query.get('command', {})
            if 'find' in command:
                filter_pattern = str(command.get('filter', {}))
                patterns[filter_pattern] = patterns.get(filter_pattern, 0) + 1
            elif '$where' in str(command):
                patterns['$where queries'] = patterns.get('$where queries', 0) + 1
        
        print("  Query patterns:")
        for pattern, count in patterns.items():
            print(f"    {pattern}: {count} queries")
    
    def cleanup(self):
        """Clean up connections"""
        if hasattr(self, 'client'):
            self.client.close()


def main():
    """Main function to run load simulation"""
    simulator = None
    try:
        simulator = MongoLoadSimulator()
        simulator.run_all_scenarios()
        
    except KeyboardInterrupt:
        print("\n⚠️ Simulation interrupted by user")
    except Exception as e:
        print(f"❌ Error running simulation: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if simulator:
            simulator.cleanup()


if __name__ == "__main__":
    main()