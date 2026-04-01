import os
import pytest
from network_monitor import ContainerlabMonitor
from agent_adapter import AgentAdapter

WEIGHTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "trained-agent", "weights", "gnn_ppo-0.pt"
)


def test_agent_returns_valid_action():
    if not os.path.exists(WEIGHTS_PATH):
        pytest.skip("weights file not in repo")
    monitor = ContainerlabMonitor()
    adapter = AgentAdapter()
    state = monitor.get_network_state()
    action = adapter.get_action(state)
    assert 0 <= action <= 80, f"action {action} out of valid range 0-80"


def test_node_action_decodes_correctly():
    if not os.path.exists(WEIGHTS_PATH):
        pytest.skip("weights file not in repo")
    monitor = ContainerlabMonitor()
    adapter = AgentAdapter()
    state = monitor.get_network_state()
    action = adapter.get_action(state)
    if action < 64:
        assert 0 <= action // 16 <= 3
        assert 0 <= action % 16 <= 15