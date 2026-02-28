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

# for i, label in enumerate(ObservationGraph.FEAT_MAP):
#     print(f"[{i}]{label}")

from wrapper.globals import ROUTERS 

WRAPPER_LABELS = [
    "tabular: was_compromised",
    "tabular: was_scanned",
    "message: bit_0",
    "message: bit_1",
    "message: is_received",
]

all_labels = (
    list(ObservationGraph.FEAT_MAP) +   # 0-177
    ROUTERS +                            # 178-186  (subnet one-hot encoding)
    WRAPPER_LABELS                       # 187-191  (graph_wrapper additions)
)

print(f"\nFull feature vector  (0 – {model_input_dimension - 1})\n")
for i, label in enumerate(all_labels):
    print(f"[{i}]  {label}")