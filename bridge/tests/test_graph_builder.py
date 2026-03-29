import os
import pytest
import torch
from graph_builder import FEATURE_DIM, ObservationGraphBuilder
from network_monitor import ContainerlabMonitor

WEIGHTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "trained-agent", "weights", "gnn_ppo-0.pt"
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