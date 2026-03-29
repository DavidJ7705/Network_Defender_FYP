import shutil
import pytest
from network_monitor import ContainerlabMonitor
from agent_adapter import AgentAdapter
from action_executor import ActionExecutor
from graph_builder import ObservationGraphBuilder, CONTAINER_ROLES


def test_analyse_action():
    monitor = ContainerlabMonitor()
    builder = ObservationGraphBuilder()
    executor = ActionExecutor()
    state = monitor.get_network_state()
    servers, users, _ = builder.classify_node_type(state)
    result = executor.execute(0, servers, users)  # action 0 = Analyse host_idx 0
    assert result["action_type"] == "Analyse"
    assert result["result"] is not None


def test_block_and_restore():
    monitor = ContainerlabMonitor()
    builder = ObservationGraphBuilder()
    executor = ActionExecutor()
    state = monitor.get_network_state()
    servers, users, _ = builder.classify_node_type(state)
    block_result = executor.execute(16, servers, users)   # action 16 = Remove host_idx 0
    assert block_result["action_type"] == "Remove"
    restore_result = executor.execute(32, servers, users) # action 32 = Restore host_idx 0
    assert restore_result["action_type"] == "Restore"


def test_agent_pipeline():
    monitor = ContainerlabMonitor()
    adapter = AgentAdapter()
    executor = ActionExecutor()
    state = monitor.get_network_state()
    action = adapter.get_action(state)
    servers = sorted(
        adapter.builder._last_servers,
        key=lambda c: CONTAINER_ROLES[c["clean_name"]][1]
    )
    users = sorted(
        adapter.builder._last_users,
        key=lambda c: CONTAINER_ROLES[c["clean_name"]][1]
    )
    result = executor.execute(action, servers, users)
    assert result["action_type"] is not None


@pytest.mark.skipif(not shutil.which("clab"), reason="containerlab not available")
def test_deploy_decoy():
    monitor = ContainerlabMonitor()
    builder = ObservationGraphBuilder()
    executor = ActionExecutor()
    state = monitor.get_network_state()
    servers, users, _ = builder.classify_node_type(state)
    result = executor.execute(48, servers, users)  # action 48 = DeployDecoy host_idx 0
    assert result["action_type"] == "DeployDecoy"
    executor.cleanup_decoys()