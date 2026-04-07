import csv
import glob
import os
import sys

BRIDGE_RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bridge", "results")
CYBORG_RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
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
    return counts

def print_comparison(bridge_counts, cyborg_counts):
    bridge_total = sum(bridge_counts.values())
    cyborg_total = sum(cyborg_counts.values())

    print("\n" + "=" * 70)
    print(f"{'Metric':<22} {'Bridge (real network)':>22} {'CybORG (simulation)':>22}")
    print("=" * 70)
    for action_type in ACTION_TYPES:
        b_pct = 100 * bridge_counts.get(action_type, 0) / bridge_total if bridge_total else 0
        c_pct = 100 * cyborg_counts.get(action_type, 0) / cyborg_total if cyborg_total else 0
        print(f"{action_type + ' %':<22}{b_pct:>18.1f} %     {c_pct:>14.1f} %")
    print("=" * 70)
    print(f"{'Total steps':<18} {bridge_total:>20} {cyborg_total:>22}")
    print("=" * 70 + "\n")
    

if __name__ == "__main__":
    bridge_counts = load_latest_csv(BRIDGE_RESULTS_DIR, "bridge_eval_*.csv")
    cyborg_counts = load_latest_csv(CYBORG_RESULTS_DIR, "cyborg_eval_*.csv")
    print_comparison(bridge_counts, cyborg_counts)