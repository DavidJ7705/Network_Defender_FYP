# Runs a full 100-step episode and logs every red/blue action to a CSV in bridge/results/.
#
# Terminal 1 (deploy topology):
#   cd ~/Desktop/Network_Defender_FYP/containerlab-networks
#   sudo containerlab deploy -t cage4-topology.yaml
#
# Terminal 2 (run — baseline):
#   cd ~/Desktop/Network_Defender_FYP/bridge
#   rm -rf __pycache__
#   sudo ~/fyp-venv-linux/bin/python evaluation.py
#   → bridge_eval_<timestamp>.csv
#
# Terminal 2 (run — with action masking):
#   sudo ~/fyp-venv-linux/bin/python evaluation.py --mask
#   → bridge_eval_<timestamp>_masked.csv
#
# Cleanup (when done):
#   sudo containerlab destroy -t cage4-topology.yaml

import argparse
import csv
import os
from datetime import datetime

from network_monitor import ContainerlabMonitor
from graph_builder import ObservationGraphBuilder
from agent_adapter import AgentAdapter
from action_executor import ActionExecutor
from red_agent import RedAgent
from intrusion_detector import IntrusionDetector

TOTAL_STEPS = 100
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def run_evaluation(mask_edge_actions=False):
    os.makedirs(LOG_DIR, exist_ok=True)
    run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    suffix = "_masked" if mask_edge_actions else ""
    csv_path = os.path.join(LOG_DIR, f"bridge_eval_{run_id}{suffix}.csv")

    monitor = ContainerlabMonitor()
    builder = ObservationGraphBuilder()
    adapter = AgentAdapter(mask_edge_actions=mask_edge_actions)
    executor = ActionExecutor()
    detector = IntrusionDetector()

    state = monitor.get_network_state()
    servers, users, routers = builder.classify_node_type(state)
    all_containers = servers + users

    executor.cleanup_stale_decoys()
    detector.cleanup_flags(all_containers)

    red_agent = RedAgent(all_containers, decoys=executor._decoys)

    rows = []
    FIELDS = ["step", "phase", "red_action", "red_host", "red_success",
              "blue_action_type", "blue_target", "blue_result",
              "compromised_count", "decoy_count"]

    print(f"Bridge System Evaluation — {TOTAL_STEPS} steps\n")

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()

        for step in range(TOTAL_STEPS):
            phase = min(step // (TOTAL_STEPS // 3), 2)

            red_action, red_host, red_success = red_agent.step()

            state = monitor.get_network_state()
            servers, users, routers = builder.classify_node_type(state)
            all_containers = servers + users

            compromises = detector.scan(all_containers)
            compromised_count = sum(1 for v in compromises.values() if v >= 1)

            action_int = adapter.get_action(
                state, phase, red_agent.host_states, compromises, decoys=executor._decoys
            )
            result = executor.execute(action_int, servers, users)

            row = {
                "step": step + 1,
                "phase": phase,
                "red_action": red_action,
                "red_host": red_host,
                "red_success": red_success,
                "blue_action_type": result["action_type"],
                "blue_target": result["target"],
                "blue_result": result["result"],
                "compromised_count": compromised_count,
                "decoy_count": len(executor._decoys),
            }
            rows.append(row)
            writer.writerow(row)
            f.flush()

            print(
                f"[{step+1:3d}] Phase {phase} | "
                f"RED: {red_action:<28} on {str(red_host):<40} | "
                f"BLUE: {result['action_type']:<14} on {str(result['target']):<40} | "
                f"Compromised: {compromised_count}  Decoys: {len(executor._decoys)}"
            )

    print(f"\nResults saved to {csv_path}\n")
    
    executor.cleanup_stale_decoys()
    detector.cleanup_flags(all_containers)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mask", action="store_true", help="Enable edge action masking (actions 64-79)")
    args = parser.parse_args()
    run_evaluation(mask_edge_actions=args.mask)
