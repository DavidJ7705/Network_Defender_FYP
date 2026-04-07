import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from datetime import datetime
import csv
import sys
import os

from CybORG import CybORG
from CybORG.Agents import SleepAgent, EnterpriseGreenAgent, FiniteStateRedAgent
from CybORG.Simulator.Scenarios import EnterpriseScenarioGenerator


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from submission import Submission

EPISODE_LENGTH = 100
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')

os.makedirs(RESULTS_DIR, exist_ok=True)
run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
csv_path = os.path.join(RESULTS_DIR, f"cyborg_eval_{run_id}.csv")


sg = EnterpriseScenarioGenerator(
    blue_agent_class=SleepAgent,
    green_agent_class=EnterpriseGreenAgent,
    red_agent_class=FiniteStateRedAgent,
    steps=EPISODE_LENGTH,
)
cyborg = CybORG(sg, "sim")
wrapped_cyborg = Submission.wrap(cyborg)
observations, _ = wrapped_cyborg.reset()

FIELDS = ["step", "blue_action_type"]

with open(csv_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()

    for step in range(EPISODE_LENGTH):

        actions = {
            name: agent.get_acitons(observations[name], wrapped_cyborg.get_action_space(name))
            for name, agent in Submission.AGENTS.items()
            if name in wrapped_cyborg.agents
        }


        action_int = actions.get("blue_agent_0")
        if action_int is None or action_int >= 64:
            action_type = "Monitor"
        else:
            action_type = ["Analyse", "Block", "Restore", "DeployDecoy"][action_int // 16]

        observations, _, term, trunc = wrapped_cyborg.step(actions)
                
        writer.writerow({"step": step + 1, "blue_action_type": action_type})
        f.flush()

        done = all(term.get(a, False) or trunc.get(a, False) for a in wrapped.agents)
        if done:
            break