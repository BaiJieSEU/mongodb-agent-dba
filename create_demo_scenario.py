#!/usr/bin/env python3
"""
Demo scenario: multiple health issues across five collections.

What this creates
─────────────────
  users      100k docs  no index on email / status / age        → slow queries (§5) + missing index (§6)
  products    50k docs  no index on category / price             → slow queries (§5) + missing index (§6)
  orders     100k docs  no index on user_id / status / amount    → slow queries (§5) + missing index (§6)
  sessions    30k docs  has session_token_1 + user_id_1 indexes,
                        but neither field is ever queried         → unused indexes (§7)
  audit_log   10k docs  has action_1 index, never queried        → unused index  (§7)

Sections triggered
──────────────────
  §5 Query Performance  WARNING   10 slow ops across 3 collections
  §6 Missing Indexes    CRITICAL  users, products, orders — only _id present
  §7 Unused Indexes     WARNING   3 indexes with 0 ops since restart
"""

import random
import time
from pymongo import MongoClient, ASCENDING

MONGO_URI = "mongodb://localhost:27018"
DB        = "testdb"


# ── helpers ───────────────────────────────────────────────────────────────────

def connect():
    c = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    c.admin.command("ping")
    return c


def batch_insert(collection, docs, batch_size=2000, label=""):
    for i in range(0, len(docs), batch_size):
        collection.insert_many(docs[i:i + batch_size])
        if label:
            done = min(i + batch_size, len(docs))
            if done % 20000 == 0 or done == len(docs):
                print(f"   {label}: {done:,} / {len(docs):,}")


# ── collection builders ───────────────────────────────────────────────────────

def build_users(db, n=100_000):
    """100k users — intentionally NO index on email, status, age."""
    print(f"\nBuilding users ({n:,} docs, no secondary indexes)…")
    db.users.drop()
    statuses = ["active", "inactive", "pending", "suspended"]
    docs = [
        {
            "user_id":    i + 1,
            "email":      f"user{i + 1}@example.com",
            "name":       f"User {i + 1}",
            "age":        random.randint(18, 80),
            "status":     random.choice(statuses),
            "created_at": time.time() - random.randint(0, 86400 * 730),
            "profile": {
                "city":    f"City{random.randint(1, 200)}",
                "country": f"Country{random.randint(1, 50)}",
                "preferences": {
                    "newsletter":     random.choice([True, False]),
                    "notifications":  random.choice([True, False]),
                    "theme":          random.choice(["light", "dark"]),
                },
            },
        }
        for i in range(n)
    ]
    batch_insert(db.users, docs, label="users")
    print(f"   ✓ {n:,} users — no index on email / status / age")


def build_products(db, n=50_000):
    """50k products — intentionally NO index on category, price."""
    print(f"\nBuilding products ({n:,} docs, no secondary indexes)…")
    db.products.drop()
    categories = ["electronics", "clothing", "books", "home", "sports", "beauty", "toys"]
    names      = ["Widget", "Gadget", "Doohickey", "Thingamajig", "Gizmo", "Contraption"]
    brands     = ["Acme", "Globex", "Initech", "Umbrella", "Stark", "Wayne"]
    docs = [
        {
            "product_id": i + 1,
            "name":       f"{random.choice(brands)} {random.choice(names)} {random.randint(1, 999)}",
            "category":   random.choice(categories),
            "price":      round(random.uniform(5.0, 2000.0), 2),
            "stock":      random.randint(0, 500),
            "rating":     round(random.uniform(1.0, 5.0), 1),
            "tags":       random.sample(["sale", "new", "featured", "clearance", "popular"], k=random.randint(0, 3)),
        }
        for i in range(n)
    ]
    batch_insert(db.products, docs, label="products")
    print(f"   ✓ {n:,} products — no index on category / price")


def build_orders(db, n=100_000):
    """100k orders — intentionally NO index on user_id, status, amount."""
    print(f"\nBuilding orders ({n:,} docs, no secondary indexes)…")
    db.orders.drop()
    statuses = ["pending", "processing", "shipped", "delivered", "cancelled", "refunded"]
    docs = [
        {
            "order_id":   f"ORD-{i + 1:07d}",
            "user_id":    random.randint(1, 100_000),
            "status":     random.choice(statuses),
            "amount":     round(random.uniform(10.0, 5000.0), 2),
            "items":      random.randint(1, 20),
            "created_at": time.time() - random.randint(0, 86400 * 365),
            "updated_at": time.time() - random.randint(0, 86400 * 30),
            "shipping": {
                "address": f"{random.randint(1, 9999)} Main St",
                "city":    f"City{random.randint(1, 200)}",
                "country": f"Country{random.randint(1, 50)}",
            },
        }
        for i in range(n)
    ]
    batch_insert(db.orders, docs, label="orders")
    print(f"   ✓ {n:,} orders — no index on user_id / status / amount")


