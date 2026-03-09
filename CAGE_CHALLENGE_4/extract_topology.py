import sys
import argparse
import json
from gymnasium.utils.seeding import np_random as make_np_random

from CybORG.Simulator.Scenarios.EnterpriseScenarioGenerator import (
    EnterpriseScenarioGenerator,
    SUBNET,
)


def _role(hostname: str) -> str:
    if hostname == "root_internet_host_0":
        return "internet"
    if "_router" in hostname:
        return "router"
    if "_user_host_" in hostname:
        return "user"
    if "_server_host_" in hostname:
        return "server"
    return "unknown"


def extract(seed: int = 42) -> dict:
    rng, _ = make_np_random(seed)
    gen = EnterpriseScenarioGenerator()
    scenario = gen.create_scenario(rng)

    topology = {
        "seed": seed,
        "subnets": {},
        "inter_router_links": [], 
        "inter_server_links": [], 
    }

    for subnet_enum, subnet in scenario.subnets.items():
        subnet_name = subnet_enum.value if hasattr(subnet_enum, "value") else str(subnet_enum)
        nacl_names = [
            s.value if hasattr(s, "value") else str(s)
            for s in subnet.nacls.keys()
        ]
        hosts_info = []
        for hostname in subnet.hosts:
            host = scenario.hosts[hostname]
            ip = str(host.interfaces[0].ip_address) if host.interfaces else None
            hosts_info.append({
                "name": hostname,
                "ip": ip,
                "role": _role(hostname),
            })
        topology["subnets"][subnet_name] = {
            "cidr": str(subnet.cidr),
            "size": subnet.size,
            "nacl_peers": nacl_names,
            "hosts": hosts_info,
        }

    ROUTER_LINKS = {
        "root_internet_host_0": [
            "restricted_zone_a_subnet_router",
            "restricted_zone_b_subnet_router",
            "contractor_network_subnet_router",
            "public_access_zone_subnet_router",
        ],
        "restricted_zone_a_subnet_router":  ["root_internet_host_0", "operational_zone_a_subnet_router"],
        "operational_zone_a_subnet_router": ["restricted_zone_a_subnet_router"],
        "restricted_zone_b_subnet_router":  ["root_internet_host_0", "operational_zone_b_subnet_router"],
        "operational_zone_b_subnet_router": ["restricted_zone_b_subnet_router"],
        "contractor_network_subnet_router": ["root_internet_host_0"],
        "public_access_zone_subnet_router": ["root_internet_host_0", "admin_network_subnet_router", "office_network_subnet_router"],
        "admin_network_subnet_router":      ["public_access_zone_subnet_router"],
        "office_network_subnet_router":     ["public_access_zone_subnet_router"],
    }
    seen = set()
    for src, dsts in ROUTER_LINKS.items():
        for dst in dsts:
            edge = tuple(sorted([src, dst]))
            if edge not in seen:
                topology["inter_router_links"].append({"from": edge[0], "to": edge[1]})
                seen.add(edge)

    SERVER_LINKS = {
        "contractor_network_subnet_server_host_0": [
            "restricted_zone_a_subnet_server_host_0",
            "restricted_zone_b_subnet_server_host_0",
            "public_access_zone_subnet_server_host_0",
        ],
        "restricted_zone_a_subnet_server_host_0":  ["operational_zone_a_subnet_server_host_0", "contractor_network_subnet_server_host_0"],
        "operational_zone_a_subnet_server_host_0": ["restricted_zone_a_subnet_server_host_0"],
        "restricted_zone_b_subnet_server_host_0":  ["operational_zone_b_subnet_server_host_0", "contractor_network_subnet_server_host_0"],
        "operational_zone_b_subnet_server_host_0": ["restricted_zone_b_subnet_server_host_0"],
        "public_access_zone_subnet_server_host_0": ["admin_network_subnet_server_host_0", "office_network_subnet_server_host_0", "contractor_network_subnet_server_host_0"],
        "admin_network_subnet_server_host_0":       ["public_access_zone_subnet_server_host_0"],
        "office_network_subnet_server_host_0":      ["public_access_zone_subnet_server_host_0"],
    }
    for src, dsts in SERVER_LINKS.items():
        for dst in dsts:
            topology["inter_server_links"].append({"from": src, "to": dst})

    return topology


def print_topology(topo: dict):
    print(f"\n{'='*60}")
    print(f"  CybORG CAGE4 Topology  (seed={topo['seed']})")
    print(f"{'='*60}")

    total_hosts = 0
    for sname, sdata in topo["subnets"].items():
        print(f"\n[SUBNET] {sname}  {sdata['cidr']}  (size={sdata['size']})")
        print(f"  NACL peers: {', '.join(sdata['nacl_peers']) or 'none'}")
        for h in sdata["hosts"]:
            print(f"  {h['role']:8s}  {h['name']:50s}  {h['ip']}")
            total_hosts += 1

    print(f"\n[INTER-ROUTER LINKS]  ({len(topo['inter_router_links'])} undirected)")
    for e in topo["inter_router_links"]:
        print(f"  {e['from']}  <->  {e['to']}")

    print(f"\n[INTER-SERVER LINKS]  ({len(topo['inter_server_links'])} directed)")
    for e in topo["inter_server_links"]:
        print(f"  {e['from']}  -->  {e['to']}")

    print(f"\nTotal hosts: {total_hosts}")
    print(f"Total subnets: {len(topo['subnets'])}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--json", action="store_true", help="Dump raw JSON instead of pretty-print")
    args = parser.parse_args()

    topo = extract(args.seed)
    if args.json:
        print(json.dumps(topo, indent=2))
    else:
        print_topology(topo)
