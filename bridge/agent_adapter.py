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
    def __init__(self, weights_path=WEIGHTS_PATH):
        sys.path.insert(0, AGENT_DIR)
        from models.cage4 import load
        self.agent = load(weights_path)
        self.builder = ObservationGraphBuilder()

    def get_action(self, network_state):
        # build_graph stores _last_* attributes so ordering is guaranteed consistent
        graph = self.builder.build_graph(network_state)
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
        subnet_routers = [r for r in routers if r["clean_name"] != "internet-router"]
        src = torch.tensor([nodes_to_idx[r["clean_name"]] for r in subnet_routers], dtype=torch.long)
        dst = torch.tensor([internet_idx] * len(subnet_routers), dtype=torch.long)
        action_edges = torch.stack([src, dst])

        # mission phase default: phase 0 (pre-attack) = [1, 0, 0]
        global_vec = torch.zeros(1, 3)
        global_vec[0, 1] = 1.0

        state  = (x, ei, global_vec, server, node_server, user, node_user, action_edges, False)
        action = self.agent.get_action((state, False))
        return action