def build_sessions(db, n=30_000):
    """
    30k sessions WITH indexes on session_token and user_id.
    These indexes are NEVER queried — triggers §7 Unused Indexes WARNING.
    """
    print(f"\nBuilding sessions ({n:,} docs, with unused indexes)…")
    db.sessions.drop()
    docs = [
        {
            "session_id":    f"sess-{i + 1:08d}",
            "session_token": f"tok_{random.randbytes(16).hex()}",
            "user_id":       random.randint(1, 100_000),
            "created_at":    time.time() - random.randint(0, 86400 * 30),
            "expires_at":    time.time() + random.randint(0, 86400 * 7),
            "ip_address":    f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            "user_agent":    random.choice(["Chrome/121", "Firefox/123", "Safari/17", "Edge/121"]),
        }
        for i in range(n)
    ]
    batch_insert(db.sessions, docs, label="sessions")

    # Create indexes AFTER insert — neither will ever be queried, so ops = 0
    db.sessions.create_index([("session_token", ASCENDING)], name="session_token_1")
    db.sessions.create_index([("user_id",       ASCENDING)], name="user_id_1")
    print(f"   ✓ {n:,} sessions — session_token_1 + user_id_1 indexes created (will show 0 ops)")


def build_audit_log(db, n=10_000):
    """
    10k audit log entries WITH index on action.
    Index is NEVER queried — triggers §7 Unused Indexes WARNING.
    """
    print(f"\nBuilding audit_log ({n:,} docs, with unused index)…")
    db.audit_log.drop()
    actions  = ["login", "logout", "update_profile", "change_password", "delete_account", "export_data"]
    resources = ["user", "order", "product", "payment", "session"]
    docs = [
        {
            "log_id":      i + 1,
            "action":      random.choice(actions),
            "resource":    random.choice(resources),
            "resource_id": random.randint(1, 100_000),
            "user_id":     random.randint(1, 100_000),
            "timestamp":   time.time() - random.randint(0, 86400 * 90),
            "ip_address":  f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            "result":      random.choice(["success", "failure", "error"]),
        }
        for i in range(n)
    ]
    batch_insert(db.audit_log, docs)

    # Create index AFTER insert — never queried, so ops = 0
    db.audit_log.create_index([("action", ASCENDING)], name="action_1")
    print(f"   ✓ {n:,} audit log entries — action_1 index created (will show 0 ops)")


# ── slow query generator ──────────────────────────────────────────────────────

def run_slow_queries(db):
    """
    Run queries that COLLSCAN large collections to populate system.profile.
    Profiler must already be enabled at slowms=5.
    """
    print("\nGenerating slow queries (populating system.profile)…")

    # ── users: email lookups (COLLSCAN 100k docs)
    print("   users: email lookups (full scan, no email index)…")
    for _ in range(4):
        uid    = random.randint(1, 100_000)
        email  = f"user{uid}@example.com"
        result = list(db.users.find({"email": email}))
        time.sleep(0.15)

    # ── users: status + age filter (COLLSCAN)
    print("   users: status/age filter queries…")
    for _ in range(3):
        list(db.users.find({
            "status": random.choice(["active", "suspended"]),
            "age":    {"$gte": random.randint(25, 40)},
        }).limit(50))
        time.sleep(0.15)

    # ── products: category + price range (COLLSCAN 50k docs)
    print("   products: category/price queries (full scan, no category index)…")
    for _ in range(4):
        list(db.products.find({
            "category": random.choice(["electronics", "clothing"]),
            "price":    {"$lt": random.uniform(50, 500)},
        }).limit(20))
        time.sleep(0.15)

    # ── orders: user_id lookup (COLLSCAN 100k docs)
    print("   orders: user_id lookups (full scan, no user_id index)…")
    for _ in range(5):
        uid    = random.randint(1, 100_000)
        result = list(db.orders.find({"user_id": uid}))
        time.sleep(0.15)

    # ── orders: status filter (COLLSCAN 100k docs)
    print("   orders: status filter queries…")
    for _ in range(3):
        list(db.orders.find({
            "status": random.choice(["pending", "processing"]),
        }).limit(100))
        time.sleep(0.15)

    print("   ✓ Slow queries complete — system.profile populated")


# ── verify ────────────────────────────────────────────────────────────────────

def verify(db):
    print("\nVerifying scenario…")

    counts = {
        "users":     db.users.count_documents({}),
        "products":  db.products.count_documents({}),
        "orders":    db.orders.count_documents({}),
        "sessions":  db.sessions.count_documents({}),
        "audit_log": db.audit_log.count_documents({}),
    }
    for name, n in counts.items():
        print(f"   {name:<12} {n:>8,} docs")

    # Slow queries in profiler
    threshold = 5
    slow = db["system.profile"].count_documents({"millis": {"$gte": threshold}})
    print(f"\n   system.profile: {slow} slow queries (≥{threshold}ms)")
    if slow < 5:
        print("   ⚠  fewer than 5 slow queries captured — try a lower slowms or re-run slow queries")
    else:
        print("   ✓  enough slow queries for WARNING/CRITICAL threshold")

    # Indexes with no usage
    print("\n   Index stats (sessions, audit_log):")
    for coll_name in ("sessions", "audit_log"):
        coll = db[coll_name]
        for stat in coll.aggregate([{"$indexStats": {}}]):
            ops = stat.get("accesses", {}).get("ops", 0)
            if isinstance(ops, dict):
                ops = ops.get("low", 0)
            name_str = stat.get("name", "?")
            flag = "← will show as unused" if ops == 0 and name_str != "_id_" else ""
            print(f"      {coll_name}.{name_str}: {ops} ops  {flag}")

    print("\n   Expected health check results:")
    print("   §5 Query Performance  ⚠ WARNING   — slow queries across users, products, orders")
    print("   §6 Missing Indexes    ✗ CRITICAL  — users, products, orders: only _id")
    print("   §7 Unused Indexes     ⚠ WARNING   — session_token_1, user_id_1, action_1: 0 ops")


