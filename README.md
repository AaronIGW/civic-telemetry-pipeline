Civic Transit Telemetry & Dispatch Intelligence Engine
An end-to-end data engineering pipeline designed to ingest, validate, and monitor live streaming public transit telemetry from SEPTA in real time. Built with Python, SQLite, Pandas, SQL window functions, and Streamlit.

Pipeline Architecture & Execution Stages
1. Raw Telemetry Ingestion (scheduler.py / ingest.py)
  - Polling Daemon: Periodically polls live public transit REST API endpoints to capture moving fleet GPS updates.
  - Streaming Payload Capture: Ingests dynamic records containing route assignments, vehicle IDs, GPS coordinates, headings, and delay offsets.
2. Validation & Cleansing Pipeline (ingest.py)
  - Geographic Bounding Validation: Evaluates incoming coordinates against strict regional geographic bounds to filter faulty sensor pings.
  - Schema & Data Quality Checks: Verifies payload data types, ensuring non-null route keys, numerical delays, and valid heading directions.
  - Dead-Letter Quarantine: Isolates corrupted or out-of-bounds telemetry payloads into quarantine_logs with exact audit drop reasons, preventing runtime ingestion failures.
  - Relational Staging: Inserts validated vehicle pings directly into vehicle_pings with captured Unix epoch timestamps.
3. Relational Storage & Analytical Processing (telemetry.db / analytics.py)
  - Point-in-Time Fleet Snapshots: Leverages SQL CTEs with window functions (ROW_NUMBER() OVER(PARTITION BY vehicle_id ORDER BY ping_timestamp DESC)) to query the absolute latest known state of each active vehicle.
  - Spatial Headway Engine: Implements the Haversine trigonometric formula to calculate great-circle distances between adjacent vehicles operating along shared routes and directions.
  - Automated Dispatch Rules: Analyzes spatial proximity (sub-0.4 mile thresholds) and relative delay variances to trigger tiered operational recommendations (holding actions, express skip-stop mode, headway monitoring).
4. Operational Dashboard & Visualization (app.py)
  - Live Maplibre GPS Fleet Map: Visualizes active vehicles geographically, color-coded by schedule delay variance.
  - Real-Time Headway & Bunching Alerts: Surfaces critical clustering incidents dynamically with explicit vehicle pairs and recommended mitigation steps.
  - Automated Telemetry Refresh: Supports interval-based automated hot-reloading via sidebar controls to mirror live city transit conditions.

Database Schema Design
- vehicle_pings
  - id (INTEGER, PK)
  - route_id (TEXT)
  - vehicle_id (TEXT)
  - destination (TEXT)
  - latitude (REAL)
  - longitude (REAL)
  - heading (INTEGER)
  - delay_minutes (INTEGER)
  - ping_timestamp (INTEGER)
- quarantine_logs
  - id (INTEGER, PK)
  - raw_record (TEXT)
  - error_reason (TEXT)
  - dropped_at (INTEGER)

Prerequisites & Dependencies
- Python 3.10+
- Recommended runtime/package manager: uv
- Required packages: requests, pandas, streamlit, plotly, streamlit-autorefresh

How to Run
1. Clone repository & open folder: git clone https://github.com/AaronIGW/civic-telemetry-pipeline.git && cd civic-telemetry-pipeline
2. Start continuous ingestion daemon: uv run --with requests python scheduler.py (Polls live transit endpoints at set intervals, validates payloads, stages valid pings, and routes bad data to quarantine_logs)
3. Launch operations dashboard: uv run --with requests --with pandas --with streamlit --with plotly --with streamlit-autorefresh streamlit run app.py (Spins up the local Streamlit web application at http://localhost:8501 showing real-time fleet positions, KPI metrics, and headway alerts)
