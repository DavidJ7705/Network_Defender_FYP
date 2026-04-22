# Translates agent action integers to real Docker operations on live containers.
# Actions: 0-63 node actions (Analyse/Block/Restore/DeployDecoy), 64-79 subnet firewall, 80 Monitor.
#
# Terminal 1 (deploy topology):
#   cd ~/Desktop/Network_Defender_FYP/containerlab-networks
#   sudo containerlab deploy -t cage4-topology.yaml
#
# Terminal 2 (run):
#   cd ~/Desktop/Network_Defender_FYP/bridge
#   sudo ~/fyp-venv-linux/bin/python action_executor.py
#
# Cleanup (when done):
#   sudo containerlab destroy -t cage4-topology.yaml

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

SUBNET_CIDR = {
    "admin-network-router": "10.0.7.0/24",
    "contractor-network-router": "10.0.5.0/24",
    "office-network-router": "10.0.8.0/24",
    "operational-zone-a-router": "10.0.2.0/24",
    "operational-zone-b-router": "10.0.4.0/24",
    "public-access-zone-router": "10.0.6.0/24",
    "restricted-zone-a-router": "10.0.1.0/24",
    "restricted-zone-b-router": "10.0.3.0/24",
}

SUBNET_GATEWAY = {
    "admin-network-router": "public-access-zone-router",
    "contractor-network-router": "internet-router",
    "office-network-router": "public-access-zone-router",
    "operational-zone-a-router": "restricted-zone-a-router",
    "operational-zone-b-router": "restricted-zone-b-router",
    "public-access-zone-router": "internet-router",
    "restricted-zone-a-router": "internet-router",
    "restricted-zone-b-router": "internet-router",
}

SUBNET_ROUTERS_SORTED = sorted(SUBNET_CIDR.keys())

SUBNET_RESTORE_VIA = {
    "admin-network-router": "10.0.6.2",
    "contractor-network-router": "10.0.0.10",
    "office-network-router": "10.0.6.6",
    "operational-zone-a-router": "10.0.1.2",
    "operational-zone-b-router": "10.0.3.2",
    "public-access-zone-router": "10.0.0.14",
    "restricted-zone-a-router": "10.0.0.2",
    "restricted-zone-b-router": "10.0.0.6",
}


class ActionExecutor:
    def __init__(self):
        self.client = docker.from_env()
        self._decoys = {}
        self._blocks = {}
        self._blocked_hosts = set()

    def execute(self, action, servers, users):
        print(f"Executing action: {action}")


        
        if  64 <= action <=71:
            print(f"Allow traffic {action}")
            subnet_router = SUBNET_ROUTERS_SORTED[action - 64]
            return self._allow_traffic(subnet_router)
        if  72 <= action <=79:
            print(f"Block traffic {action}")
            subnet_router = SUBNET_ROUTERS_SORTED[action - 72]
            return self._block_traffic(subnet_router)

        if action >= 80:
            print(f"Global action — Monitor")
            return {"action_type": "Monitor", "target": None, "result": "no operation yet implemented"}
        
        
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
            processes = container.exec_run("ps aux").output.decode(errors="replace")
            user_compromised = container.exec_run("ls /tmp/.compromised").exit_code == 0
            root_compromised = container.exec_run("ls /root/.compromised").exit_code == 0
            print(f"Analyse {clean_name}:\n{processes[:300]}\nUser compromised: {user_compromised}, Root compromised: {root_compromised}")
            return {
                "action_type": "Analyse", 
                "target": clean_name, 
                "result": {
                    "processes": processes,
                    "user_compromised": user_compromised,
                    "root_compromised": root_compromised
                }
            }
        except Exception as e:
            print(f"Error analysing {clean_name}: {e}")
            return {"action_type": "Analyse", "target": clean_name, "result": f"error: {e}"}
        
    def _block(self, full_name, clean_name):
        try:
            container = self.client.containers.get(full_name)
            container.reload()
            net_names = list(container.attrs["NetworkSettings"]["Networks"].keys())
            if not net_names:
                return {"action_type": "Remove", "target": clean_name, "result": "already blocked"}
            mgmt_network = next((n for n in net_names if n.startswith("clab")), net_names[0])
            self.client.networks.get(mgmt_network).disconnect(container)
            self._blocked_hosts.add(clean_name)
            print(f"[Executor] Blocked {clean_name} — disconnected from {mgmt_network}")
            return {"action_type": "Remove", "target": clean_name, "result": "blocked"}
        except Exception as e:
            print(f"Error Block failed {clean_name}: {e}")
            return {"action_type": "Remove", "target": clean_name, "result": f"error: {e}"}

    def _restore(self, full_name, clean_name):
        self._blocked_hosts.discard(clean_name)
        try:
            container = self.client.containers.get(full_name)
            container.reload()
            connected = list(container.attrs["NetworkSettings"]["Networks"].keys())
            mgmt_network = self._get_mgmt_network(container)
            was_blocked  = mgmt_network and mgmt_network not in connected
            container.restart()
            container.exec_run("rm -f /tmp/.compromised /root/.compromised")
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

    def cleanup_stale_decoys(self):
        import glob
        for yaml_path in glob.glob("/tmp/decoy_*.yaml"):
            subprocess.run(["clab", "destroy", "-t", yaml_path],
                        capture_output=True, text=True)
            try:
                os.remove(yaml_path)
            except Exception:
                pass

    def _allow_traffic(self, subnet_router_name):
        if subnet_router_name not in self._blocks:
            return {"action_type": "AllowTraffic", "target": subnet_router_name, "result": "not currently blocked"}
        
        full_gateway, cidr = self._blocks[subnet_router_name]
        via = SUBNET_RESTORE_VIA[subnet_router_name]
        try:
            container = self.client.containers.get(full_gateway)
            container.exec_run(f"ip route replace {cidr} via {via}")
            del self._blocks[subnet_router_name]
            print(f"Traffic to {subnet_router_name} allowed via {via}")
            return {"action_type": "AllowTraffic", "target": subnet_router_name, "result": f"traffic allowed via {via}"}
        except Exception as e:
            print(f"Error allowing traffic to {subnet_router_name}: {e}")
            return {"action_type": "AllowTraffic", "target": subnet_router_name, "result": f"error: {e}"}

    def _block_traffic(self, subnet_router_name):
        gateway = SUBNET_GATEWAY[subnet_router_name]
        cidr = SUBNET_CIDR[subnet_router_name]
        full_gateway = CLAB_PREFIX + gateway
        try:
            container = self.client.containers.get(full_gateway)
            result = container.exec_run(f"ip route replace blackhole {cidr}")
            if result.exit_code == 0:
                self._blocks[subnet_router_name] = (full_gateway, cidr)
                print(f"Traffic to {subnet_router_name} blocked via {gateway}")
                return {"action_type": "BlockTraffic", "target": subnet_router_name, "result": "traffic blocked"}
            return {"action_type": "BlockTraffic", "target": subnet_router_name, "result": f"error: {result.output.decode()}"}
        except Exception as e:
            print(f"Error blocking traffic to {subnet_router_name}: {e}")
            return {"action_type": "BlockTraffic", "target": subnet_router_name, "result": f"error: {e}"}