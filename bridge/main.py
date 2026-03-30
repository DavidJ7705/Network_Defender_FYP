import signal
import sys

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
detector = IntrusionDetector()

#initial calssification to get red agents container lsit
state = monitor.get_network_state()
servers, users, routers = builder.classify_node_type(state)
all_containers = servers + users 

#clean up any existing decoys or flags from previous runs
executor.cleanup_stale_decoys()
detector.cleanup_flags(all_containers)

red_agent = RedAgent(all_containers, decoys=executor._decoys)

def shutdown(sig, frame):
    print("\nShutting down...")
    executor.cleanup_stale_decoys()
    detector.cleanup_flags(all_containers)
    sys.exit(0)
signal.signal(signal.SIGINT, shutdown)

def run(total_steps = MAX_STEPS):
    print(f"Network Defender - Starting @{total_steps} steps per episode\n")

    for step in range(total_steps):
        phase = step //(total_steps//3)
        print(f"Step {step+1}")

        #Red agent attacks
        red_action, red_host, red_success = red_agent.step()
        print(f"[RED] {red_action} on {red_host} - status: {red_success}")


        #Blue agent observes
        state = monitor.get_network_state()
        servers, users, routers = builder.classify_node_type(state)
        all_containers = servers + users

        #Intrusion detector scans containers
        compromises = detector.scan(all_containers)

        #Blue agent acts
        action_int = adapter.get_action(state, phase, red_agent.host_states, compromises, decoys=executor._decoys)
        result = executor.execute(action_int, servers, users)
        print(f"[BLUE] action={action_int} {result['action_type']} on {result['target']} - {result['result']}")
        print()
    
    print("Episode complete. Cleaning up...")
    executor.cleanup_stale_decoys()
    detector.cleanup_flags(all_containers)


if __name__ == "__main__":
    run()
