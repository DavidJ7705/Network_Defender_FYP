import docker
import json
from datetime import datetime

CLAB_PREFIX = "clab-cage4-defense-network-"


class ContainerlabMonitor:
    def __init__(self):
        self.client = docker.from_env()

    def get_network_state(self):
        """Collect complete network state from all containerlab containers."""
        return {
            "timestamp": datetime.now().isoformat(),
            "containers": self._get_containers(),
            "processes": self._get_processes(),
            "connections": self._get_connections(),
        }

    def _get_clab_containers(self):
        """Return only containerlab containers for our topology."""
        return [
            c for c in self.client.containers.list()
            if c.name.startswith(CLAB_PREFIX)
        ]

    def _short_name(self, container):
        """Strip the clab prefix to get the node name."""
        return container.name.removeprefix(CLAB_PREFIX)

    def _get_containers(self):
        """Get running containers with IPs."""
        result = []
        for c in self._get_clab_containers():
            result.append({
                "name": self._short_name(c),
                "full_name": c.name,
                "ip": self._get_container_ip(c),
                "status": c.status,
                "image": c.image.tags[0] if c.image.tags else "unknown",
            })
        return result

    def _get_container_ip(self, container):
        """Extract container IP address."""
        networks = container.attrs["NetworkSettings"]["Networks"]
        for network_info in networks.values():
            if network_info["IPAddress"]:
                return network_info["IPAddress"]
        return None

    def _get_processes(self):
        """Get processes running in each container."""
        result = {}
        for c in self._get_clab_containers():
            name = self._short_name(c)
            try:
                ps_output = c.exec_run("ps aux").output.decode()
                result[name] = self._parse_ps_output(ps_output)
            except Exception as e:
                # Some containers may not have ps
                try:
                    ps_output = c.exec_run("ps").output.decode()
                    result[name] = self._parse_ps_output(ps_output)
                except Exception:
                    result[name] = {"error": str(e)}
        return result

    def _parse_ps_output(self, output):
        """Parse ps aux output into structured data."""
        lines = output.strip().split("\n")
        if not lines:
            return []
        header = lines[0]
        # Find column positions from header
        hdr_lower = header.lower()
        cmd_idx = max(hdr_lower.find("command"), hdr_lower.find("cmd"))
        processes = []
        for line in lines[1:]:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            # Use column position to split command if available
            if cmd_idx > 0 and len(line) > cmd_idx:
                command = line[cmd_idx:].strip()
            else:
                command = " ".join(parts[3:]) if len(parts) > 3 else parts[-1]
            processes.append({
                "pid": parts[0],
                "user": parts[1] if len(parts) > 2 else "unknown",
                "command": command,
            })
        return processes

    def _get_connections(self):
        """Get open ports from each container."""
        result = {}
        for c in self._get_clab_containers():
            name = self._short_name(c)
            try:
                # Try ss first, then netstat
                out = c.exec_run(
                    "sh -c 'ss -tuln 2>/dev/null || netstat -tuln 2>/dev/null'"
                )
                result[name] = self._parse_netstat(out.output.decode())
            except Exception as e:
                result[name] = {"error": str(e)}
        return result

    def _parse_netstat(self, output):
        """Parse ss/netstat output to get open ports."""
        ports = []
        for line in output.split("\n"):
            if "LISTEN" in line or "UNCONN" in line:
                parts = line.split()
                if len(parts) >= 4:
                    local_addr = parts[3] if "LISTEN" in line else parts[4]
                    if ":" in local_addr:
                        port = local_addr.rsplit(":", 1)[-1]
                        if port.isdigit():
                            ports.append(port)
        return list(set(ports))
