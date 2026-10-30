CREATE TABLE IF NOT EXISTS vehicle_pings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id TEXT NOT NULL,
    vehicle_id TEXT NOT NULL,
    trip_id TEXT,
    direction TEXT,
    destination TEXT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    heading REAL,
    delay_minutes INTEGER DEFAULT 0,
    next_stop_name TEXT,
    ping_timestamp INTEGER NOT NULL,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_ping UNIQUE (vehicle_id, ping_timestamp)
);

CREATE TABLE IF NOT EXISTS quarantine_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_payload TEXT NOT NULL,
    rejection_reason TEXT NOT NULL,
    quarantined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_route_timestamp ON vehicle_pings(route_id, ping_timestamp);
CREATE INDEX IF NOT EXISTS idx_vehicle ON vehicle_pings(vehicle_id);