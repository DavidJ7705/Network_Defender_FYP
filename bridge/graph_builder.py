FEATURE_DIM = 192

NODE_TYPES = {
    "SystemNode":0,
    "ConnectionNode":1,
    "FileNode":2,
    "InternetNode":3,
}

NUM_ROUTERS = 9

CONTAINER_ROLES ={
    "admin-ws": ("user", 0),
    "web-server": ("server", 0),
    "database": ("server", 1),
    "public-web": ("server", 2),
    #maybe attacker one too
}

class ObservationGraphBuilder:
    def build_graph(self, network_state):
        raise NotImplementedError

    def encode_host(self, container, role):
        features = [0.0] * FEATURE_DIM

        features[14] = 1.0 #ubuntu
        features[24] = 1.0 #linux

        if role == "server":
            features[56] = 1.0 #server
        else:
            features[55] = 1.0 #user

        if container.get("is_compromised"):
            features[187] = 1.0
            features[188] = 1.0
        
        return features
    
