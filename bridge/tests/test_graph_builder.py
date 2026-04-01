import os
import pytest
import torch
from graph_builder import FEATURE_DIM, ObservationGraphBuilder
from network_monitor import ContainerlabMonitor

WEIGHTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "trained-agent", "weights", "gnn_ppo-0.pt"
)


def test_feature_dim_matches_weights():
    if not os.path.exists(WEIGHTS_PATH):
        pytest.skip("weights file not in repo")
    data = torch.load(WEIGHTS_PATH, map_location="cpu", weights_only=False)
    in_dim = data["agent"][0][0]
    assert in_dim == FEATURE_DIM, f"weights expect {in_dim}, graph builder produces {FEATURE_DIM}"


def test_graph_correct_shape():
    monitor = ContainerlabMonitor()
    builder = ObservationGraphBuilder()
    state = monitor.get_network_state()
    graph = builder.build_graph(state)
    assert graph.x.shape[1] == FEATURE_DIM
    assert graph.x.shape[0] > 0


def test_servers_and_users_classified():
    monitor = ContainerlabMonitor()
    builder = ObservationGraphBuilder()
    state = monitor.get_network_state()
    servers, users, routers = builder.classify_node_type(state)
    assert len(servers) > 0
    assert len(users) > 0
    assert len(routers) > 0


def test_feature_indices():
    monitor = ContainerlabMonitor()
    builder = ObservationGraphBuilder()
    state = monitor.get_network_state()
    graph = builder.build_graph(state, processes=state.get("processes", {}))
    nodes = builder._last_servers + builder._last_users + builder._last_routers

    for i, c in enumerate(nodes):
        row = graph.x[i]
        non_zero = {idx: round(float(row[idx]), 1) for idx in range(192) if row[idx] != 0.0}
        print(f"{c['clean_name']}: {non_zero}")

    # every node has exactly one subnet bit set
    for i, c in enumerate(nodes):
        subnet_bits = sum(float(graph.x[i][178 + j]) for j in range(9))
        assert subnet_bits == 1.0, f"{c['clean_name']} subnet one-hot invalid"