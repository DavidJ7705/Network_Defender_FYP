from network_monitor import ContainerlabMonitor
from agent_adapter import AgentAdapter
from action_executor import ActionExecutor
from graph_builder import CONTAINER_ROLES

monitor  = ContainerlabMonitor()
state    = monitor.get_network_state()
adapter  = AgentAdapter()
executor = ActionExecutor()

action = adapter.get_action(state)

servers = sorted(
    adapter.builder._last_servers,
    key=lambda c: CONTAINER_ROLES[c["clean_name"]][1]
)
users = sorted(
    adapter.builder._last_users,
    key=lambda c: CONTAINER_ROLES[c["clean_name"]][1]
)

print(f"Agent action : {action}")

result = executor.execute(action, servers, users)
print(f"Result: {result}")
