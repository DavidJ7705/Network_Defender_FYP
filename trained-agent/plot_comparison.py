"""
Poster-quality plot comparing Bridge vs CybORG action distributions.
Reads the latest CSVs from bridge/results/ and trained-agent/results/.

Run from trained-agent/:
    python plot_comparison.py
"""

import csv
import glob
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────────────
BRIDGE_RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bridge", "results")
CYBORG_RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")

ACTION_TYPES = ["Analyse", "Block", "Restore", "DeployDecoy", "Monitor"]


def load_latest_csv(directory, pattern):
    csvs = sorted(glob.glob(os.path.join(directory, pattern)))
    if not csvs:
        print(f"No CSV found matching {pattern} in {directory}")
        sys.exit(1)
    latest = csvs[-1]
    print(f"Loaded: {latest}")
    counts = {t: 0 for t in ACTION_TYPES}
    with open(latest, newline="") as f:
        for row in csv.DictReader(f):
            action_type = row["blue_action_type"]
            if action_type in counts:
                counts[action_type] += 1
            else:
                counts["Monitor"] += 1
    masked = "_masked" in os.path.basename(latest)
    return counts, masked


def to_pct(counts):
    total = sum(counts.values())
    return {k: 100 * v / total for k, v in counts.items()} if total else counts


def plot_bar_cards(b_pct, c_pct, out_path, masked=False):
    action_colors = {
        "Analyse":     "#4C9BE8",
        "Block":       "#F4845F",
        "Restore":     "#52C48A",
        "DeployDecoy": "#A87FE8",
        "Monitor":     "#B0B8C8",
    }
    TRACK_CLR = "#EAECF3"
    BAR_H     = 0.17
    BAR_GAP   = 0.28
    GROUP_GAP = 0.82
    XLIM      = 100.0

    sorted_actions = sorted(ACTION_TYPES, key=lambda a: b_pct[a], reverse=True)
    n = len(sorted_actions)

    fig, ax = plt.subplots(figsize=(7.5, n * GROUP_GAP + 0.9))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])

    def pill(x_start, y_center, width, height, color, alpha=1.0, zorder=3):
        r = height / 2
        patch = FancyBboxPatch(
            (x_start + r, y_center - r),
            max(width - 2 * r, 1e-4), 0,
            boxstyle=f"round,pad={r}",
            facecolor=color, edgecolor="none",
            alpha=alpha, zorder=zorder,
        )
        ax.add_patch(patch)

    for i, action in enumerate(sorted_actions):
        y_center = (n - 1 - i) * GROUP_GAP
        y_b = y_center + BAR_GAP / 2
        y_c = y_center - BAR_GAP / 2
        color = action_colors[action]

        pill(0, y_b, XLIM, BAR_H, TRACK_CLR, zorder=2)
        pill(0, y_c, XLIM, BAR_H, TRACK_CLR, zorder=2)
        pill(0, y_b, b_pct[action], BAR_H, color, alpha=1.0,  zorder=3)
        pill(0, y_c, c_pct[action], BAR_H, color, alpha=0.42, zorder=3)

        ax.text(-2, y_center, action, va="center", ha="right",
                fontsize=10.5, color="#2C3A4B", fontweight="700")
        ax.text(XLIM + 2, y_b, f"{b_pct[action]:.0f}%", va="center", ha="left",
                fontsize=9.5, color=color, fontweight="700")
        ax.text(XLIM + 2, y_c, f"{c_pct[action]:.0f}%", va="center", ha="left",
                fontsize=9.5, color=color, alpha=0.55, fontweight="600")

    bridge_label = "Bridge  ·  Live Network  ·  Action Masked" if masked else "Bridge  ·  Live Network  ·  Baseline"
    lx, ly = 0, -GROUP_GAP * 0.52
    pill(lx, ly, 7, BAR_H, "#888", alpha=1.0,  zorder=4)
    ax.text(lx + 9, ly, bridge_label, va="center",
            fontsize=9, color="#2C3A4B", fontweight="600")
    pill(lx + 55, ly, 7, BAR_H, "#888", alpha=0.42, zorder=4)
    ax.text(lx + 64, ly, "CybORG  ·  Simulation", va="center",
            fontsize=9, color="#2C3A4B")

    ax.set_xlim(-22, 120)
    ax.set_ylim(-GROUP_GAP * 0.85, (n - 1) * GROUP_GAP + GROUP_GAP * 0.6)

    fig.tight_layout(pad=0.6)
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)

    b_counts, masked = load_latest_csv(BRIDGE_RESULTS_DIR, "bridge_eval_*.csv")
    c_counts, _      = load_latest_csv(CYBORG_RESULTS_DIR, "cyborg_eval_*.csv")
    b_pct = to_pct(b_counts)
    c_pct = to_pct(c_counts)

    suffix = "_masked" if masked else "_baseline"
    plot_bar_cards(b_pct, c_pct, os.path.join(OUT_DIR, f"plot_bar_cards{suffix}.png"), masked=masked)

    print("\nDone. PNGs saved to trained-agent/results/")
