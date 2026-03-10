from network_monitor import ContainerlabMonitor
from agent_adapter import AgentAdapter
from action_executor import ActionExecutor

monitor = ContainerlabMonitor()
state = monitor.get_network_state()
adapter = AgentAdapter()
executor = ActionExecutor()
