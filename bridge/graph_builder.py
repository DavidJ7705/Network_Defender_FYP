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
    def build_graph(self, network_state):
        servers, users, routers = self.classify_node_type(network_state)
        all_nodes = servers + users + routers
        print(f"Total node count: {len(all_nodes)}")


        return None #for now 

    
        
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

    def encode_host(self, container, role, subnet_idx):
        features = [0.0] * FEATURE_DIM

        features[14] = 1.0 #ubuntu
        features[24] = 1.0 #linux

        if role == "server":
            features[56] = 1.0 #server
        elif role == "router":
            features[57] = 1.0 #router
        elif role == "user":
            features[55] = 1.0 #user

        features[178 +subnet_idx] = 1.0

        if container.get("is_compromised"):
            features[187] = 1.0
            features[188] = 1.0
        
        return features
    