# ── testUATdb collections ─────────────────────────────────────────────────────

def build_uat_inventory(db, n=20_000):
    """20k inventory records — no index on sku or warehouse_id → slow queries + missing index."""
    print(f"\nBuilding testUATdb.inventory ({n:,} docs, no secondary indexes)…")
    db.inventory.drop()
    statuses   = ["in_stock", "low_stock", "out_of_stock", "discontinued"]
    warehouses = [f"WH-{i:03d}" for i in range(1, 21)]
    docs = [
        {
            "sku":          f"SKU-{i + 1:07d}",
            "name":         f"Part {i + 1}",
            "warehouse_id": random.choice(warehouses),
            "quantity":     random.randint(0, 1000),
            "unit_cost":    round(random.uniform(1.0, 500.0), 2),
            "status":       random.choice(statuses),
            "last_updated": time.time() - random.randint(0, 86400 * 180),
        }
        for i in range(n)
    ]
    batch_insert(db.inventory, docs, label="inventory")
    print(f"   ✓ {n:,} inventory records — no index on sku / warehouse_id")


def build_uat_customers(db, n=15_000):
    """15k customers — has email_1 index but it is never queried → unused index."""
    print(f"\nBuilding testUATdb.customers ({n:,} docs, with unused index)…")
    db.customers.drop()
    tiers = ["bronze", "silver", "gold", "platinum"]
    docs = [
        {
            "customer_id": i + 1,
            "email":       f"uat_customer{i + 1}@example.com",
            "name":        f"UAT Customer {i + 1}",
            "tier":        random.choice(tiers),
            "region":      f"Region-{random.randint(1, 10)}",
            "created_at":  time.time() - random.randint(0, 86400 * 365),
        }
        for i in range(n)
    ]
    batch_insert(db.customers, docs, label="customers")
    db.customers.create_index([("email", ASCENDING)], name="email_1")
    print(f"   ✓ {n:,} customers — email_1 index created (will show 0 ops)")


def run_uat_slow_queries(db):
    """Slow queries against testUATdb collections to populate system.profile."""
    print("\nGenerating slow queries for testUATdb…")

    print("   inventory: warehouse_id lookups (full scan, no index)…")
    for _ in range(4):
        list(db.inventory.find({
            "warehouse_id": random.choice([f"WH-{i:03d}" for i in range(1, 21)]),
            "status":       random.choice(["in_stock", "low_stock"]),
        }).limit(50))
        time.sleep(0.15)

    print("   inventory: sku lookups (full scan, no index)…")
    for _ in range(3):
        list(db.inventory.find({"sku": f"SKU-{random.randint(1, 20000):07d}"}))
        time.sleep(0.15)

    print("   ✓ UAT slow queries complete")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("MongoDB DBA Agent — Demo Scenario Setup")
    print("=" * 50)

    try:
        client = connect()
    except Exception as e:
        print(f"\n✗ Cannot connect to {MONGO_URI}: {e}")
        print("  Start MongoDB on port 27018 first.")
        return 1

    db     = client[DB]
    db_uat = client["testUATdb"]

    # 1. Build collections — profiler OFF during inserts
    db.command("profile", 0)
    db_uat.command("profile", 0)

    build_users(db)
    build_products(db)
    build_orders(db)
    build_sessions(db)        # creates unused indexes
    build_audit_log(db)       # creates unused index

    build_uat_inventory(db_uat)
    build_uat_customers(db_uat)   # creates unused email_1 index

    # 2. Enable profiler at 5ms BEFORE running slow queries
    db.command("profile", 1, slowms=5)
    db_uat.command("profile", 1, slowms=5)
    print("\nProfiler enabled at level 1, slowms=5  (testdb + testUATdb)")

    # 3. Run slow queries to populate system.profile in both databases
    run_slow_queries(db)
    run_uat_slow_queries(db_uat)

    # 4. Verify everything looks right
    verify(db)

    client.close()

    print("\n" + "=" * 50)
    print("Setup complete. Run the health check:")
    print("  source venv/bin/activate && python src/main_agentic.py --health-check")
    print("  open $(ls -t reports/*.html | head -1)")
    return 0


if __name__ == "__main__":
    exit(main())
