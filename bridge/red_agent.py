import docker

CLAB_PREFIX = "clab-cage4-defense-network-"

ACTION_NAMES = [
    DiscoverRemoteSystems,          #0
    AggressiveServiceDiscovery,     #1
    StealthServiceDiscovery,        #2
    DiscoverDeception,              #3
    ExploitRemoteService,           #4
    PrivilegeEscalate,              #5
    Impact,                         #6
    DegradeServices,                #7
    Withdraw                        #8
]


class RedAgent:
    def __init__(self, containers, decoys = None):
        self.client = docker.from_env()
        self.decoys = {}
