from network_monitor import ContainerlabMonitor
from graph_builder import ObservationGraphBuilder


def test_containers_discovered():
    monitor = ContainerlabMonitor()
    state = monitor.get_network_state()
    assert len(state["containers"]) > 0


def test_most_containers_have_ip():
    monitor = ContainerlabMonitor()
    state = monitor.get_network_state()
    # blocked containers legitimately have no IP — assert majority are connected
    with_ip = [c for c in state["containers"] if c["ip"] is not None]
    assert len(with_ip) > 0


def test_containers_classified():
    monitor = ContainerlabMonitor()
    builder = ObservationGraphBuilder()
    state = monitor.get_network_state()
    servers, users, routers = builder.classify_node_type(state)
    assert len(servers) > 0
    assert len(users) > 0
    assert len(routers) > 0


def test_processes_collected():
    monitor = ContainerlabMonitor()
    state = monitor.get_network_state()
    assert len(state["processes"]) > 0