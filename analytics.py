import sqlite3
import pandas as pd
import math

DB_PATH = "telemetry.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def fetch_route_summary():
    query = """
    SELECT 
        route_id,
        COUNT(DISTINCT vehicle_id) AS active_vehicles,
        ROUND(AVG(delay_minutes), 1) AS avg_delay_min,
        MAX(delay_minutes) AS max_delay_min,
        COUNT(id) AS total_pings_recorded
    FROM vehicle_pings
    GROUP BY route_id
    ORDER BY avg_delay_min DESC;
    """
    with get_connection() as conn:
        return pd.read_sql_query(query, conn)


def fetch_live_fleet_positions():
    query = """
    WITH ranked_pings AS (
        SELECT 
            route_id,
            vehicle_id,
            destination,
            latitude,
            longitude,
            heading,
            delay_minutes,
            datetime(ping_timestamp, 'unixepoch', 'localtime') AS ping_time,
            ROW_NUMBER() OVER(PARTITION BY vehicle_id ORDER BY ping_timestamp DESC) as rn
        FROM vehicle_pings
    )
    SELECT 
        route_id,
        vehicle_id,
        destination,
        latitude,
        longitude,
        heading,
        delay_minutes,
        ping_time
    FROM ranked_pings
    WHERE rn = 1;
    """
    with get_connection() as conn:
        return pd.read_sql_query(query, conn)


def fetch_pipeline_health():
    query = """
    SELECT 
        (SELECT COUNT(*) FROM vehicle_pings) AS valid_pings,
        (SELECT COUNT(*) FROM quarantine_logs) AS quarantined_records;
    """
    with get_connection() as conn:
        return pd.read_sql_query(query, conn)


def haversine_distance(lat1, lon1, lat2, lon2):
    r = 3958.8  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    return r * c


def detect_bus_bunching(max_gap_miles=0.4):
    df = fetch_live_fleet_positions()
    if df.empty:
        return pd.DataFrame()

    bunching_incidents = []
    grouped = df.groupby(["route_id", "destination"])

    for (route, dest), group in grouped:
        if len(group) < 2:
            continue

        records = group.to_dict("records")
        for i in range(len(records)):
            for j in range(i + 1, len(records)):
                b1, b2 = records[i], records[j]
                dist = haversine_distance(
                    b1["latitude"], b1["longitude"],
                    b2["latitude"], b2["longitude"]
                )

                if dist <= max_gap_miles:
                    delay_delta = abs(b1["delay_minutes"] - b2["delay_minutes"])
                    
                    if dist < 0.2 and delay_delta >= 15:
                        recommendation = "INTERVENTION: Instruct trailing vehicle to run express / skip stops to restore schedule spacing."
                    elif dist < 0.35 and delay_delta >= 5:
                        recommendation = f"HOLDING ACTION: Hold vehicle #{b2['vehicle_id']} at next major time point for 3-4 mins to rebuild headway."
                    else:
                        recommendation = "MONITOR: Headway compression observed; track arrival cadence at next terminal."

                    bunching_incidents.append({
                        "route_id": route,
                        "destination": dest,
                        "lead_vehicle": b1["vehicle_id"],
                        "trailing_vehicle": b2["vehicle_id"],
                        "distance_miles": round(dist, 2),
                        "lead_delay": b1["delay_minutes"],
                        "trail_delay": b2["delay_minutes"],
                        "delay_gap": delay_delta,
                        "severity": "CRITICAL" if dist < 0.2 else "WARNING",
                        "dispatch_action": recommendation
                    })

    return pd.DataFrame(bunching_incidents)


if __name__ == "__main__":
    print("\n=== Pipeline Health ===")
    print(fetch_pipeline_health().to_string(index=False))

    print("\n=== Route Performance Summary ===")
    print(fetch_route_summary().to_string(index=False))