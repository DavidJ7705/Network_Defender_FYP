import torch
import os
import sys
from wrapper.observation_graph import ObservationGraph


WEIGHTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "trained-agent", "weights", "gnn_ppo-0.pt"
)

data = torch.load(WEIGHTS_PATH, map_location="cpu", weights_only=False)
args, kwargs = data["agent"]

model_input_dimension = args[0]

print(f"Agent constructor args: {args}")
print(f"Agent constructor kwargs: {list(kwargs.keys())}")
print(f"\ninput_dimension = {model_input_dimension}")

#seeing where the 192 comes from 
graph_dim = ObservationGraph.DIM
print(f"ObservationGraph.DIM = {graph_dim}")


difference = model_input_dimension - graph_dim
print(f"Extra features added: {difference}")
print("+5 comes from:\n +2 -> Tabular host feature (compromised, scanned)\n +3 -> Message features (2 message bits + is_received flag)")