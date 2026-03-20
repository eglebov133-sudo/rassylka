"""
DB Migration: Add new columns for enhanced batching, SMTP tracking, and supplier archiving.
Run this script against the production database.
"""
import sqlite3
import sys
import os

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else "data/bidroute.db"

if not os.path.exists(DB_PATH):
    print(f"Database not found: {DB_PATH}")
    sys.exit(1)

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA journal_mode=WAL")
cursor = conn.cursor()

migrations = [
    # RoutingRule: new batching fields
    ("routing_rules", "batch1_size", "ALTER TABLE routing_rules ADD COLUMN batch1_size INTEGER DEFAULT 5"),
    ("routing_rules", "batch1_delay_seconds", "ALTER TABLE routing_rules ADD COLUMN batch1_delay_seconds INTEGER DEFAULT 120"),
    ("routing_rules", "batch2_size", "ALTER TABLE routing_rules ADD COLUMN batch2_size INTEGER DEFAULT 10"),
    ("routing_rules", "batch2_delay_seconds", "ALTER TABLE routing_rules ADD COLUMN batch2_delay_seconds INTEGER DEFAULT 120"),
    ("routing_rules", "escalation_hours", "ALTER TABLE routing_rules ADD COLUMN escalation_hours INTEGER DEFAULT 24"),
    ("routing_rules", "max_no_response", "ALTER TABLE routing_rules ADD COLUMN max_no_response INTEGER DEFAULT 10"),
    ("routing_rules", "auto_supplier_search", "ALTER TABLE routing_rules ADD COLUMN auto_supplier_search BOOLEAN DEFAULT 1"),
    # DistributionLog: SMTP tracking
    ("distribution_logs", "smtp_account_id", "ALTER TABLE distribution_logs ADD COLUMN smtp_account_id INTEGER"),
    # Supplier: archiving
    ("suppliers", "no_response_count", "ALTER TABLE suppliers ADD COLUMN no_response_count INTEGER DEFAULT 0"),
    ("suppliers", "archived_at", "ALTER TABLE suppliers ADD COLUMN archived_at DATETIME"),
]

applied = 0
for table, column, sql in migrations:
    # Check if column exists
    cursor.execute(f"PRAGMA table_info({table})")
    existing = [row[1] for row in cursor.fetchall()]
    if column in existing:
        print(f"  SKIP: {table}.{column} already exists")
        continue
    try:
        cursor.execute(sql)
        print(f"  OK:   {table}.{column} added")
        applied += 1
    except Exception as e:
        print(f"  ERR:  {table}.{column}: {e}")

conn.commit()
conn.close()
print(f"\nMigration complete: {applied} columns added")
