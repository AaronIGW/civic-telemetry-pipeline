import time
from ingest import run_ingestion_cycle

POLL_INTERVAL_SECONDS = 30  

print(
    f"[*] Starting Civic Telemetry Ingestion Daemon (Interval:"
    f" {POLL_INTERVAL_SECONDS}s)"
)
print("[*] Press Ctrl+C to stop.\n")

try:
  while True:
    run_ingestion_cycle()
    time.sleep(POLL_INTERVAL_SECONDS)
except KeyboardInterrupt:
  print("\n[*] Ingestion daemon stopped gracefully.")