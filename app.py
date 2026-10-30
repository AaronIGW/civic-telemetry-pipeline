import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from analytics import detect_bus_bunching

st.set_page_config(
    page_title="Philly Civic Telemetry",
    page_icon="🚌",
    layout="wide"
)

# Sidebar controls for real-time polling
st.sidebar.header("⚙️ Telemetry Stream Controls")
auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh", value=True)
refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", min_value=10, max_value=60, value=30, step=5)

if auto_refresh:
    st_autorefresh(interval=refresh_interval * 1000, key="telemetry_counter")

st.title("🚌 Live Transit & Civic Telemetry Engine")
st.caption("Automated ingestion pipeline consuming live streaming transit telemetry with schema validation & dead-letter quarantine.")

DB_PATH = "telemetry.db"

def load_data():
    with sqlite3.connect(DB_PATH) as conn:
        pings_df = pd.read_sql_query("""
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
            SELECT * FROM ranked_pings WHERE rn = 1;
        """, conn)
        
        health_df = pd.read_sql_query("""
            SELECT 
                (SELECT COUNT(*) FROM vehicle_pings) AS valid_pings,
                (SELECT COUNT(*) FROM quarantine_logs) AS quarantined_records;
        """, conn)
    return pings_df, health_df

pings_df, health_df = load_data()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Active Tracked Fleet", len(pings_df))
col2.metric("Total Pings Ingested", int(health_df["valid_pings"].iloc[0]))
col3.metric("Quarantine Drops", int(health_df["quarantined_records"].iloc[0]), delta_color="inverse")
avg_delay = pings_df["delay_minutes"].mean() if not pings_df.empty else 0
col4.metric("Fleet Avg Delay", f"{avg_delay:.1f} min", delta=f"{avg_delay:.1f}m late")

st.divider()

st.subheader("🚨 Dispatch Operations & Headway Alerts")
bunching_df = detect_bus_bunching(max_gap_miles=0.45)

if not bunching_df.empty:
    for _, row in bunching_df.iterrows():
        alert_func = st.error if row.get("severity") == "CRITICAL" else st.warning
        alert_func(
            f"**Route {row['route_id']} ({row['destination']}) — {row.get('severity', 'INCIDENT')}:**\n\n"
            f"Vehicles **#{row['lead_vehicle']}** and **#{row['trailing_vehicle']}** are clustered "
            f"only **{row['distance_miles']} miles** apart. (Delays: {row['lead_delay']}m vs {row['trail_delay']}m)\n\n"
            f"👉 **Dispatch Recommendation:** {row.get('dispatch_action', 'Monitor headway progression.')}"
        )
    st.dataframe(bunching_df, use_container_width=True)
else:
    st.success("✅ Nominal Headways: No active vehicle bunching detected across monitored routes.")

st.divider()

st.subheader("📍 Live Fleet Locations & Delays")
if not pings_df.empty:
    center_lat = pings_df["latitude"].mean()
    center_lon = pings_df["longitude"].mean()
    
    fig = px.scatter_map(
        pings_df,
        lat="latitude",
        lon="longitude",
        hover_name="vehicle_id",
        hover_data={
            "route_id": True,
            "destination": True,
            "delay_minutes": True,
            "latitude": False,
            "longitude": False
        },
        color="delay_minutes",
        color_continuous_scale="Reds",
        map_style="carto-positron"
    )
    
    fig.update_traces(marker=dict(size=14))
    fig.update_layout(
        map=dict(
            center=dict(lat=center_lat, lon=center_lon),
            zoom=11.5
        ),
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )
    st.plotly_chart(fig, use_container_width=True)

st.subheader("📊 Delay Distribution & Recent Pings")
st.dataframe(
    pings_df[["route_id", "vehicle_id", "destination", "delay_minutes", "ping_time"]],
    use_container_width=True
)