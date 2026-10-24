import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# Input files
# ---------------------------------------------------------
DET_FILE = "experiments/deterministic_latency.csv"
QWEN_FILE = "experiments/qwen_latency.csv"

# ---------------------------------------------------------
# Load data
# ---------------------------------------------------------
det_df = pd.read_csv(DET_FILE)
qwen_df = pd.read_csv(QWEN_FILE)

# Automatically find the latency column
def get_latency_column(df):
    possible = [
        "latency_seconds",
        "latency",
        "elapsed_seconds",
        "response_time",
        "time_seconds"
    ]

    for col in possible:
        if col in df.columns:
            return col

    # fallback: first numeric column
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) == 0:
        raise ValueError("No numeric latency column found.")

    return numeric_cols[0]


det_col = get_latency_column(det_df)
qwen_col = get_latency_column(qwen_df)

det = det_df[det_col].dropna().astype(float).to_numpy()
qwen = qwen_df[qwen_col].dropna().astype(float).to_numpy()

# ---------------------------------------------------------
# Statistics
# ---------------------------------------------------------
det_median = np.median(det)
det_p95 = np.percentile(det, 95, method="linear")

qwen_median = np.median(qwen)
qwen_p95 = np.percentile(qwen, 95, method="linear")

print("\n===== LATENCY RESULTS =====")

print(f"Deterministic Agent")
print(f"  Trials : {len(det)}")
print(f"  Median : {det_median:.4f} s")
print(f"  P95    : {det_p95:.4f} s")
print(f"  Min    : {np.min(det):.4f} s")
print(f"  Max    : {np.max(det):.4f} s")

print()

print(f"Qwen2.5:7B via Ollama")
print(f"  Trials : {len(qwen)}")
print(f"  Median : {qwen_median:.4f} s")
print(f"  P95    : {qwen_p95:.4f} s")
print(f"  Min    : {np.min(qwen):.4f} s")
print(f"  Max    : {np.max(qwen):.4f} s")

print()

print(
    f"Median latency ratio "
    f"(Qwen / Deterministic): "
    f"{qwen_median / det_median:.1f}x"
)

print(
    f"P95 latency ratio "
    f"(Qwen / Deterministic): "
    f"{qwen_p95 / det_p95:.1f}x"
)

# ---------------------------------------------------------
# Plot
# ---------------------------------------------------------
data = [det, qwen]

fig, ax = plt.subplots(figsize=(3.5, 2.8))

bp = ax.boxplot(
    data,
    positions=[1, 2],
    widths=0.45,
    patch_artist=True,
    showfliers=False,
    medianprops=dict(color="black", linewidth=1.5),
    boxprops=dict(edgecolor="black", linewidth=1.0),
    whiskerprops=dict(color="black", linewidth=1.0),
    capprops=dict(color="black", linewidth=1.0)
)

# White boxes for clean IEEE-style presentation
for box in bp["boxes"]:
    box.set_facecolor("white")

# ---------------------------------------------------------
# Plot individual observations
# ---------------------------------------------------------
rng = np.random.default_rng(42)

for x, values in zip([1, 2], data):
    jitter = rng.uniform(-0.08, 0.08, size=len(values))

    ax.scatter(
        np.full(len(values), x) + jitter,
        values,
        s=10,
        alpha=0.55,
        color="black",
        zorder=3
    )

# ---------------------------------------------------------
# Mark P95 values
# ---------------------------------------------------------
ax.scatter(
    [1, 2],
    [det_p95, qwen_p95],
    marker="^",
    s=45,
    color="black",
    zorder=5,
    label="P95"
)

# ---------------------------------------------------------
# Median annotations
# ---------------------------------------------------------
ax.annotate(
    f"Median\n{det_median:.4f} s",
    xy=(1, det_median),
    xytext=(1.18, det_median * 1.8),
    fontsize=7,
    ha="left",
    va="center",
    arrowprops=dict(
        arrowstyle="-",
        linewidth=0.8,
        color="black"
    )
)

ax.annotate(
    f"Median\n{qwen_median:.2f} s",
    xy=(2, qwen_median),
    xytext=(1.55, qwen_median / 1.7),
    fontsize=7,
    ha="left",
    va="center",
    arrowprops=dict(
        arrowstyle="-",
        linewidth=0.8,
        color="black"
    )
)

# ---------------------------------------------------------
# P95 labels
# ---------------------------------------------------------
ax.text(
    1,
    det_p95 * 1.25,
    f"P95 = {det_p95:.4f} s",
    ha="center",
    fontsize=6.8
)

ax.text(
    2,
    qwen_p95 * 1.08,
    f"P95 = {qwen_p95:.2f} s",
    ha="center",
    fontsize=6.8
)

# ---------------------------------------------------------
# Axis formatting
# ---------------------------------------------------------
ax.set_xticks([1, 2])
ax.set_xticklabels([
    "Deterministic\nAgent",
    "Qwen2.5:7B\n(Ollama)"
], fontsize=8)

ax.set_ylabel(
    "Latency (seconds)",
    fontsize=8
)

ax.set_yscale("log")

ax.tick_params(
    axis="both",
    labelsize=7
)

ax.grid(
    axis="y",
    linestyle="--",
    linewidth=0.5,
    alpha=0.35
)

ax.set_axisbelow(True)

# Remove unnecessary top/right borders
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

plt.tight_layout()

# ---------------------------------------------------------
# Save publication-quality outputs
# ---------------------------------------------------------
plt.savefig(
    "experiments/fig5_latency_comparison.png",
    dpi=600,
    bbox_inches="tight"
)

plt.savefig(
    "experiments/fig5_latency_comparison.pdf",
    bbox_inches="tight"
)

plt.show()

print("\nFigure saved:")
print("  experiments/fig5_latency_comparison.png")
print("  experiments/fig5_latency_comparison.pdf")