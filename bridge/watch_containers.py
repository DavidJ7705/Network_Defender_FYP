
"""
Terminal 2 — live network observer.
Keep this running while you use test_docker_action.py in Terminal 1.

Two modes:

  # Watch container statuses + start times (good for seeing Restore/restart)
  sudo ~/fyp-venv-linux/bin/python watch_containers.py

  # Ping a container by short name — IP is resolved automatically from Docker
  sudo ~/fyp-venv-linux/bin/python watch_containers.py ping office-network-user-0

  # Or pass an IP directly
  sudo ~/fyp-venv-linux/bin/python watch_containers.py ping 172.20.20.5
"""

import sys
import time
import subprocess
import docker

PREFIX = "clab-cage4-defense-network-"

# ── Mode: ping ────────────────────────────────────────────────────────────────

if len(sys.argv) == 3 and sys.argv[1] == "ping":
    raw_arg = sys.argv[2]
    # Resolve a short container name to its current management IP.
    if not raw_arg[0].isdigit():
        _client = docker.from_env()
        _full_name = PREFIX + raw_arg if not raw_arg.startswith(PREFIX) else raw_arg
        try:
            _c = _client.containers.get(_full_name)
            _c.reload()
            _nets = _c.attrs["NetworkSettings"]["Networks"]
            _ip = next((v["IPAddress"] for v in _nets.values() if v["IPAddress"]), None)
            if not _ip:
                print(f"ERROR: {raw_arg} has no management IP — is it already blocked?")
                sys.exit(1)
            target_ip = _ip
            print(f"Resolved {raw_arg} → {target_ip}")
        except Exception as e:
            print(f"ERROR resolving container name: {e}")
            sys.exit(1)
    else:
        target_ip = raw_arg
    print(f"Pinging {target_ip} continuously (Ctrl+C to stop)")
    print("You should see replies stop when you run Block, and resume after Unblock.\n")
    try:
        while True:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "1", target_ip],
                capture_output=True, text=True
            )
            timestamp = time.strftime("%H:%M:%S")
            if result.returncode == 0:
                # Pull the time= value out of the ping output
                line = [l for l in result.stdout.splitlines() if "time=" in l]
                rtt  = line[0].split("time=")[-1] if line else "?"
                print(f"[{timestamp}]  REACHABLE   {target_ip}  rtt={rtt}")
            else:
                print(f"[{timestamp}]  NO REPLY    {target_ip}  ← blocked or down")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped.")
    sys.exit()
 
# ── Mode: status (default) ────────────────────────────────────────────────────
 
client = docker.from_env()
 
print("Watching cage4 containers (Ctrl+C to stop).")
print("StartedAt changes clearly when a container is restarted.\n")
 
try:
    while True:
        containers = client.containers.list(all=True)
        cage4 = sorted(
            [c for c in containers if c.name.startswith(PREFIX)],
            key=lambda c: c.name
        )
 
        print("\033[2J\033[H", end="")  # clear screen
        print(f"{'CONTAINER':<42} {'STATUS':<14} {'STARTED AT'}")
        print("-" * 80)
 
        for c in cage4:
            c.reload()
            short      = c.name.replace(PREFIX, "")
            started_at = c.attrs["State"]["StartedAt"][:19].replace("T", " ")
            status     = c.status
            print(f"{short:<42} {status:<14} {started_at}")
 
        print(f"\nRefreshed at {time.strftime('%H:%M:%S')}  |  {len(cage4)} containers")
        time.sleep(1)
 
except KeyboardInterrupt:
    print("\nStopped.")
 
 