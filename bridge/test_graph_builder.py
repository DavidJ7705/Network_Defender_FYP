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

    print("\nServers List:")
    for server in servers:
        subnet_idx = builder.get_subnet_index(server["clean_name"])
        print(f"  Server: {server['clean_name']}, Subnet idx: {subnet_idx} features[{178+subnet_idx}]")

    print("\nUsers List:")
    for user in users:
        subnet_idx = builder.get_subnet_index(user["clean_name"])
        print(f"  User: {user['clean_name']}, Subnet idx: {subnet_idx} features[{178+subnet_idx}]")

    print("\nRouters List:")
    for router in routers:
        subnet_idx = builder.get_subnet_index(router["clean_name"])
        print(f"  Router: {router['clean_name']}, Subnet idx: {subnet_idx} features[{178+subnet_idx}]")

unmapped = []
if state:
    for c in state["containers"]:
        name = c["name"].replace("clab-cage4-defense-network-", "")
        if name not in CONTAINER_ROLES:
            unmapped.append(name)
    print(f"\nUnmapped (excluded): {unmapped}")

print(f"\nSystem node encoding")
test_cases = [
    {"container": {"name": "restricted-zone-a-server-0", "is_compromised": True}, "role": "server"},
    {"container": {"name": "admin-network-user-0", "is_compromised": False}, "role": "user"},
    {"container": {"name": "internet-router", "is_compromised": False}, "role": "router"},
]
for tc in test_cases:
    c = tc["container"]
    role = tc["role"]
    subnet_idx = builder.get_subnet_index(c["name"])
    feature_vector = builder.encode_host(c, role, subnet_idx)
    non_zero = {idx: value for idx, value in enumerate(feature_vector) if value != 0.0}
    status = "COMPROMISED" if c["is_compromised"] else "clean"
    print(f"  {c['name']:42} [{status}]  role={role}")
    for pos, val in non_zero.items():
        print(f"    [{pos}] = {val}")


if state:
    result = builder.build_graph(state)