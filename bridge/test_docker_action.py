"""
Terminal 1 — manually fire a Docker action on a cage4 container.
Shows what action_executor.py will do under the hood.
 
    sudo ~/fyp-venv-linux/bin/python test_docker_action.py
 
Then watch watch_containers.py in Terminal 2 to see the effect.
"""
 
import docker
from action_executor import ActionExecutor, SUBNET_ROUTERS_SORTED
    

PREFIX = "clab-cage4-defense-network-"
client = docker.from_env()
 
# ── List running cage4 containers ────────────────────────────────────────────
 
containers = client.containers.list()
cage4 = [c for c in containers if c.name.startswith(PREFIX)]
 
print("Running cage4 containers:")
for i, c in enumerate(sorted(cage4, key=lambda c: c.name)):
    short = c.name.replace(PREFIX, "")
    print(f"  [{i}] {short}  ({c.status})")
 
# ── Pick a target ─────────────────────────────────────────────────────────────
 
choice = input("\nEnter number to select a container: ").strip()
target = sorted(cage4, key=lambda c: c.name)[int(choice)]
short  = target.name.replace(PREFIX, "")
print(f"\nSelected: {short}")
 
# ── Pick an action ────────────────────────────────────────────────────────────
 
print("\nActions:")
print("  [0] Analyse  — run ps aux inside the container")
print("  [1] Block    — pause the container (Remove)")
print("  [2] Restore  — restart the container")
print("  [3] Unblock  — unpause the container (undo Block)")
print("  [4] Decoy Deploy  — deploy a honeypot container")
print("  [5] Decoy Cleanup  — remove a deployed honeypot container")
print("  [6] Compromise Cleanup  — remove compromise markers from the container")
print("  [7] Allow Traffic  — allow traffic to the subnet router")
print("  [8] Block Traffic  — block traffic to the subnet router")

 
action = input("\nEnter action number: ").strip()
 
# ── Execute ───────────────────────────────────────────────────────────────────
 
if action == "0":
    executor = ActionExecutor()
    result = executor._analyse(PREFIX + short, short)  # Placeholder for decoy deployment logic
    print(result)
 
elif action == "1":
    # Find the management network name directly from the container's own settings.
    target.reload()
    net_names = list(target.attrs["NetworkSettings"]["Networks"].keys())
    print(f"  Container is on networks: {net_names}")
    # Pick the one that looks like the clab management network (starts with 'clab')
    mgmt_network = next((n for n in net_names if n.startswith("clab")), net_names[0])
    print(f"\n[Block] Disconnecting {short} from {mgmt_network} ...")
    net = client.networks.get(mgmt_network)
    net.disconnect(target)
    target.reload()
    print(f"Done. Status: {target.status}")
    print("Management interface removed — ping watcher in Terminal 2 will show NO REPLY.")
 
elif action == "2":
    print(f"\n[Restore] Restarting {short} ...")
    # Check now (before restart) whether the container was blocked.
    target.reload()
    connected_nets = list(target.attrs["NetworkSettings"]["Networks"].keys())
    ref = next(c for c in cage4 if c.name != target.name)
    ref.reload()
    ref_nets = list(ref.attrs["NetworkSettings"]["Networks"].keys())
    mgmt_network = next((n for n in ref_nets if n.startswith("clab")), None)
    was_blocked = mgmt_network and mgmt_network not in connected_nets
    # Restart first — container stays unreachable the whole time.
    target.restart()
    # Only reconnect after restart completes — this is the moment it becomes reachable.
    if was_blocked:
        print(f"  Reconnecting to {mgmt_network} ...")
        client.networks.get(mgmt_network).connect(target)
    target.reload()
    print(f"Done. Status: {target.status}")
    print("Watch Terminal 2: StartedAt timestamp has changed, ping watcher shows REACHABLE.")
 
elif action == "3":
    target.reload()
    already_connected = list(target.attrs["NetworkSettings"]["Networks"].keys())
    ref = cage4[0] if cage4[0].name != target.name else cage4[1]
    ref.reload()
    ref_nets = list(ref.attrs["NetworkSettings"]["Networks"].keys())
    mgmt_network = next((n for n in ref_nets if n.startswith("clab")), ref_nets[0])
    if mgmt_network in already_connected:
        print(f"\n[Unblock] {short} is not blocked — already connected to {mgmt_network}.")
    else:
        print(f"\n[Unblock] Reconnecting {short} to {mgmt_network} ...")
        client.networks.get(mgmt_network).connect(target)
        target.reload()
        print(f"Done. Status: {target.status}")
        print("Management interface restored — ping watcher in Terminal 2 will show REACHABLE.")

elif action == "4":
    executor = ActionExecutor()
    result = executor._deploy_decoy(PREFIX + short, short)  # Placeholder for decoy deployment logic
    print(result)

elif action == "5":
    import subprocess
    yaml_path = f"/tmp/decoy_{short}.yaml"
    result = subprocess.run(["clab", "destroy", "-t", yaml_path], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Decoy for {short} destroyed")
    else:
        print(f"Cleanup failed: {result.stderr}")

elif action == "6":
    print(f"\n[Compromise Cleanup] Removing compromise markers from {short} ...")
    try:
        target.exec_run("rm -f /tmp/.compromised && rm -f /root/.compromised")
        print("Markers removed.")
    except Exception as e:
        print(f"Error during cleanup: {e}")

elif action == "7":
    print("\n Subnet routers (alphabetical order):")
    for i, name in enumerate(SUBNET_ROUTERS_SORTED):
        print(f"[{i}] {name}")
    idx = int(input("\nEnter subnet router number to allow traffic: ").strip())
    executor = ActionExecutor()
    result = executor._allow_traffic(SUBNET_ROUTERS_SORTED[idx])
    print(result)

elif action == "8":
    print("\n Subnet routers (alphabetical order):")
    for i, name in enumerate(SUBNET_ROUTERS_SORTED):
        print(f"[{i}] {name}")
    idx = int(input("\nEnter subnet router number to block traffic: ").strip())
    executor = ActionExecutor()
    result = executor._block_traffic(SUBNET_ROUTERS_SORTED[idx])
    print(result)


else:
    print("Unknown action.")
 
 