import json
import sqlite3
import sys
import time
import requests

ROUTES_TO_TRACK = ["21", "42", "47", "17"]
DB_PATH = "telemetry.db"
API_URL = "https://www3.septa.org/api/TransitView/index.php"


def init_db():
  with open("schema.sql", "r") as f:
    schema_sql = f.read()
  with sqlite3.connect(DB_PATH) as conn:
    conn.executescript(schema_sql)


def validate_and_parse(bus):
  """Validates payload schema.

  Raises ValueError if corrupted or drifted.
  """
  required_fields = ["VehicleID", "lat", "lng", "timestamp"]
  for field in required_fields:
    if field not in bus or bus[field] is None:
      raise ValueError(f"Missing required field: {field}")

  lat = float(bus["lat"])
  lng = float(bus["lng"])

  # Bounding box validation for Greater Philadelphia region
  if not (39.5 <= lat <= 40.5) or not (-75.5 <= lng <= -74.5):
    raise ValueError(f"Coordinates ({lat}, {lng}) out of realistic bounds")

  return {
      "route_id": str(bus.get("route_id", "UNKNOWN")),
      "vehicle_id": str(bus["VehicleID"]),
      "trip_id": str(bus.get("trip", "")),
      "direction": str(bus.get("Direction", "")),
      "destination": str(bus.get("destination", "")),
      "latitude": lat,
      "longitude": lng,
      "heading": float(bus.get("heading", 0.0) or 0.0),
      "delay_minutes": int(bus.get("late", 0) or 0),
      "next_stop_name": str(bus.get("next_stop_name", "")),
      "ping_timestamp": int(bus["timestamp"]),
  }


def run_ingestion_cycle():
  init_db()

  total_inserted = 0
  total_quarantined = 0

  with sqlite3.connect(DB_PATH) as conn:
    cursor = conn.cursor()

    for route in ROUTES_TO_TRACK:
      try:
        resp = requests.get(f"{API_URL}?route={route}", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        vehicles = data.get("bus", [])

        for bus in vehicles:
          try:
            record = validate_and_parse(bus)
            cursor.execute(
                """
                            INSERT OR IGNORE INTO vehicle_pings (
                                route_id, vehicle_id, trip_id, direction, destination,
                                latitude, longitude, heading, delay_minutes, next_stop_name, ping_timestamp
                            ) VALUES (
                                :route_id, :vehicle_id, :trip_id, :direction, :destination,
                                :latitude, :longitude, :heading, :delay_minutes, :next_stop_name, :ping_timestamp
                            )
                        """,
                record,
            )
            if cursor.rowcount > 0:
              total_inserted += 1

          except (ValueError, TypeError, KeyError) as validation_err:
            cursor.execute(
                """
                            INSERT INTO quarantine_logs (raw_payload, rejection_reason)
                            VALUES (?, ?)
                        """,
                (json.dumps(bus), str(validation_err)),
            )
            total_quarantined += 1

      except Exception as net_err:
        print(f"[ERROR] Failed to fetch Route {route}: {net_err}")

    conn.commit()

  print(
      f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ingested: {total_inserted} pings"
      f" | Quarantined: {total_quarantined} records"
  )


if __name__ == "__main__":
  run_ingestion_cycle()