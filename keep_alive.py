import requests
import sys

URL = "https://cummand.onrender.com/health"

try:
    response = requests.get(URL, timeout=10)
    data = response.json()
    if data.get("status") == "ok":
        print(f"Server alive — v{data['version']}, {data['tunnels']} tunnel(s)")
    else:
        print(f"Unexpected response: {data}")
        sys.exit(1)
except Exception as e:
    print(f"Could not ping server: {e}")
    sys.exit(1)
