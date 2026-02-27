import torch
import os, sys
from graph_builder import FEATURE_DIM, NUM_ROUTERS, CONTAINER_ROLES, ObservationGraphBuilder
from network_monitor import ContainerlabMonitor

WEIGHTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "trained-agent", "weights", "gnn_ppo-0.pt"
)



data = torch.load(WEIGHTS_PATH, map_location="cpu", weights_only=False)
in_dim = data["agent"][0][0]

print(f"Dimension check")
print(f"Agent in_dim (from weights):{in_dim}")
print(f"FEATURE_DIM (graph builder):{FEATURE_DIM}")
print(f"Match: {in_dim == FEATURE_DIM}")

builder = ObservationGraphBuilder()

print(f"\nContianer lab role maps")
try:
    monitor = ContainerlabMonitor()
    state = monitor.get_network_state()
    print(f"Containers found: {len(state['containers'])}")
except Exception as e:
    print(f"Monitor failed ({e})")
    state = None

for role_name, (role_type, slot) in CONTAINER_ROLES.items():
    print(f"{role_name:20} -> {role_type} slot {slot}")

unmapped = []
if state:
    for c in state["containers"]:
        name = c["name"].replace("clab-fyp-defense-network-", "")
        if name not in CONTAINER_ROLES:
            unmapped.append(name)
    print(f"\nUnmapped (excluded): {unmapped}")


print(f"\nSystem node encoding")
test_cases = [
    {"name": "web-server", "is_compromised": True},
    {"name": "database",   "is_compromised": False},
    {"name": "admin-ws",   "is_compromised": True},
]
for c in test_cases:
    role, slot = CONTAINER_ROLES[c["name"]]
    feature_vector = builder.encode_host(c, role)
    non_zero = {idx: value for idx, value in enumerate(feature_vector) if value != 0.0}
    status = "COMPROMISED" if c["is_compromised"] else "clean"
    print(f"  {c['name']:20} [{status}]")
    for pos, val in non_zero.items():
        print(f"    [{pos}] = {val}")