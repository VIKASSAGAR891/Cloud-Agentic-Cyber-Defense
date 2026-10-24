import requests
import time
import csv
import statistics

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:7b"

payload = {
    "model": MODEL,
    "messages": [
        {
            "role": "system",
            "content": (
                "You are a cybersecurity analysis assistant. "
                "Analyze the supplied security event and return concise "
                "structured reasoning."
            )
        },
        {
            "role": "user",
            "content": (
                "Analyze this security event: "
                "event_type=BEHAVIORAL_ANOMALY, "
                "client_ip=127.0.0.1, "
                "path=/services, "
                "reason=HIGH_REQUEST_FREQUENCY. "
                "Provide a concise JSON response containing assessment, "
                "severity_context, reasoning, and recommended_observations."
            )
        }
    ],
    "stream": False,
    "format": "json",
    "options": {
        "temperature": 0.2,
        "num_predict": 512
    }
}

results = []

print("Starting Qwen2.5:7B latency benchmark...")
print("Trials: 30\n")

for i in range(30):

    start = time.perf_counter()

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=180
    )

    end = time.perf_counter()

    latency = end - start

    response.raise_for_status()

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

print("\n--- Qwen2.5:7B Results ---")
print(f"Median: {median:.4f} s")
print(f"P95:    {p95:.4f} s")

with open("experiments/qwen_latency.csv", "w", newline="") as f:
    writer = csv.writer(f)

    writer.writerow(["trial", "latency_seconds"])

    for i, latency in enumerate(results, start=1):
        writer.writerow([i, latency])