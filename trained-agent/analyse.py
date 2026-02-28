import os
import re
import json
import csv
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path
from datetime import datetime
from collections import Counter
from typing import Optional

TMP_DIR    = Path(__file__).resolve().parent / "tmp"
OUTPUT_DIR = TMP_DIR / "analysis" / f"run_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"

RED_AGENTS = ["FiniteStateRedAgent", "RandomSelectRedAgent", "SleepRedAgent"]

COLORS = {
    "FiniteStateRedAgent":  "#da1919",
    "RandomSelectRedAgent": "#f39c12",
    "SleepRedAgent":        "#17aa07",
}
LABELS = {
    "FiniteStateRedAgent":  "FiniteState (Primary)",
    "RandomSelectRedAgent": "RandomSelect",
    "SleepRedAgent":        "Sleep (Baseline)",
}

BG_DARK  = "#0f0f1a"
BG_PANEL = "#1a1a2e"
GRID_COL = "#2a2a3e"
TEXT_COL = "#ccccdd"
AXIS_COL = "#444455"


# ─────────────────────────────────────────────
#  SHARED HELPERS
# ─────────────────────────────────────────────

def style_ax(ax):
    ax.set_facecolor(BG_PANEL)
    ax.tick_params(colors=TEXT_COL, labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor(AXIS_COL)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color=GRID_COL, linewidth=0.5, alpha=0.6)
    ax.xaxis.label.set_color(TEXT_COL)
    ax.yaxis.label.set_color(TEXT_COL)


def styled_fig(nrows, ncols, figsize):
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
    fig.patch.set_facecolor(BG_DARK)
    return fig, axes


def fig_title(fig, text, y=1.01):
    fig.suptitle(text, color="white", fontsize=13, fontweight="bold", y=y)


def save(fig, path: Path, name: str):
    path.mkdir(parents=True, exist_ok=True)
    out = path / name
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG_DARK)
    plt.close(fig)
    print(f"  Saved → {out}")


def find_latest_run(agent_name: str) -> Optional[Path]:
    agent_dir = TMP_DIR / agent_name
    if not agent_dir.exists():
        return None
    runs = [d for d in agent_dir.iterdir() if d.is_dir()]
    return max(runs, key=lambda d: d.name) if runs else None


# ─────────────────────────────────────────────
#  DATA LOADING
# ─────────────────────────────────────────────

def load_results():
    summaries, episode_dfs, action_counters = {}, {}, {}

    for agent in RED_AGENTS:
        run_path = find_latest_run(agent)
        if run_path is None:
            print(f"  [SKIP] No runs found for {agent}")
            continue

        # summary.json
        json_path = run_path / "summary.json"
        if json_path.exists():
            with open(json_path) as f:
                d = json.load(f)
            summaries[agent] = {
                "mean":           d["reward"]["mean"],
                "stdev":          d["reward"]["stdev"],
                "episodes":       d["parameters"]["max_episodes"],
                "episode_length": d["parameters"]["episode_length"],
                "elapsed_time":   d["time"]["elapsed"],
                "run_folder":     run_path.name,
            }
            print(f"  Loaded {agent}: mean={d['reward']['mean']:.2f}, stdev={d['reward']['stdev']:.2f}")

        # episode_rewards.csv
        rewards_path = run_path / "episode_rewards.csv"
        if rewards_path.exists():
            episode_dfs[agent] = pd.read_csv(rewards_path)
        else:
            print(f"  No episode_rewards.csv for {agent} — per-episode graphs will be skipped.")

        # actions.txt — parse action-type frequencies
        actions_path = run_path / "actions.txt"
        if actions_path.exists():
            content = actions_path.read_text(errors="replace")
            action_counters[agent] = Counter(re.findall(r"\[(\w+)", content))

    return summaries, episode_dfs, action_counters


