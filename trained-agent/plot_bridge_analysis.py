"""
Analysis plots for Bridge evaluation CSV.
Run from trained-agent/:
    python plot_bridge_analysis.py
"""

import csv
import glob
import os
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BRIDGE_RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bridge", "results")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def load_latest_csv(directory, pattern):
    csvs = sorted(glob.glob(os.path.join(directory, pattern)))
    if not csvs:
        print(f"No CSV found matching {pattern} in {directory}")
        sys.exit(1)
    latest = csvs[-1]
    print(f"Loaded: {latest}")
    rows = []
    with open(latest, newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    masked = "_masked" in os.path.basename(latest)
    return rows, masked


def label(title, masked):
    suffix = " (action masked)" if masked else " (baseline)"
    return title + suffix


def plot_red_blue_timeline(rows, out_path, masked=False):
    steps = []
    red_success_rate = []
    blue_active_rate = []

    window = 5
    for i in range(len(rows)):
        start = max(0, i - window // 2)
        end = min(len(rows), i + window // 2 + 1)
        window_rows = rows[start:end]

        red_success = sum(1 for r in window_rows if r["red_success"].lower() == "true")
        blue_active = sum(1 for r in window_rows if r["blue_action_type"] not in ["Monitor", "AllowTraffic"])

        steps.append(i + 1)
        red_success_rate.append(100 * red_success / len(window_rows))
        blue_active_rate.append(100 * blue_active / len(window_rows))

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.fill_between(steps, 0, red_success_rate, alpha=0.6, color="#f85149", label="Red Success Rate")
    ax.fill_between(steps, 0, blue_active_rate, alpha=0.6, color="#3fb950", label="Blue Active Actions")

    ax.set_xlabel("Step", fontsize=11)
    ax.set_ylabel("% (rolling window)", fontsize=11)
    ax.set_title(label("Red Attack Success vs Blue Active Defense (rolling avg)", masked), fontsize=11, pad=10)
    ax.legend(frameon=False, fontsize=10, loc="upper right")
    ax.grid(True, color="#e0e0e0", alpha=0.5, zorder=0)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="both", length=0)

    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {out_path}")


def plot_compromise_timeline(rows, out_path, masked=False):
    steps = [int(r["step"]) for r in rows]
    compromises = [int(r["compromised_count"]) for r in rows]

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.plot(steps, compromises, color="#da3633", linewidth=2.5, marker="o", markersize=4, zorder=3)
    ax.fill_between(steps, 0, compromises, alpha=0.2, color="#da3633")

    ax.set_xlabel("Step", fontsize=11)
    ax.set_ylabel("Compromised Hosts", fontsize=11)
    ax.set_title(label("Network Compromise Timeline", masked), fontsize=11, pad=10)
    ax.grid(True, color="#e0e0e0", alpha=0.5, zorder=0)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="both", length=0)

    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {out_path}")


def plot_action_effectiveness(rows, out_path, masked=False):
    actions = defaultdict(list)

    for i in range(len(rows) - 1):
        curr_action = rows[i]["blue_action_type"]
        curr_compromises = int(rows[i]["compromised_count"])
        next_compromises = int(rows[i + 1]["compromised_count"])

        reduction = curr_compromises - next_compromises
        actions[curr_action].append(reduction)

    action_names = sorted(actions.keys())
    avg_reductions = [np.mean(actions[a]) for a in action_names]
    std_reductions = [np.std(actions[a]) for a in action_names]
    counts = [len(actions[a]) for a in action_names]

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    colors = ["#3fb950" if r > 0 else "#f85149" for r in avg_reductions]
    bars = ax.bar(action_names, avg_reductions, yerr=std_reductions, capsize=5,
                  color=colors, alpha=0.7, zorder=3, error_kw={"linewidth": 1.5})

    for i, (bar, count) in enumerate(zip(bars, counts)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height + 0.1,
                f"n={count}", ha="center", va="bottom", fontsize=8)

    ax.axhline(y=0, color="#484f58", linestyle="-", linewidth=0.8, zorder=0)
    ax.set_ylabel("Avg Compromise Reduction", fontsize=11)
    ax.set_title(label("Action Effectiveness (avg compromise count change)", masked), fontsize=11, pad=10)
    ax.set_xticklabels(action_names, rotation=45, ha="right", fontsize=9)
    ax.grid(True, color="#e0e0e0", alpha=0.5, axis="y", zorder=0)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="x", length=0)

    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    rows, masked = load_latest_csv(BRIDGE_RESULTS_DIR, "bridge_eval_*.csv")
    os.makedirs(OUT_DIR, exist_ok=True)

    suffix = "_masked" if masked else "_baseline"
    plot_red_blue_timeline(rows, os.path.join(OUT_DIR, f"plot_red_blue_timeline{suffix}.png"), masked=masked)
    plot_compromise_timeline(rows, os.path.join(OUT_DIR, f"plot_compromise_timeline{suffix}.png"), masked=masked)
    plot_action_effectiveness(rows, os.path.join(OUT_DIR, f"plot_action_effectiveness{suffix}.png"), masked=masked)

    print("\nDone. PNGs saved to trained-agent/results/")
