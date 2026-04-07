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

load_latest_csv(BRIDGE_RESULTS_DIR, "bridge_eval_*.csv")
load_latest_csv(CYBORG_RESULTS_DIR, "cyborg_eval_*.csv")