def calculate_metrics(df: pd.DataFrame) -> dict:
    r = df["reward"]
    return {
        "mean":      r.mean(),
        "std":       r.std(),
        "median":    r.median(),
        "min":       r.min(),
        "max":       r.max(),
        "episodes":  len(r),
        "iqr":       r.quantile(0.75) - r.quantile(0.25),
        "cv":        r.std() / abs(r.mean()) * 100,
        "below_300": int((r < -300).sum()),
        "below_500": int((r < -500).sum()),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  ORIGINAL GRAPHS
# ═══════════════════════════════════════════════════════════════════════════

def plot_metrics(metrics: dict, out: Path):
    """Bar chart: Mean / Median / Max / Min per agent."""
    labels = ["Mean", "Median", "Max", "Min"]
    agents = list(metrics.keys())
    data   = {n: [metrics[n]["mean"], metrics[n]["median"],
                  metrics[n]["max"],  metrics[n]["min"]] for n in agents}
    x = np.arange(len(labels))
    w = 0.18

    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor("white")
    for i, name in enumerate(agents):
        ax.bar(x + (i - len(agents)/2)*w + w/2, data[name],
               width=w, label=LABELS.get(name, name),
               color=COLORS.get(name), alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("Value", fontsize=11)
    ax.set_title("FrozenLake — Algorithm Performance Metrics", fontsize=13, weight="bold")
    ax.legend(frameon=False, fontsize=9, ncol=2)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    save(fig, out, "metrics.png")


def plot_cumulative(dfs: dict, out: Path):
    """Cumulative reward over episodes."""
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("white")
    for name, df in dfs.items():
        ax.plot(np.cumsum(df["reward"]), label=LABELS.get(name, name),
                color=COLORS.get(name), linewidth=1.8)
    ax.set_title("Cumulative Rewards Over Episodes— CC4")
    ax.set_xlabel("Episode")
    ax.set_ylabel("Cumulative Reward")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    save(fig, out, "cumulative.png")


def plot_overlay_with_mean(dfs: dict, out: Path, window: int = 20):
    """Smoothed learning curves."""
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("white")
    for name, df in dfs.items():
        smooth = df["reward"].rolling(window, min_periods=1).mean()
        ax.plot(smooth, label=f"{LABELS.get(name, name)} (MA-{window})",
                color=COLORS.get(name), linewidth=2, alpha=0.8)
        ax.axhline(df["reward"].mean(), color=COLORS.get(name),
                   linestyle="--", alpha=0.5, linewidth=1)
    ax.set_title(f"Smoothed Learning Curves (MA-{window}) — CC4", fontsize=13, pad=10)
    ax.set_xlabel("Episode", fontsize=11)
    ax.set_ylabel("Average Reward", fontsize=11)
    ax.legend(frameon=False, fontsize=9)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    save(fig, out, "smoothed_learning.png")


# ═══════════════════════════════════════════════════════════════════════════
#  NEW GRAPHS
# ═══════════════════════════════════════════════════════════════════════════

def plot_per_episode_detail(dfs: dict, out: Path):
    """Per-episode scatter + rolling MA + trend line + worst-episode marker."""
    agents = list(dfs.keys())
    fig, axes = styled_fig(1, len(agents), (16, 5))
    if len(agents) == 1:
        axes = [axes]

    for ax, agent in zip(axes, agents):
        rewards = dfs[agent]["reward"].values
        eps     = np.arange(len(rewards))
        col     = COLORS[agent]

        ax.scatter(eps, rewards, alpha=0.35, s=18, color=col)
        roll = pd.Series(rewards).rolling(10, center=True).mean()
        ax.plot(eps, roll, color="white", linewidth=2, label="MA-10")
        z = np.polyfit(eps, rewards, 1)
        ax.plot(eps, np.poly1d(z)(eps), "--", color=col, alpha=0.7,
                linewidth=1.5, label="Trend")
        ax.axhline(rewards.mean(), color="cyan", linewidth=1, linestyle=":",
                   alpha=0.8, label=f"Mean: {rewards.mean():.1f}")
        worst = np.argmin(rewards)
        ax.scatter([worst], [rewards[worst]], color="red", s=100,
                   zorder=5, marker="v", label=f"Worst: {rewards[worst]}")

        style_ax(ax)
        ax.set_title(LABELS[agent], color="white", fontsize=10, fontweight="bold")
        ax.set_xlabel("Episode")
        ax.set_ylabel("Episode Reward")
        ax.legend(fontsize=7, facecolor=BG_PANEL, labelcolor="white", framealpha=0.7)

    fig_title(fig, "Per-Episode Reward Detail — CC4 Blue Agent Evaluation")
    fig.tight_layout()
    save(fig, out, "per_episode_detail.png")


def plot_action_distribution(action_counters: dict, out: Path):
    """Heatmap + stacked bar of blue-agent action-type frequencies."""
    if not action_counters:
        print("  [SKIP] No action data found — skipping action distribution plot.")
        return

    action_types = ["Sleep", "AllowTrafficZone", "BlockTrafficZone",
                    "Monitor", "Analyse", "Remove", "Restore", "DeployDecoy"]
    agent_keys   = [a for a in RED_AGENTS if a in action_counters]
    agent_labels = [LABELS[a] for a in agent_keys]

    matrix = np.array([
        [action_counters[a].get(t, 0) / max(sum(action_counters[a].values()), 1) * 100
         for t in action_types]
        for a in agent_keys
    ])

    fig, (ax1, ax2) = styled_fig(1, 2, (16, 5))

    # Heatmap
    im = ax1.imshow(matrix, cmap="YlOrRd", aspect="auto", vmin=0, vmax=matrix.max())
    ax1.set_xticks(range(len(action_types)))
    ax1.set_xticklabels(action_types, rotation=35, ha="right", color="white", fontsize=8)
    ax1.set_yticks(range(len(agent_labels)))
    ax1.set_yticklabels(agent_labels, color="white", fontsize=9)
    ax1.set_title("Action Distribution Heatmap (% of total)", color="white",
                  fontsize=10, fontweight="bold")
    for i in range(len(agent_labels)):
        for j in range(len(action_types)):
            ax1.text(j, i, f"{matrix[i,j]:.1f}%", ha="center", va="center",
                     fontsize=7, color="white" if matrix[i,j] > matrix.max()*0.4 else "black")
    cbar = plt.colorbar(im, ax=ax1)
    cbar.ax.tick_params(colors="white")

    # Stacked bar
    bar_colors = ["#2c3e50","#3498db","#e74c3c","#2ecc71","#f39c12","#9b59b6","#1abc9c","#e67e22"]
    x       = np.arange(len(agent_labels))
    bottoms = np.zeros(len(agent_labels))
    for i, (action, color) in enumerate(zip(action_types, bar_colors)):
        vals = matrix[:, i]
        ax2.bar(x, vals, bottom=bottoms, label=action, color=color,
                width=0.5, edgecolor=BG_DARK, linewidth=0.5)
        for j, (v, b) in enumerate(zip(vals, bottoms)):
            if v > 3:
                ax2.text(j, b + v/2, f"{v:.0f}%", ha="center", va="center",
                         fontsize=7, color="white", fontweight="bold")
        bottoms += vals
    ax2.set_xticks(x)
    ax2.set_xticklabels(agent_labels, color="white", fontsize=9)
    ax2.set_ylabel("% of Actions")
    ax2.set_title("Stacked Action Frequency by Scenario", color="white",
                  fontsize=10, fontweight="bold")
    ax2.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=8,
               facecolor=BG_PANEL, labelcolor="white", framealpha=0.8)
    for ax in (ax1, ax2):
        style_ax(ax)

    fig_title(fig, "Blue Agent Action Analysis — What is the Agent Actually Doing?")
    fig.tight_layout()
    save(fig, out, "action_distribution.png")


def plot_stats_table_and_boxplot(dfs: dict, metrics: dict, out: Path):
    """Box plot + comprehensive stats table side by side."""
    fig, (ax1, ax2) = styled_fig(1, 2, (16, 6))
    agents_present = [a for a in RED_AGENTS if a in dfs]

    # Box plot
    arrays = [dfs[a]["reward"].values for a in agents_present]
    bp = ax1.boxplot(
        arrays,
        labels=[LABELS[a].replace(" (", "\n(") for a in agents_present],
        patch_artist=True,
        notch=False,
        widths=0.5,
    )
    for patch, agent in zip(bp["boxes"], agents_present):
        patch.set_facecolor(COLORS[agent])
        patch.set_alpha(0.7)
    for med in bp["medians"]:
        med.set_color("white")
        med.set_linewidth(2)
    for flier in bp["fliers"]:
        flier.set(marker="o", markerfacecolor="red", alpha=0.5, markersize=5)
    for w in bp["whiskers"]:
        w.set(color=TEXT_COL, linewidth=1.5)
    for c in bp["caps"]:
        c.set(color=TEXT_COL, linewidth=1.5)

    style_ax(ax1)
    ax1.set_title("Reward Distribution Box Plot", color="white", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Episode Reward")
    ax1.tick_params(axis="x", colors="white")
    for i, agent in enumerate(agents_present, 1):
        m = metrics[agent]
        ax1.text(i, m["max"] + 3, f"IQR: {m['iqr']:.0f}",
                 ha="center", fontsize=7, color=COLORS[agent])

    # Stats table
    ax2.set_facecolor(BG_PANEL)
    ax2.axis("off")

    row_labels = ["Mean", "Std Dev", "Median", "Min", "Max",
                  "IQR", "CV (%)", "n < -300", "n < -500"]
    col_labels = ["Metric"] + [LABELS[a] for a in agents_present]
    row_keys = [
        ("mean",      "{:.1f}"),
        ("std",       "{:.1f}"),
        ("median",    "{:.1f}"),
        ("min",       "{}"),
        ("max",       "{}"),
        ("iqr",       "{:.1f}"),
        ("cv",        "{:.1f}%"),
        ("below_300", "{}"),
        ("below_500", "{}"),
    ]
    cell_data = []
    for (key, fmt), label in zip(row_keys, row_labels):
        row = [label]
        for a in agents_present:
            row.append(fmt.format(metrics[a][key]))
        cell_data.append(row)

    tbl = ax2.table(cellText=cell_data, colLabels=col_labels,
                    cellLoc="center", loc="center", bbox=[0, 0, 1, 1])
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8.5)

    hdr_bg           = ["#16213e", "#1b5e20", "#7f0000", "#e65100"]
    cell_shades      = ["#1a1a2e", "#1b2e1b", "#2e1b1b", "#2e2010"]
    agent_txt_colors = [TEXT_COL, "#2ecc71", "#e74c3c", "#f39c12"]

    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor("#333")
        cell.set_linewidth(0.5)
        if r == 0:
            cell.set_facecolor(hdr_bg[c] if c < len(hdr_bg) else "#16213e")
            cell.set_text_props(color="white", fontweight="bold")
        else:
            cell.set_facecolor(cell_shades[c] if c < len(cell_shades) else "#1a1a2e")
            cell.set_text_props(
                color=agent_txt_colors[c] if c < len(agent_txt_colors) else TEXT_COL
            )

    ax2.set_title("Comprehensive Statistical Summary", color="white",
                  fontsize=11, fontweight="bold", pad=15)

    fig_title(fig, "Statistical Analysis — CybOrg Cage 4 Blue Agent vs Red Agent Types")
    fig.tight_layout()
    save(fig, out, "stats_table_boxplot.png")


def plot_failure_analysis(dfs: dict, out: Path):
    """Histogram with catastrophic zone + cumulative % above threshold."""
    fig, (ax1, ax2) = styled_fig(1, 2, (16, 5))
    agents_present = [a for a in RED_AGENTS if a in dfs]
    bins = np.linspace(-650, 50, 30)

    for agent in agents_present:
        ax1.hist(dfs[agent]["reward"].values, bins=bins, alpha=0.55,
                 color=COLORS[agent], label=LABELS[agent],
                 edgecolor="black", linewidth=0.4)
    ax1.axvline(-300, color="white", linewidth=1.5, linestyle="--",
                alpha=0.7, label="–300 threshold")
    ax1.axvline(-500, color="red", linewidth=1.5, linestyle="--",
                alpha=0.9, label="Catastrophic –500")
    ax1.axvspan(-650, -500, alpha=0.12, color="red")
    ax1.figure.canvas.draw()
    ylim_top = ax1.get_ylim()[1]
    ax1.text(-575, ylim_top * 0.80, "Catastrophic\nZone",
             ha="center", color="red", fontsize=8, alpha=0.9)

    style_ax(ax1)
    ax1.set_title("Episode Reward Histogram", color="white", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Episode Reward")
    ax1.set_ylabel("Frequency")
    ax1.legend(facecolor=BG_PANEL, labelcolor="white", fontsize=8)

    thresholds = np.arange(-650, 10, 10)
    for agent in agents_present:
        rewards = dfs[agent]["reward"].values
        pct = [(rewards >= t).mean() * 100 for t in thresholds]
        ax2.plot(thresholds, pct, color=COLORS[agent], linewidth=2, label=LABELS[agent])
    ax2.axvline(-300, color="white", linewidth=1, linestyle="--", alpha=0.5)
    ax2.axvline(-500, color="red",   linewidth=1, linestyle="--", alpha=0.7)
    ax2.text(-300, 7, " –300", color="white", fontsize=8)
    ax2.text(-500, 7, " –500", color="red",   fontsize=8)
    ax2.set_ylim(0, 105)

    style_ax(ax2)
    ax2.set_title("Cumulative % of Episodes Above Reward Threshold",
                  color="white", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Reward Threshold")
    ax2.set_ylabel("% of Episodes Above Threshold")
    ax2.legend(facecolor=BG_PANEL, labelcolor="white", fontsize=8)

    fig_title(fig, "Failure Mode Analysis — Catastrophic Episode Investigation")
    fig.tight_layout()
    save(fig, out, "failure_analysis.png")


def plot_learning_stability(dfs: dict, out: Path):
    """Rolling volatility + first-half vs second-half mean comparison."""
    fig, (ax1, ax2) = styled_fig(1, 2, (16, 5))
    agents_present = [a for a in RED_AGENTS if a in dfs]
    window = 10

    for agent in agents_present:
        roll_std = dfs[agent]["reward"].rolling(window).std()
        ax1.plot(roll_std, color=COLORS[agent], linewidth=2,
                 label=LABELS[agent], alpha=0.9)
    style_ax(ax1)
    ax1.set_title(f"Rolling Volatility (Std Dev, window={window})",
                  color="white", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Episode")
    ax1.set_ylabel("Rolling Std Dev")
    ax1.legend(facecolor=BG_PANEL, labelcolor="white")

    x = np.arange(len(agents_present))
    w = 0.3
    first_means, second_means = [], []
    for agent in agents_present:
        r   = dfs[agent]["reward"].values
        mid = len(r) // 2
        first_means.append(r[:mid].mean())
        second_means.append(r[mid:].mean())

    def make_darker(hex_col: str, factor: float = 0.5) -> str:
        hex_col = hex_col.lstrip("#")
        rgb = tuple(int(hex_col[i:i+2], 16) for i in (0, 2, 4))
        return "#{:02x}{:02x}{:02x}".format(*[int(c * factor) for c in rgb])

    dark_colors = [make_darker(COLORS[a]) for a in agents_present]
    b1 = ax2.bar(x - w/2, first_means,  w, label="First Half (Eps 0–24)",
                 color=dark_colors, edgecolor=BG_DARK)
    b2 = ax2.bar(x + w/2, second_means, w, label="Second Half (Eps 25–49)",
                 color=[COLORS[a] for a in agents_present], edgecolor=BG_DARK)

    for bar in list(b1) + list(b2):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() - 4,
                 f"{bar.get_height():.0f}", ha="center", va="top",
                 color="white", fontsize=8)
    for i, (f, s, agent) in enumerate(zip(first_means, second_means, agents_present)):
        diff  = s - f
        arrow = "↑" if diff > 0 else "↓"
        ax2.text(i, max(f, s) + 5, f"{arrow}{abs(diff):.0f}",
                 ha="center", color=COLORS[agent], fontsize=10, fontweight="bold")

    style_ax(ax2)
    ax2.set_xticks(x)
    ax2.set_xticklabels([LABELS[a] for a in agents_present], color="white", fontsize=8)
    ax2.set_title("First Half vs Second Half Performance\n(Evidence of Learning)",
                  color="white", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Mean Episode Reward")
    ax2.legend(facecolor=BG_PANEL, labelcolor="white", fontsize=9)

    fig_title(fig, "Learning Stability & Temporal Performance Analysis")
    fig.tight_layout()
    save(fig, out, "learning_stability.png")


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  CybORG Cage 4 — Blue Agent Analysis")
    print(f"{'='*60}\n")

    print("Loading results from tmp/ ...\n")
    summaries, episode_dfs, action_counters = load_results()

    if not summaries:
        print("No results found. Run evaluations first (evaluation.py).")
        exit(1)

    graphs_dir = OUTPUT_DIR / "graphs"
    graphs_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {OUTPUT_DIR}\n")

    metrics = {a: calculate_metrics(df) for a, df in episode_dfs.items()}

    print("\n── Original graphs ──────────────────────────────────")
    plot_metrics(metrics, graphs_dir)
    plot_cumulative(episode_dfs, graphs_dir)
    plot_overlay_with_mean(episode_dfs, graphs_dir, window=20)

    print("\n── New analysis graphs ──────────────────────────────")
    plot_per_episode_detail(episode_dfs, graphs_dir)
    plot_action_distribution(action_counters, graphs_dir)
    plot_stats_table_and_boxplot(episode_dfs, metrics, graphs_dir)
    plot_failure_analysis(episode_dfs, graphs_dir)
    plot_learning_stability(episode_dfs, graphs_dir)

    print(f"\n{'='*60}")
    print(f"  All graphs saved to:")
    print(f"  {graphs_dir}")
    print(f"{'='*60}\n")