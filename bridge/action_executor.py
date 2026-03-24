import docker
import subprocess
import yaml
import os

CLAB_PREFIX = "clab-cage4-defense-network-"

MAX_SERVERS = 6
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
        self._decoys = {}

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
            return self._analyse(full_name, container_name)
        elif action_name == "Remove":
            return self._block(full_name, container_name)
        elif action_name == "Restore":
            return self._restore(full_name, container_name)
        elif action_name == "DeployDecoy":
            return self._deploy_decoy(full_name, container_name)
        else:
            raise ValueError(f"Unknown action: {action}")
        

    def _get_mgmt_network(self, container):
        all_containers = self.client.containers.list()
        cage4 = [c for c in all_containers
                 if c.name.startswith(CLAB_PREFIX) and "router" not in c.name
                 and c.name != container.name]
        
        if not cage4:
            return None
        ref = cage4[0]
        ref.reload()
        ref_nets = list(ref.attrs["NetworkSettings"]["Networks"].keys())
        return next((n for n in ref_nets if n.startswith("clab")), None)

    def _analyse(self, full_name, clean_name):
        try:
            container = self.client.containers.get(full_name)
            output = container.exec_run("ps aux").output.decode(errors="replace")
            print(f"Analyse {clean_name}:\n{output[:300]}")
            return {"action_type": "Analyse", "target": clean_name, "result": output}
        except Exception as e:
            print(f"Error analysing {clean_name}: {e}")
            return {"action_type": "Analyse", "target": clean_name, "result": f"error: {e}"}
        
    def _block(self, full_name, clean_name):
        try:
            container = self.client.containers.get(full_name)
            container.reload()
            net_names = list(container.attrs["NetworkSettings"]["Networks"].keys())
            mgmt_network = next((n for n in net_names if n.startswith("clab")), net_names[0])
            self.client.networks.get(mgmt_network).disconnect(container)
            print(f"[Executor] Blocked {clean_name} — disconnected from {mgmt_network}")
            return {"action_type": "Remove", "target": clean_name, "result": "blocked"}
        except Exception as e:
            print(f"Error Block failed {clean_name}: {e}")
            return {"action_type": "Remove", "target": clean_name, "result": f"error: {e}"}

    def _restore(self, full_name, clean_name):
        try:
            container = self.client.containers.get(full_name)
            container.reload()
            connected = list(container.attrs["NetworkSettings"]["Networks"].keys())
            mgmt_network = self._get_mgmt_network(container)
            was_blocked  = mgmt_network and mgmt_network not in connected
            container.restart()
            if was_blocked and mgmt_network:
                self.client.networks.get(mgmt_network).connect(container)
                print(f"[Executor] Reconnected {clean_name} to {mgmt_network}")
            print(f"[Executor] Restored {clean_name}")
            return {"action_type": "Restore", "target": clean_name, "result": "restarted"}
        except Exception as e:
            print(f"Error Restore failed {clean_name}: {e}")
            return {"action_type": "Restore", "target": clean_name, "result": f"error: {e}"}

    def _deploy_decoy(self, full_name, clean_name):
        if clean_name in self._decoys:
            print(f"Decoy already deployed for {clean_name}")
            return {"action_type": "DeployDecoy", "target": clean_name, "result": "decoy already deployed"}
        try:
            container = self.client.containers.get(full_name)
            mgmt_network = self._get_mgmt_network(container)
            print(f"[DEBUG] mgmt_network = {mgmt_network}")

            topology_name = f"decoy_{clean_name}"
            topology = {
                "name": topology_name,
                "mgmt": {"network": mgmt_network},
                "topology": {
                    "nodes": {
                        "decoy-host": {
                            "kind": "linux",
                            "image": "nginx:alpine",
                        }
                    }
                }
            }

            yaml_path = f"/tmp/{topology_name}.yaml"
            with open(yaml_path, "w") as f:
                yaml.dump(topology, f)
            result = subprocess.run(
                ["clab", "deploy", "-t", yaml_path],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                self._decoys[clean_name] = yaml_path
                print(f"Decoy deployed for {clean_name}")
                return {"action_type": "DeployDecoy", "target": clean_name, "result": "decoy deployed"}
            else:
                print(f"Error deploying decoy for {clean_name}: {result.stderr}")
                return {"action_type": "DeployDecoy", "target": clean_name, "result": f"error: {result.stderr}"}
            
        except Exception as e:
            print(f"Error preparing decoy deployment for {clean_name}: {e}")
            return {"action_type": "DeployDecoy", "target": clean_name, "result": f"error: {e}"}
        
    def cleanup_decoys(self):
        for clean_name, yaml_path in list(self._decoys.items()):
            topology_name = os.path.splitext(os.path.basename(yaml_path))[0]
            result = subprocess.run(
                ["clab", "destroy", "-t", yaml_path],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"Decoy {clean_name} cleaned up")
                del self._decoys[clean_name]
                try:
                    os.remove(yaml_path)
                except Exception as e:
                    pass  # Ignore errors in cleanup
            else:
                print(f"Error cleaning up decoy {clean_name}: {result.stderr}")