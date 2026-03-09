
from network_monitor import ContainerlabMonitor
from agent_adapter import AgentAdapter

monitor = ContainerlabMonitor()
state   = monitor.get_network_state()
print(f"Containers found: {len(state['containers'])}")

adapter = AgentAdapter()
action  = adapter.get_action(state)
print(f"Agent action: {action}")

if action < 64:
    action_type = action // 16
    host_idx    = action % 16
    print(f"-> Node action - type_idx={action_type} - host_idx={host_idx}")
elif action < 80:
    print(f"-> action  idx={action}")
else:
    print(f"-> Some other Action")