"""
Overview: IPAM resolver — automatically allocates IP addresses and subnets from the IPAM system.
Architecture: Resolver implementation for IPAM (Section 11)
Dependencies: app.services.resolver.base, app.services.ipam.ipam_service
Concepts: Wraps the existing IpamService to provide subnet allocation and IP reservation
    as part of the component parameter resolution pipeline.
"""

from __future__ import annotations

import logging
import uuid

from app.services.resolver.base import BaseResolver, ResolverContext

logger = logging.getLogger(__name__)


class IPAMResolver(BaseResolver):
    """Resolves IPAM parameters by allocating subnets or reserving IPs."""

    resolver_type = "ipam"

    async def resolve(
        self,
        params: dict,
        config: dict,
        context: ResolverContext,
    ) -> dict:
        """Resolve IPAM parameters.

        Input params:
            allocation_type: 'subnet' or 'ip'
            prefix_length: int (for subnet)
            parent_scope: str (optional, address space or parent allocation ID)
            ip_version: int (default 4)

        Config:
            address_space_id: UUID of the default address space
            default_allocation_type: 'subnet' or 'ip'

        Returns:
            For subnet: {cidr, gateway, subnet_id}
            For ip: {ip_address, subnet_id}
        """
        from app.services.ipam.ipam_service import IpamService

        ipam = IpamService()
        db = context.db

        allocation_type = params.get("allocation_type", config.get("default_allocation_type", "subnet"))
        address_space_id = params.get("parent_scope") or config.get("address_space_id")

        if not address_space_id:
            raise ValueError("IPAM resolver requires address_space_id in config or parent_scope in params")

        address_space_uuid = uuid.UUID(str(address_space_id))

        if allocation_type == "subnet":
            prefix_length = params.get("prefix_length", 24)
            ip_version = params.get("ip_version", config.get("ip_version", 4))

            # Suggest next available block
            cidr = await ipam.suggest_next_block(
                db, address_space_uuid, prefix_length
            )
            if not cidr:
                raise ValueError(
                    f"No available /{prefix_length} block in address space '{address_space_id}'"
                )

            if context.dry_run:
                # Preview only — suggest CIDR without allocating
                import ipaddress
                network = ipaddress.ip_network(cidr)
                hosts = list(network.hosts())
                gateway = str(hosts[0]) if hosts else str(network.network_address)
                return {
                    "cidr": cidr,
                    "gateway": gateway,
                    "subnet_id": "(preview)",
                }

            # Allocate the block
            from app.models.ipam import AllocationType
            allocation = await ipam.allocate_block(
                db, address_space_uuid,
                name=f"auto-{cidr}",
                cidr=cidr,
                allocation_type=AllocationType.SUBNET,
                purpose="Auto-allocated by IPAM resolver",
            )

            # Calculate gateway (first usable IP)
            import ipaddress
            network = ipaddress.ip_network(cidr)
            hosts = list(network.hosts())
            gateway = str(hosts[0]) if hosts else str(network.network_address)

            return {
                "cidr": cidr,
                "gateway": gateway,
                "subnet_id": str(allocation.id),
            }

        elif allocation_type == "ip":
            # Find a subnet allocation to reserve from
            parent_id = params.get("subnet_id")
            if not parent_id:
                raise ValueError("IP reservation requires subnet_id in params")

            parent_uuid = uuid.UUID(str(parent_id))
            allocation = await ipam.get_allocation(db, parent_uuid)
            if not allocation:
                raise ValueError(f"Subnet allocation '{parent_id}' not found")

            # Find next available IP in the subnet
            import ipaddress
            network = ipaddress.ip_network(allocation.cidr)
            existing = await ipam.list_reservations(db, parent_uuid)
            reserved_ips = {r.ip_address for r in existing}

            next_ip = None
            for host in network.hosts():
                ip_str = str(host)
                if ip_str not in reserved_ips:
                    next_ip = ip_str
                    break

            if not next_ip:
                raise ValueError(f"No available IPs in subnet '{allocation.cidr}'")

            return {
                "ip_address": next_ip,
                "subnet_id": str(parent_uuid),
            }

        else:
            raise ValueError(f"Unknown IPAM allocation type: '{allocation_type}'")

    async def release(
        self,
        allocation_ref: dict,
        config: dict,
        context: ResolverContext,
    ) -> bool:
        """Release an IPAM allocation (mark as RELEASED)."""
        from app.services.ipam.ipam_service import IpamService

        ipam = IpamService()
        db = context.db

        subnet_id = allocation_ref.get("subnet_id")
        if not subnet_id or subnet_id == "(preview)":
            return True

        allocation = await ipam.get_allocation(db, uuid.UUID(str(subnet_id)))
        if allocation:
            from app.models.ipam import AllocationStatus
            allocation.status = AllocationStatus.RELEASED
            await db.flush()

        return True

    async def update(
        self,
        current: dict,
        new_params: dict,
        config: dict,
        context: ResolverContext,
    ) -> dict:
        """Update IPAM allocation: release old, allocate new."""
        await self.release(current, config, context)
        return await self.resolve(new_params, config, context)

    async def validate(
        self,
        params: dict,
        config: dict,
        context: ResolverContext,
    ) -> list[str]:
        """Validate IPAM parameters — check address space capacity."""
        errors: list[str] = []

        address_space_id = params.get("parent_scope") or config.get("address_space_id")
        if not address_space_id:
            errors.append("address_space_id is required in config or parent_scope in params")
            return errors

        from app.services.ipam.ipam_service import IpamService

        ipam = IpamService()
        db = context.db

        try:
            address_space_uuid = uuid.UUID(str(address_space_id))
            allocation_type = params.get("allocation_type", config.get("default_allocation_type", "subnet"))

            if allocation_type == "subnet":
                prefix_length = params.get("prefix_length", 24)
                cidr = await ipam.suggest_next_block(db, address_space_uuid, prefix_length)
                if not cidr:
                    errors.append(f"No available /{prefix_length} block in address space '{address_space_id}'")
        except Exception as e:
            errors.append(str(e))

        return errors
