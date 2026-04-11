import json
import os
import signal
import sys
from collections import Counter

import server
from network_monitor import ContainerlabMonitor
from graph_builder import ObservationGraphBuilder
from agent_adapter import AgentAdapter
from action_executor import ActionExecutor
from red_agent import RedAgent
from intrusion_detector import IntrusionDetector

MAX_STEPS = 100

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")

monitor = ContainerlabMonitor()
builder = ObservationGraphBuilder()
adapter = AgentAdapter()
executor = ActionExecutor()
detector = IntrusionDetector()

#initial classification to get red agents container list
state = monitor.get_network_state()
servers, users, routers = builder.classify_node_type(state)
all_containers = servers + users

#clean up any existing decoys or flags from previous runs
executor.cleanup_stale_decoys()
detector.cleanup_flags(all_containers)

red_agent = RedAgent(all_containers, decoys=executor._decoys)

def shutdown(sig, frame):
    print("\nShutting down...")
    executor.cleanup_stale_decoys()
    detector.cleanup_flags(all_containers)
    sys.exit(0)
signal.signal(signal.SIGINT, shutdown)


def _write_state(step, phase, red_action, red_host, result, compromises, servers, users):
    blue_tgt = result.get("target")

    # Build nodeStatuses: blocked > compromised > clean, then overlay transient actions
    node_statuses = {}
    for host in servers + users:
        name = host["clean_name"]
        if name in executor._blocked_hosts:
            node_statuses[name] = "blocked"
        elif compromises.get(name, 0) >= 1:
            node_statuses[name] = "compromised"
        else:
            node_statuses[name] = "clean"

    # Transient visual for blue's action this step
    if blue_tgt and blue_tgt in node_statuses:
        if result["action_type"] == "Restore":
            node_statuses[blue_tgt] = "restored"
        elif result["action_type"] == "Analyse":
            node_statuses[blue_tgt] = "analysed"

    # Flatten FSM host_states {"state": "K"} → "K"
    fsm_states = {k: v["state"] for k, v in red_agent.host_states.items()}
    fsm_counts = Counter(fsm_states.values())

    payload = {
        "step":           step + 1,
        "phase":          phase,
        "nodeStatuses":   node_statuses,
        "fsmStates":      fsm_states,
        "fsmCounts":      {k: fsm_counts.get(k, 0) for k in ["K", "KD", "S", "SD", "U", "UD", "R", "RD", "F"]},
        "blockedRouters": list(executor._blocks.keys()),
        "activeDecoys":   list(executor._decoys.keys()),
        "highlighted":    {k: True for k in [red_host, blue_tgt] if k},
        "events":         list(_write_state.events),
        "nComp":    sum(1 for s in node_statuses.values() if s == "compromised"),
        "nClean":   sum(1 for s in node_statuses.values() if s == "clean"),
        "nBlocked": len(executor._blocked_hosts),
        "nRestored": 1 if (blue_tgt and result["action_type"] == "Restore") else 0,
        "nAnalysed": 1 if (blue_tgt and result["action_type"] == "Analyse") else 0,
        "nDecoy":   len(executor._decoys),
        "nZones":   len(executor._blocks),
    }

    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f)
    os.replace(tmp, STATE_FILE)

_write_state.events = []  # rolling event log, persists across steps


def run(total_steps=MAX_STEPS):
    print(f"Network Defender - Starting @{total_steps} steps per episode\n")
    _write_state.events = []

    server.start(port=8080)

    for step in range(total_steps):
        phase = min(step // (total_steps // 3), 2)
        print(f"Step {step+1}")

        #Red agent attacks
        red_action, red_host, red_success = red_agent.step()
        print(f"[RED] {red_action} on {red_host} - status: {red_success}")

        if red_action:
            _write_state.events.append({
                "step": step + 1, "actor": "red",
                "type": red_action, "target": red_host or "—"
            })

        #Blue agent observes
        state = monitor.get_network_state()
        servers, users, routers = builder.classify_node_type(state)
        all_containers = servers + users

        #Intrusion detector scans containers
        compromises = detector.scan(all_containers)

        #Blue agent acts
        action_int = adapter.get_action(state, phase, red_agent.host_states, compromises, decoys=executor._decoys)
        result = executor.execute(action_int, servers, users)
        print(f"[BLUE] action={action_int} {result['action_type']} on {result['target']} - {result['result']}")
        print()

        _write_state.events.append({
            "step": step + 1, "actor": "blue",
            "type": result["action_type"], "target": result.get("target") or "—"
        })
        if len(_write_state.events) > 80:
            _write_state.events = _write_state.events[-80:]

        _write_state(step, phase, red_action, red_host, result, compromises, servers, users)

    print("Episode complete. Cleaning up...")
    executor.cleanup_stale_decoys()
    detector.cleanup_flags(all_containers)


if __name__ == "__main__":
    run()
