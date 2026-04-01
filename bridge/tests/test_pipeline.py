import os
import pytest
from network_monitor import ContainerlabMonitor
from agent_adapter import AgentAdapter
from action_executor import ActionExecutor
from graph_builder import ObservationGraphBuilder, CONTAINER_ROLES

WEIGHTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "trained-agent", "weights", "gnn_ppo-0.pt"
)

def test_full_pipeline():

    if not os.path.exists(WEIGHTS_PATH):
        pytest.skip("weights file not in repo")

    monitor = ContainerlabMonitor()
    builder = ObservationGraphBuilder()
    adapter = AgentAdapter()
    executor = ActionExecutor()
    
    state = monitor.get_network_state()
    servers, users, routers = builder.classify_node_type(state)

    action_int = adapter.get_action(state, decoys=executor._decoys)
    result = executor.execute(action_int, servers, users)

    assert 0 <= action_int <= 80
    assert "action_type" in result
    assert "target" in result
    assert "result" in result