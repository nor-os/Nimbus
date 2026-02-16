"""
Overview: IPAM validation — CIDR overlap detection, containment checking, boundary validation.
Architecture: IPAM validation layer (Section 5)
Dependencies: ipaddress (stdlib)
Concepts: CIDR arithmetic, overlap detection, RFC 1918 validation, subnet boundaries
"""

from __future__ import annotations

import ipaddress
from typing import Union

IPNetwork = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]
IPAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]


def validate_cidr(cidr: str) -> IPNetwork:
    """Parse and validate CIDR notation. Raises ValueError on invalid input."""
    return ipaddress.ip_network(cidr, strict=False)


def validate_cidr_strict(cidr: str) -> IPNetwork:
    """Parse CIDR with strict boundary checking (host bits must be zero)."""
    return ipaddress.ip_network(cidr, strict=True)


def is_contained_in(child_cidr: str, parent_cidr: str) -> bool:
    """Check if child is entirely within parent."""
    child = ipaddress.ip_network(child_cidr, strict=False)
    parent = ipaddress.ip_network(parent_cidr, strict=False)
    return (
        child.network_address >= parent.network_address
        and child.broadcast_address <= parent.broadcast_address
        and child.version == parent.version
    )


def overlaps_with(cidr_a: str, cidr_b: str) -> bool:
    """Check if two CIDRs overlap."""
    net_a = ipaddress.ip_network(cidr_a, strict=False)
    net_b = ipaddress.ip_network(cidr_b, strict=False)
    return net_a.overlaps(net_b)


def find_overlaps(new_cidr: str, existing_cidrs: list[str]) -> list[str]:
    """Return all existing CIDRs that overlap with new_cidr."""
    new_net = ipaddress.ip_network(new_cidr, strict=False)
    return [c for c in existing_cidrs if ipaddress.ip_network(c, strict=False).overlaps(new_net)]


def validate_subnet_boundary(cidr: str) -> bool:
    """Check CIDR is on a proper network boundary (host bits are zero)."""
    try:
        ipaddress.ip_network(cidr, strict=True)
        return True
    except ValueError:
        return False


def is_private_range(cidr: str) -> bool:
    """Check if CIDR falls within RFC 1918 (IPv4) or RFC 4193 (IPv6) private ranges."""
    net = ipaddress.ip_network(cidr, strict=False)
    if net.version == 4:
        private_ranges = [
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("192.168.0.0/16"),
        ]
    else:
        private_ranges = [
            ipaddress.ip_network("fc00::/7"),
        ]
    return any(
        net.network_address >= pr.network_address
        and net.broadcast_address <= pr.broadcast_address
        for pr in private_ranges
    )


def calculate_usable_ips(cidr: str) -> int:
    """Total usable IPs in a CIDR (excludes network and broadcast for IPv4 /31+)."""
    net = ipaddress.ip_network(cidr, strict=False)
    total = net.num_addresses
    if net.version == 4:
        if net.prefixlen == 32:
            return 1
        if net.prefixlen == 31:
            return 2
        # Subtract network address and broadcast address
        return max(total - 2, 0)
    # IPv6: all addresses usable
    return total


def next_available_block(
    parent_cidr: str,
    existing_children: list[str],
    prefix_length: int,
) -> str | None:
    """Find next available CIDR of given prefix_length within parent that doesn't overlap existing.

    Returns the CIDR string of the first available block, or None if no space available.
    """
    parent = ipaddress.ip_network(parent_cidr, strict=False)
    if prefix_length < parent.prefixlen:
        return None  # Requested block is larger than parent

    existing_nets = [ipaddress.ip_network(c, strict=False) for c in existing_children]

    # Iterate through all possible subnets of the requested size within the parent
    for candidate in parent.subnets(new_prefix=prefix_length):
        conflict = False
        for existing in existing_nets:
            if candidate.overlaps(existing):
                conflict = True
                break
        if not conflict:
            return str(candidate)

    return None


def ip_in_cidr(ip: str, cidr: str) -> bool:
    """Check if an IP address falls within a CIDR block."""
    addr = ipaddress.ip_address(ip)
    net = ipaddress.ip_network(cidr, strict=False)
    return addr in net


def split_cidr(cidr: str, new_prefix: int) -> list[str]:
    """Split a CIDR block into smaller blocks of the given prefix length."""
    net = ipaddress.ip_network(cidr, strict=False)
    if new_prefix <= net.prefixlen:
        return [str(net)]
    return [str(s) for s in net.subnets(new_prefix=new_prefix)]


def cidr_summary(cidr: str) -> dict:
    """Return summary info about a CIDR block."""
    net = ipaddress.ip_network(cidr, strict=False)
    return {
        "network": str(net.network_address),
        "broadcast": str(net.broadcast_address),
        "prefix_length": net.prefixlen,
        "total_addresses": net.num_addresses,
        "usable_addresses": calculate_usable_ips(cidr),
        "ip_version": net.version,
        "is_private": is_private_range(cidr),
    }
