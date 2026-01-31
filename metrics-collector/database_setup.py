"""
Database setup for PHCA metrics collection
Creates PostgreSQL + TimescaleDB tables for storing microservice metrics
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def create_database_and_tables():
    """Set up the metrics database with TimescaleDB hypertables"""
    
    # Database connection parameters
    DB_CONFIG = {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': 'your_password'  # Change this
    }
    
    # Connect to PostgreSQL server
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    # Create database
    try:
        cursor.execute("CREATE DATABASE phca_metrics;")
        print("✅ Database 'phca_metrics' created")
    except psycopg2.errors.DuplicateDatabase:
        print("ℹ️  Database 'phca_metrics' already exists")
    
    cursor.close()
    conn.close()
    
    # Connect to the new database
    DB_CONFIG['database'] = 'phca_metrics'
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Enable TimescaleDB extension
    cursor.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
    
    # Create metrics table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS microservice_metrics (
        time TIMESTAMPTZ NOT NULL,
        service_name TEXT NOT NULL,
        container_id TEXT NOT NULL,
        
        -- Resource metrics
        cpu_percent REAL,
        memory_percent REAL,
        memory_usage_mb REAL,
        memory_limit_mb REAL,
        
        -- Network metrics  
        network_rx_bytes BIGINT,
        network_tx_bytes BIGINT,
        network_rx_packets BIGINT,
        network_tx_packets BIGINT,
        
        -- Application metrics (from container stats)
        pids_current INTEGER,
        
        -- Load context
        load_pattern TEXT,
        active_users INTEGER,
        
        -- Metadata
        node_name TEXT,
        experiment_id TEXT
    );
    """
    
    cursor.execute(create_table_sql)
    
    # Convert to hypertable for time-series optimization
    try:
        cursor.execute("SELECT create_hypertable('microservice_metrics', 'time');")
        print("✅ Hypertable created for microservice_metrics")
    except Exception as e:
        if "already a hypertable" in str(e):
            print("ℹ️  Table is already a hypertable")
        else:
            print(f"⚠️  Error creating hypertable: {e}")
    
    # Create indexes for better query performance
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_service_time ON microservice_metrics (service_name, time DESC);",
        "CREATE INDEX IF NOT EXISTS idx_experiment ON microservice_metrics (experiment_id, time DESC);",
        "CREATE INDEX IF NOT EXISTS idx_load_pattern ON microservice_metrics (load_pattern, time DESC);"
    ]
    
    for index_sql in indexes:
        cursor.execute(index_sql)
    
    # Create events table for scaling decisions (future ML model outputs)
    events_table_sql = """
    CREATE TABLE IF NOT EXISTS scaling_events (
        time TIMESTAMPTZ NOT NULL,
        service_name TEXT NOT NULL,
        event_type TEXT NOT NULL, -- 'scale_up', 'scale_down', 'no_action'
        current_replicas INTEGER,
        target_replicas INTEGER,
        confidence_score REAL,
        model_version TEXT,
        experiment_id TEXT,
        
        -- Trigger metrics (what caused this decision)
        trigger_cpu REAL,
        trigger_memory REAL,
        trigger_request_rate REAL,
        
        PRIMARY KEY (time, service_name)
    );
    """
    
    cursor.execute(events_table_sql)
    
    try:
        cursor.execute("SELECT create_hypertable('scaling_events', 'time');")
        print("✅ Hypertable created for scaling_events")
    except Exception as e:
        if "already a hypertable" in str(e):
            print("ℹ️  Events table is already a hypertable")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("✅ Database setup complete!")
    print("📊 Tables created: microservice_metrics, scaling_events")
    print("🚀 Ready for metrics collection!")

if __name__ == "__main__":
    create_database_and_tables()