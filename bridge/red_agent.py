import docker
import random
from action_executor import SUBNET_RESTORE_VIA

CLAB_PREFIX = "clab-cage4-defense-network-"

ACTION_NAMES = [
    "DiscoverRemoteSystems",       #0
    "AggressiveServiceDiscovery",  #1
    "StealthServiceDiscovery",     #2
    "DiscoverDeception",           #3
    "ExploitRemoteService",        #4
    "PrivilegeEscalate",           #5
    "Impact",                      #6
    "DegradeServices",             #7
    "Withdraw"                     #8
]


class RedAgent:
    def __init__(self, containers, decoys = None):
        self.client = docker.from_env()
        self.decoys = decoys or {}
        self.host_ips = {c["clean_name"]: c.get("ip") for c in containers}

        self.host_states = {}
        for c in containers:
            self.host_states[c["clean_name"]] = {"state": 'K'}  # K = Known, KD = Known Deception, S = Scanned, SD = Scanned Deception, U = User Access, UD = User Access Deception, R = Root Access, RD = Root Access Deception, F = Failed

        self.state_transitions_success = self._build_success_matrix()
        self.state_transitions_failure = self._build_failure_matrix()
        self.state_transitions_probability    = self._build_probability_matrix()


    def _build_success_matrix(self):
        map = {
            'K'  : ['KD', 'S',  'S',  None, None, None, None, None, None],
            'KD' : ['KD', 'SD', 'SD',  None, None, None, None, None, None],
            'S'  : ['SD', None, None, 'S' , 'U' , None, None, None, None],
            'SD' : ['SD', None, None, 'SD', 'UD', None, None, None, None],
            'U'  : ['UD', None, None, None, None, 'R' , None, None, 'S' ],
            'UD' : ['UD', None, None, None, None, 'RD', None, None, 'SD'],
            'R'  : ['RD', None, None, None, None, None, 'R' , 'R' , 'S' ],
            'RD' : ['RD', None, None, None, None, None, 'RD', 'RD', 'SD'],
            'F'  : ['F',  None, None, None, None, None, None, None, None],
        }
        return map
    
    def _build_failure_matrix(self):
        map = {
            'K'  : ['K' , 'K' , 'K' , None, None, None, None, None, None],
            'KD' : ['KD', 'KD', 'KD', None, None, None, None, None, None],
            'S'  : ['S' , None, None, 'S' , 'S' , None, None, None, None],
            'SD' : ['SD', None, None, 'SD', 'SD', None, None, None, None],
            'U'  : ['U' , None, None, None, None, 'U' , None, None, 'U' ],
            'UD' : ['UD', None, None, None, None, 'UD', None, None, 'UD'],
            'R'  : ['R' , None, None, None, None, None, 'R' , 'R' , 'R' ],
            'RD' : ['RD', None, None, None, None, None, 'RD', 'RD', 'RD'],
            'F'  : ['F',  None, None, None, None, None, None, None, None],
        }
        return map
    
    def _build_probability_matrix(self):    
        map = {
            'K'  : [0.5,  0.25, 0.25, None, None, None, None, None, None],
            'KD' : [None, 0.5,  0.5,  None, None, None, None, None, None],
            'S'  : [0.25, None, None, 0.25, 0.5 , None, None, None, None],
            'SD' : [None, None, None, 0.25, 0.75, None, None, None, None],
            'U'  : [0.5 , None, None, None, None, 0.5 , None, None, 0.0 ],
            'UD' : [None, None, None, None, None, 1.0 , None, None, 0.0 ],
            'R'  : [0.5,  None, None, None, None, None, 0.25, 0.25, 0.0 ],
            'RD' : [None, None, None, None, None, None, 0.5,  0.5,  0.0 ],
        }
        return map

    def _choose_host_and_action(self):
        #filter out the failed hosts
        active = [h for h, v in self.host_states.items() if v["state"] !="F"]
        if not active:
            return None, None
        
        #preference 75% chance of a server target when both types are available
        servers = [h for h in active if "server" in h]
        users = [h for h in active if "server" not in h]
        if servers and users:
            chosen_host = random.choice(servers) if random.random() <= 0.75 else random.choice(users)
        else:
            chosen_host = random.choice(active)

        state = self.host_states[chosen_host]["state"]
        probs  =self.state_transitions_probability.get(state)
        if probs is None:
            return chosen_host, 0 
        
        #Building a valid action list with weights
        options = [(i, p) for i, p in enumerate(probs) if p is not None and p > 0]
        if not options:
            return chosen_host, 0
        
        indices, weights = zip(*options)
        total = sum(weights)
        weights = [w / total for w in weights]
        action_idx = random.choices(indices, weights=weights, k=1)[0]
        return chosen_host,action_idx
    
    
    def _execute_action(self, host, action_idx):

        full_name = CLAB_PREFIX + host
        try:
            container = self.client.containers.get(full_name)
        except Exception as e:
            print(f"Error getting container {full_name}: {e}")
            return False

        action_name = ACTION_NAMES[action_idx]
        print(f"[RED]: {action_name} on {host}")
        
        
        if action_idx == 0: #DiscoverRemoteSystems
            target_ip = random.choice(list(SUBNET_RESTORE_VIA.values()))
            result = container.exec_run(f"ping -c 1 {target_ip}")
            return result.exit_code == 0
        
        elif action_idx == 1: #AggressiveServiceDiscovery
            target_ip = random.choice([ip for ip in self.host_ips.values() if ip])
            container.exec_run(f"nc -zv {target_ip} 22 80 443 3306 8080")
            return True



        elif action_idx == 2: #StealthServiceDiscovery
            target_ip = random.choice([ip for ip in self.host_ips.values() if ip])
            container.exec_run(f"nc -zv {target_ip} 22 80")
            return True

        elif action_idx == 3: #DiscoverDeception
            is_decoy = host in self.decoys
            print(f"[RED]: decoy = {is_decoy}")
            return is_decoy

        elif action_idx == 4: #ExploitRemoteService
            result = container.exec_run("touch /tmp/.compromised") 
            return result.exit_code == 0

        elif action_idx == 5: #PrivilegeEscalate
            result = container.exec_run("touch /root/.compromised") 
            return result.exit_code == 0
        
        elif action_idx == 6: #Impact
            container.exec_run(
                "dd if=/dev/zero of=/tmp/junk bs=1M count=5",
                detach=True
            )
            return True

        elif action_idx == 7: #DegradeServices
            container.exec_run(
                "dd if=/dev/zero of=/tmp/degraded bs=1M count=10",
                detach=True
            )
            return True

            
        elif action_idx == 8: #Withdraw
            container.exec_run(
                "rm -f /tmp/.compormised /root/.compromised /tmp/junk /tmp/degraded"
            )
            return True
        
        return False

    def _transition_state(self, host, action_idx, success):

        curr_state = self.host_states[host]['state']
        matrix = self.state_transitions_success if success \
            else self.state_transitions_failure
        
        row = matrix.get(curr_state)

        if row is None:
            return
        next_state = row[action_idx]
        
        if next_state is not None:
            self.host_states[host]['state'] = next_state
            print(f"[RED] {host} state: {curr_state} > {next_state}")