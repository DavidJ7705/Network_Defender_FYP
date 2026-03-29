import docker
from network_monitor import ContainerlabMonitor
from intrusion_detector import IntrusionDetector
from graph_builder import ObservationGraphBuilder

PREFIX = "clab-cage4-defense-network-"


def test_clean_state():
    monitor = ContainerlabMonitor()
    builder = ObservationGraphBuilder()
    detector = IntrusionDetector()
    state = monitor.get_network_state()
    servers, users, _ = builder.classify_node_type(state)
    target = servers[0]["clean_name"]
    results = detector.scan(servers + users)
    assert results[target] == 0


def test_user_compromise_detected():
    monitor = ContainerlabMonitor()
    builder = ObservationGraphBuilder()
    detector = IntrusionDetector()
    client = docker.from_env()
    state = monitor.get_network_state()
    servers, users, _ = builder.classify_node_type(state)
    target = servers[0]["clean_name"]
    client.containers.get(PREFIX + target).exec_run("touch /tmp/.compromised")
    results = detector.scan(servers + users)
    assert results[target] == 1
    client.containers.get(PREFIX + target).exec_run("rm -f /tmp/.compromised")


def test_root_compromise_detected():
    monitor = ContainerlabMonitor()
    builder = ObservationGraphBuilder()
    detector = IntrusionDetector()
    client = docker.from_env()
    state = monitor.get_network_state()
    servers, users, _ = builder.classify_node_type(state)
    target = servers[0]["clean_name"]
    client.containers.get(PREFIX + target).exec_run("touch /root/.compromised")
    results = detector.scan(servers + users)
    assert results[target] == 2
    client.containers.get(PREFIX + target).exec_run("rm -f /root/.compromised")