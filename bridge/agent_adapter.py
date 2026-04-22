# Loads trained GNN-PPO weights and runs a forward pass to select a defensive action (0-80).
#
# Terminal 1 (deploy topology):
#   cd ~/Desktop/Network_Defender_FYP/containerlab-networks
#   sudo containerlab deploy -t cage4-topology.yaml
#
# Terminal 2 (run):
#   cd ~/Desktop/Network_Defender_FYP/bridge
#   sudo ~/fyp-venv-linux/bin/python agent_adapter.py
#
# Cleanup (when done):
#   sudo containerlab destroy -t cage4-topology.yaml
#
# Action masking (optional):
#   AgentAdapter(mask_edge_actions=True) — zeroes edge action probabilities (64-79)
#   before sampling so the agent never picks firewall no-ops unsupported by containerlab.
#   Masking is applied at inference time — trained weights are unchanged.
#   Enabled via --mask flag in evaluation.py. Not used in main.py by default.

import os
import sys
import torch

WEIGHTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "trained-agent", "weights", "gnn_ppo-0.pt"
)
AGENT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "trained-agent")
)

from graph_builder import ObservationGraphBuilder, CONTAINER_ROLES


class AgentAdapter:
    def __init__(self, weights_path=WEIGHTS_PATH, mask_edge_actions=False):
        sys.path.insert(0, AGENT_DIR)
        from models.cage4 import load
        self.agent = load(weights_path)
        self.builder = ObservationGraphBuilder()
        self.mask_edge_actions = mask_edge_actions

    def get_action(self, network_state, phase = 0, host_states = None, compromise_map = None, decoys=None, processes=None):
        # build_graph stores _last_* attributes so ordering is guaranteed consistent
        graph = self.builder.build_graph(
            network_state, 
            compromise_map=compromise_map,
            host_states=host_states,
            decoys=decoys,
            processes=processes
        )
        x     = graph.x
        ei    = graph.edge_index

        servers      = self.builder._last_servers
        users        = self.builder._last_users
        routers      = self.builder._last_routers
        nodes_to_idx = self.builder._last_nodes_to_idx

        # server/user node index tensors for agent attention pooling
        server   = torch.tensor([nodes_to_idx[c["clean_name"]] for c in servers], dtype=torch.long)
        user   = torch.tensor([nodes_to_idx[c["clean_name"]] for c in users],   dtype=torch.long)
        node_server = torch.tensor([len(servers)])
        node_user = torch.tensor([len(users)])

        # action_edges: 8 subnet-router -> internet-router edges [2, 8]
        internet_idx   = nodes_to_idx["internet-router"]
        subnet_routers = sorted(
            [r for r in routers if r["clean_name"] != "internet-router"], 
            key=lambda r: r["clean_name"]
        )
        src = torch.tensor([nodes_to_idx[r["clean_name"]] for r in subnet_routers], dtype=torch.long)
        dst = torch.tensor([internet_idx] * len(subnet_routers), dtype=torch.long)
        action_edges = torch.stack([src, dst])

        # mission phase default: phase 0 (pre-attack) = [1, 0, 0]
        global_vec = torch.zeros(1, 3)
        global_vec[0, phase] = 1.0

        state = (x, ei, global_vec, server, node_server, user, node_user, action_edges, False)

        if self.mask_edge_actions:
            # Zero edge action probs (64-79)
            with torch.no_grad():
                distro = self.agent.actor(*state)
                probs = distro.probs.clone()
                probs[..., 64:80] = 0.0
                probs = probs / probs.sum(-1, keepdim=True)
                action = torch.distributions.Categorical(probs=probs).sample().item()
        else:
            action = self.agent.get_action((state, False))

        return action
