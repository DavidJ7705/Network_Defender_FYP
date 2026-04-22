# Builds a PyTorch Geometric graph from live network state (192-dim feature vector per node).
#
# Terminal 1 (deploy topology):
#   cd ~/Desktop/Network_Defender_FYP/containerlab-networks
#   sudo containerlab deploy -t cage4-topology.yaml
#
# Terminal 2 (run):
#   cd ~/Desktop/Network_Defender_FYP/bridge
#   sudo ~/fyp-venv-linux/bin/python graph_builder.py
#
# Cleanup (when done):
#   sudo containerlab destroy -t cage4-topology.yaml

import torch
from torch_geometric.data import Data

FEATURE_DIM = 192

NODE_TYPES = {
    "SystemNode":0,
    "ConnectionNode":1,
    "FileNode":2,
    "InternetNode":3,
}

NUM_ROUTERS = 9

CONTAINER_ROLES ={
    #servers
    "restricted-zone-a-server-0": ("server", 0),
    "restricted-zone-a-server-1": ("server", 1),
    "operational-zone-a-server-0": ("server", 2),
    "restricted-zone-b-server-0": ("server", 3),
    "operational-zone-b-server-0": ("server", 4),
    "contractor-network-server-0": ("server", 5),

    
    #users
    "restricted-zone-a-user-0": ("user", 0),
    "operational-zone-a-user-0": ("user", 1),
    "restricted-zone-b-user-0": ("user", 2),
    "operational-zone-b-user-0": ("user", 3),
    "contractor-network-user-0": ("user", 4),
    "contractor-network-user-1": ("user", 5),
    "public-access-zone-user-0": ("user", 6),
    "office-network-user-0": ("user", 7),
    "office-network-user-1": ("user", 8),
    "admin-network-user-0": ("user", 9),
    

}

# subnets in alphabetical order - gotten from inspect_weights.py
# [178]  admin_network_subnet_router
# [179]  contractor_network_subnet_router
# [180]  internet_subnet_router
# [181]  office_network_subnet_router
# [182]  operational_zone_a_subnet_router
# [183]  operational_zone_b_subnet_router
# [184]  public_access_zone_subnet_router
# [185]  restricted_zone_a_subnet_router
# [186]  restricted_zone_b_subnet_router
# [187]  tabular: was_compromised

class ObservationGraphBuilder:
    def build_graph(self, network_state, compromise_map=None, host_states=None, decoys=None, processes=None):
        servers, users, routers = self.classify_node_type(network_state)
        all_nodes = servers + users + routers
        nodes_to_idx = {c["clean_name"]: i for i, c in enumerate(all_nodes)}

        # store so AgentAdapter can read consistent ordering without a second classify call
        self._last_servers      = servers
        self._last_users        = users
        self._last_routers      = routers
        self._last_nodes_to_idx = nodes_to_idx

        if compromise_map:
            for c in all_nodes:
                c["compromise_level"] = compromise_map.get(c["clean_name"], 0)

        #feature matrix construction
        node_features = []
        for c in all_nodes:
            name = c["clean_name"]
            subnet_idx = self.get_subnet_index(name)
            role = "router" if name.endswith("-router") else CONTAINER_ROLES[name][0]
            node_features.append(self.encode_host(c, role, subnet_idx, host_states, processes=processes, decoys=decoys))
        x = torch.tensor(node_features, dtype = torch.float)
        

        #Build edge index
        edge_index = []
        for c in servers + users:
            host_idx = nodes_to_idx[c["clean_name"]]
            subnet_idx = self.get_subnet_index(c["clean_name"])
            for router in routers:
                if router["clean_name"] != "internet-router" and self.get_subnet_index(router["clean_name"]) == subnet_idx:
                    router_idx = nodes_to_idx[router["clean_name"]]
                    edge_index += [[host_idx, router_idx], [router_idx, host_idx]]
                    break

        #connecting subnet routers to internet router
        internet_idx = nodes_to_idx["internet-router"]
        for router in routers:
            if router["clean_name"] != "internet-router" and internet_idx is not None:
                router_idx = nodes_to_idx[router["clean_name"]]
                edge_index += [[router_idx, internet_idx], [internet_idx, router_idx]]

        edge_index = torch.tensor(edge_index, dtype=torch.long).t().contiguous()
        return Data(x=x, edge_index=edge_index)



    def classify_node_type(self, state):
        servers, users, routers = [], [], []
        for container in state["containers"]:
            name = container["name"].replace("clab-cage4-defense-network-", "")
            container["clean_name"] = name

            if name.endswith("-router"):
                routers.append(container)
            elif name in CONTAINER_ROLES and CONTAINER_ROLES[name] is not None:
                role = CONTAINER_ROLES[name][0]
                if role == "server":
                    servers.append(container)
                else:
                    users.append(container)

        return servers, users, routers

    def get_subnet_index (self, clean_name):
        if "admin-network" in clean_name: return 0
        elif "contractor-network" in clean_name: return 1
        elif "internet" in clean_name: return 2
        elif "office-network" in clean_name: return 3
        elif "operational-zone-a" in clean_name: return 4
        elif "operational-zone-b" in clean_name: return 5
        elif "public-access-zone" in clean_name: return 6
        elif "restricted-zone-a" in clean_name: return 7
        elif "restricted-zone-b" in clean_name: return 8
        return 0

    def encode_host(self, container, role, subnet_idx, host_states= None, processes=None, decoys=None):
        features = [0.0] * FEATURE_DIM

        #node type
        if role in ("server", "user"):
            features[0] = 1.0 #system node
        else:
            features[3] = 1.0 #internet node

        #Architecture and OS
        features[5] = 1.0 #x64
        features[14] = 1.0 #ubuntu
        features[24] = 1.0 #linux

        if role == "server":
            features[56] = 1.0 #server
        elif role == "router":
            features[57] = 1.0 #router
        elif role == "user":
            features[55] = 1.0 #user

        features[178 +subnet_idx] = 1.0

        level = container.get("compromise_level", 0)
        if level >= 1:
            features[187] = 1.0

        name = container.get("clean_name","")
        if host_states:
            red_state = host_states.get(name, {}).get('state','K')
            if red_state in ("S", "SD", "U", "UD", "R", "RD"):
                features[188] = 1.0

        #Process based features from ps
        if processes:
            proc = processes.get(name, [])
            cmds = " ".join(p.get("command", "") for p in proc).lower() if isinstance(proc, list) else ""
            features[60] = 1.0
            features[78] = 1.0
            features[101] = 1.0
            if "sshd" in cmds:
                features[64] = 1.0
                features[88] = 1.0
            if "apache2" in cmds or "nginx" in cmds:
                features[70] = 1.0
                features[93] = 1.0

        #Suspicious pid
        if level >=1:
            features[99] = 1.0

        #decoy flags 
        if decoys and name in decoys:
            features[100] = 1.0 #is decoy?
            features[102] = 1.0 #is ephemeral

        return features
    
