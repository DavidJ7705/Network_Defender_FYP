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


if state:
    servers, users, routers = builder.classify_node_type(state)
    print(f"  Servers: {len(servers)}")
    print(f"  Users: {len(users)}")
    print(f"  Routers: {len(routers)}")

unmapped = []
if state:
    for c in state["containers"]:
        name = c["name"].replace("clab-cage4-defense-network-", "")
        if name not in CONTAINER_ROLES:
            unmapped.append(name)
    print(f"\nUnmapped (excluded): {unmapped}")
