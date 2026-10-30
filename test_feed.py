import requests

url = "https://www3.septa.org/api/TransitView/index.php?route=21"

try:
  response = requests.get(url, timeout=10)
  response.raise_for_status()
  data = response.json()
  print("Status:", response.status_code)
  print("Keys returned:", data.keys())
  if "bus" in data:
    print(f"Active vehicles found: {len(data['bus'])}")
    if data["bus"]:
      print("Sample Vehicle Record:", data["bus"][0])
except Exception as e:
  print("Error fetching live feed:", e)