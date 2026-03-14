import docker
import json
from datetime import datetime

CLAB_PREFIX = "clab-cage4-defense-network-"

MAX_SERVERS = 6
MAX_USERS = 10
MAX_HOSTS = 16

ACTION_TYPES ={
    0: "Analyse",
    1: "Remove",
    2: "Restore",
    3: "DeployDecoy",
}

class ActionExecutor:
    def __init__(self):
        self.client = docker.from_env()

    def execute(self, action, servers, users):
        print(f"Executing action: {action}")

        if action >= 80:
            print(f"Global action — Monitor")
            return {"action_type": "Monitor", "target": None, "result": "no operation yet implemented"}
        
        if action >= 64:
            print(f"Edge action {action}")
            return {"action_type": "EdgeAction", "target": None, "result": "edge actions not implemented yet"}
        
        action_type_idx = action // MAX_HOSTS
        host_idx        = action % MAX_HOSTS
        action_name     = ACTION_TYPES.get(action_type_idx, "Unknown")
        
        if host_idx < MAX_SERVERS:
            if host_idx >= len(servers):
                return {"action_type": action_name, "target": None, "result": "invalid"}
            container_name = servers[host_idx]["clean_name"]
        else:
            user_idx = host_idx - MAX_SERVERS
            if user_idx >= len(users):
                return {"action_type": action_name, "target": None, "result": "invalid"}
            container_name = users[user_idx]["clean_name"]

        full_name = CLAB_PREFIX + container_name
        print(f"Action: {action_name} on {container_name} (action={action}, host_idx={host_idx})")

        if action_name == "Analyse":
            return self._analyse(servers, users)
        # elif action_name == "Remove":
        #     return self._block(servers, users)
        # elif action_name == "Restore":
        #     return self._restore(servers, users)
        # elif action_name == "DeployDecoy":
        #     return self._deploy_decoy(servers, users)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    def _analyse(self, full_name, clean_name):
        try:
            container = self.client.containers.get(full_name)
            output = container.exec_run("ps aux").output.decode(errors="replace")
            print(f"Analyse output for {clean_name}:\n{output[:1000]}")
            return {"action_type": "Analyse", "target": clean_name, "result": output}
        except Exception as e:
            print(f"Error analysing {clean_name}: {e}")
            return {"action_type": "Analyse", "target": clean_name, "result": f"error: {e}"}
