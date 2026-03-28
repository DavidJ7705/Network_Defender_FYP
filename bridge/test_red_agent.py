from network_monitor import ContainerlabMonitor
from graph_builder import ObservationGraphBuilder
from red_agent import RedAgent, ACTION_NAMES

monitor = ContainerlabMonitor()
builder = ObservationGraphBuilder()
state   = monitor.get_network_state()

servers, users, routers = builder.classify_node_type(state)
containers = servers + users

agent = RedAgent(containers)

# Force hosts into all FSM states so every action branch is reachable
agent.host_states["restricted-zone-a-server-0"]["state"] = "S"    # unlocks ExploitRemoteService (4)
agent.host_states["operational-zone-a-server-0"]["state"] = "U"   # unlocks PrivilegeEscalate (5)
agent.host_states["restricted-zone-b-server-0"]["state"] = "R"    # unlocks Impact (6), DegradeServices (7), Withdraw (8)
agent.host_states["operational-zone-b-server-0"]["state"] = "SD"  # unlocks DiscoverDeception (3)

print("Initial host states:")
for host, info in agent.host_states.items():
    print(f"  {host}: {info['state']}")

print("\n--- Running 20 steps ---\n")
for i in range(20):
    host, action_idx = agent._choose_host_and_action()
    action_name = ACTION_NAMES[action_idx]
    success = agent._execute_action(host, action_idx)
    agent._transition_state(host, action_idx, success)
    print(f"Step {i+1}: {action_name} on {host} — success={success}\n")

