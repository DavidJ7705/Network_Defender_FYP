from network_monitor import ContainerlabMonitor
from graph_builder import ObservationGraphBuilder
from red_agent import RedAgent, ACTION_NAMES

monitor = ContainerlabMonitor()
builder = ObservationGraphBuilder()
state   = monitor.get_network_state()

servers, users, routers = builder.classify_node_type(state)
containers = servers + users

agent = RedAgent(containers)

print("Initial host states:")
for host, info in agent.host_states.items():
    print(f"  {host}: {info['state']}")

print("\n--- Running 20 steps ---\n")
for i in range(20):
    action_name, host, success = agent.step()
    print(f"Step {i+1}: {action_name} on {host} — success={success}\n")

print("Final host states:")
for host, info in agent.host_states.items():
    print(f"  {host}: {info['state']}")

