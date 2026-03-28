from network_monitor import ContainerlabMonitor
from graph_builder import ObservationGraphBuilder
from agent_adapter import AgentAdapter
from action_executor import ActionExecutor
from red_agent import RedAgent
from intrusion_detector import IntrusionDetector

MAX_STEPS = 100

monitor = ContainerlabMonitor()
builder = ObservationGraphBuilder()
adapter = AgentAdapter()
executor = ActionExecutor()
detector = IntrusionDetector

state = monitor.get_network_state()
servers, users, routers = builder.classify_node_type(state)
containers = servers + users 

red_agent = RedAgent(containers,decoys = executor._decoys)