import requests
import time

BASE_URL = "http://localhost:8000"

def test_route():
    payload = {
        "start_lat": 34.191,
        "start_lng": -118.131,
        "end_lat": 34.196,
        "end_lng": -118.126,
        "unit_id": "test-unit-1"
    }

    print("\n🚀 Sending route request...")
    start_time = time.time()

    res = requests.post(f"{BASE_URL}/route", json=payload)

    latency = time.time() - start_time

    print(f"Status Code: {res.status_code}")
    print(f"Latency: {latency:.3f}s")

    if res.status_code != 200:
        print("❌ FAILED:", res.text)
        return

    data = res.json()

    print("\n✅ Response:")
    print(data)

    # --- Assertions ---
    assert "path" in data, "Missing path"
    assert "cost" in data, "Missing cost"
    assert "rerouted" in data, "Missing rerouted"
    assert "route_id" in data, "Missing route_id"

    assert isinstance(data["path"], list), "Path not list"
    assert len(data["path"]) > 0, "Empty path"

    print("\n🎯 Basic validation passed!")

if __name__ == "__main__":
    test_route()