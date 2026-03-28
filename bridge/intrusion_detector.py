import docker 

CLAB_PREFIX = "clab-cage4-defense-network-"

class IntrusionDetector:
    def __init__(self):
        self.client = docker.from_env()

    def scan(self, containers):
        print("scanning for compromised markers on hosts")

        results = {}
        for c in containers:
            name = c["clean_name"]
            results[name] = self._check_container(name)
        return results
    
    def _check_container(self, clean_name):
        full_name = CLAB_PREFIX + clean_name
        try:
            container = self.client.containers.get(full_name)
            if container.status != "running":
                return 0
            
            result = container.exec_run("test -f /root/.compromised")
            if result.exit_code == 0:
                print(f"  [IntrusionDetector] {clean_name} - root compromised")
                return 2
            
            results = container.exec_run("test -f /tmp/.compromised")
            if results.exit_code == 0:
                print(f"  [IntrusionDetector] {clean_name} - user compromised")
                return 1
            return 0
        
        except Exception as e:
            print(f"  [IntrusionDetector] could not scan {clean_name}: {e}")
            return 0

    def cleanup_flags(self, containers):
        for c in containers:
            name = c["clean_name"]
            full_name = CLAB_PREFIX + name
            try:
                container = self.client.containers.get(full_name)
                container.exec_run("rm -f /root/.compromised /tmp/.compromised /tmp/junk /tmp/degraded")
            except Exception:
                pass