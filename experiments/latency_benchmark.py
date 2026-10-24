import requests
import time
import csv
import statistics

AGENT_URL = "http://127.0.0.1:8003/analyze"

EVENT = {
    "event_type": "BEHAVIORAL_ANOMALY",
    "client_ip": "127.0.0.1",
    "path": "/services",
    "reason": "HIGH_REQUEST_FREQUENCY"
}

results = []

print("Starting deterministic Agent latency benchmark...")
print("Trials: 30\n")

for i in range(30):
    start = time.perf_counter()

    response = requests.post(
        AGENT_URL,
        json=EVENT,
        timeout=10
    )

    end = time.perf_counter()

    latency = end - start
    results.append(latency)

    print(
        f"Trial {i + 1:02d}: "
        f"{latency:.4f} s | "
        f"HTTP {response.status_code}"
    )

median = statistics.median(results)

sorted_results = sorted(results)
p95_index = int(0.95 * len(sorted_results)) - 1
p95 = sorted_results[p95_index]

print("\n--- Deterministic Agent Results ---")
print(f"Median: {median:.4f} s")
print(f"P95:    {p95:.4f} s")

with open("experiments/deterministic_latency.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["trial", "latency_seconds"])

    for i, latency in enumerate(results, start=1):
        writer.writerow([i, latency])