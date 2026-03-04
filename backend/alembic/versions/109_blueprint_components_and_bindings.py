"""
Overview: Seed system components for all 12 stack blueprints, then populate
    stack_blueprint_components and stack_variable_bindings so the blueprint
    detail UI shows composition and wiring.
Architecture: Alembic data migration for blueprint composition (Section 8)
Dependencies: alembic, sqlalchemy
Concepts: Each blueprint slot maps to a reusable system Component (IaC building
    block). Variable bindings wire blueprint inputs → component parameters and
    component outputs → blueprint outputs.

Revision ID: 109
Revises: 108
"""

import json

from alembic import op
import sqlalchemy as sa

revision = "109"
down_revision = "108"
branch_labels = None
depends_on = None


# ── System Component Definitions ────────────────────────────────────────
# Each component maps to a semantic_resource_type and uses the first
# available provider (proxmox).  Code is a placeholder — real IaC is
# added when the Proxmox provider (Phase 11) or cloud providers (Phase 18)
# are implemented.

COMPONENTS = [
    # ── Database ──
    {"name": "postgresql-server", "display": "PostgreSQL Server", "desc": "PostgreSQL database server with streaming replication support", "stype": "RelationalDatabase", "lang": "PYTHON"},
    {"name": "pgbouncer-pooler", "display": "PgBouncer Connection Pooler", "desc": "PgBouncer connection pooling proxy for PostgreSQL", "stype": "Container", "lang": "PYTHON"},
    {"name": "patroni-manager", "display": "Patroni Failover Manager", "desc": "Patroni HA manager with DCS-backed leader election", "stype": "Container", "lang": "PYTHON"},
    {"name": "redis-server", "display": "Redis Server", "desc": "Redis in-memory data store with RDB/AOF persistence", "stype": "CacheService", "lang": "PYTHON"},
    {"name": "redis-sentinel-node", "display": "Redis Sentinel", "desc": "Redis Sentinel for automatic failover and service discovery", "stype": "Container", "lang": "PYTHON"},
    {"name": "mongodb-server", "display": "MongoDB Server", "desc": "MongoDB replica set member with WiredTiger engine", "stype": "NoSQLDatabase", "lang": "PYTHON"},
    {"name": "mongos-router", "display": "Mongos Router", "desc": "MongoDB query router for sharded clusters", "stype": "Container", "lang": "PYTHON"},
    {"name": "mongodb-config-srv", "display": "MongoDB Config Server", "desc": "MongoDB config server for sharded cluster metadata", "stype": "Container", "lang": "PYTHON"},
    # ── Platform ──
    {"name": "k8s-control-plane", "display": "Kubernetes Control Plane", "desc": "Kubernetes control plane node (API server, etcd, scheduler, controller-manager)", "stype": "VirtualMachine", "lang": "PYTHON"},
    {"name": "k8s-worker-node", "display": "Kubernetes Worker Node", "desc": "Kubernetes worker node for running pods", "stype": "VirtualMachine", "lang": "PYTHON"},
    {"name": "ingress-controller", "display": "Ingress Controller", "desc": "Kubernetes ingress controller (Nginx/Envoy) for L7 routing", "stype": "LoadBalancer", "lang": "PYTHON"},
    {"name": "cert-manager", "display": "Cert-Manager", "desc": "Kubernetes certificate manager for automated TLS issuance", "stype": "Container", "lang": "PYTHON"},
    {"name": "velero-backup", "display": "Velero Backup Operator", "desc": "Velero for Kubernetes cluster backup and disaster recovery", "stype": "Container", "lang": "PYTHON"},
    {"name": "kafka-broker", "display": "Kafka Broker", "desc": "Apache Kafka broker with KRaft consensus", "stype": "Container", "lang": "PYTHON"},
    {"name": "schema-registry", "display": "Schema Registry", "desc": "Confluent Schema Registry for Kafka message validation", "stype": "Container", "lang": "PYTHON"},
    {"name": "kafka-connect-worker", "display": "Kafka Connect Worker", "desc": "Kafka Connect distributed worker for source/sink connectors", "stype": "Container", "lang": "PYTHON"},
    {"name": "kafka-mirror-maker", "display": "MirrorMaker 2", "desc": "Kafka MirrorMaker 2 for cross-cluster replication", "stype": "Container", "lang": "PYTHON"},
    {"name": "rabbitmq-node", "display": "RabbitMQ Node", "desc": "RabbitMQ cluster node with quorum queue support", "stype": "Container", "lang": "PYTHON"},
    # ── Compute ──
    {"name": "app-container", "display": "Application Container", "desc": "Generic application container with health checks and auto-scaling", "stype": "Container", "lang": "PYTHON"},
    # ── Shared ──
    {"name": "backup-agent", "display": "Backup Agent", "desc": "Backup agent for scheduled snapshots and WAL/oplog archival", "stype": "Container", "lang": "PYTHON"},
    {"name": "load-balancer", "display": "Load Balancer", "desc": "L4/L7 load balancer with health checking and connection draining", "stype": "LoadBalancer", "lang": "PYTHON"},
    {"name": "tls-termination", "display": "TLS Termination", "desc": "TLS termination endpoint with certificate management", "stype": "Certificate", "lang": "PYTHON"},
    {"name": "health-check-probe", "display": "Health Check Probe", "desc": "Active health check probe for service liveness and readiness", "stype": "Container", "lang": "PYTHON"},
    # ── Storage ──
    {"name": "minio-node", "display": "MinIO Node", "desc": "MinIO distributed object storage node with erasure coding", "stype": "ObjectStorage", "lang": "PYTHON"},
    # ── Monitoring ──
    {"name": "prometheus-server", "display": "Prometheus Server", "desc": "Prometheus time-series database and scraper", "stype": "Container", "lang": "PYTHON"},
    {"name": "alertmanager-cluster", "display": "Alertmanager", "desc": "Prometheus Alertmanager with gossip clustering", "stype": "Container", "lang": "PYTHON"},
    {"name": "grafana-server", "display": "Grafana", "desc": "Grafana dashboard and visualization platform", "stype": "Dashboard", "lang": "PYTHON"},
    {"name": "thanos-sidecar", "display": "Thanos Sidecar", "desc": "Thanos sidecar for Prometheus HA deduplication", "stype": "Container", "lang": "PYTHON"},
    {"name": "thanos-store-gw", "display": "Thanos Store Gateway", "desc": "Thanos Store Gateway for long-term metric retention", "stype": "Container", "lang": "PYTHON"},
    {"name": "node-exporter", "display": "Node Exporter", "desc": "Prometheus Node Exporter for host-level metrics", "stype": "Container", "lang": "PYTHON"},
    {"name": "loki-writer", "display": "Loki Write Path", "desc": "Grafana Loki write path (distributor + ingester)", "stype": "Container", "lang": "PYTHON"},
    {"name": "loki-reader", "display": "Loki Read Path", "desc": "Grafana Loki read path (querier + query-frontend)", "stype": "Container", "lang": "PYTHON"},
    {"name": "log-shipper", "display": "Log Shipper", "desc": "Log collection agent (Promtail/Fluentd/Fluent Bit)", "stype": "Container", "lang": "PYTHON"},
    # ── Networking ──
    {"name": "vpn-gateway-node", "display": "VPN Gateway", "desc": "WireGuard/IPSec VPN gateway with tunnel management", "stype": "VPNGateway", "lang": "PYTHON"},
    {"name": "firewall-rules", "display": "Firewall Rules", "desc": "Stateful firewall ruleset with logging", "stype": "SecurityGroup", "lang": "PYTHON"},
    {"name": "dns-resolver", "display": "DNS Resolver", "desc": "DNS resolver/forwarder with caching and split-horizon", "stype": "DNS", "lang": "PYTHON"},
    # ── Security ──
    {"name": "reverse-proxy", "display": "Reverse Proxy", "desc": "HAProxy/Nginx/Envoy reverse proxy with connection pooling", "stype": "LoadBalancer", "lang": "PYTHON"},
    {"name": "waf-engine", "display": "WAF Engine", "desc": "ModSecurity/Coraza web application firewall", "stype": "Container", "lang": "PYTHON"},
    {"name": "rate-limiter", "display": "Rate Limiter", "desc": "Token bucket rate limiter with ban escalation", "stype": "Container", "lang": "PYTHON"},
]

PLACEHOLDER_CODE = """# Placeholder — real IaC implementation added when provider integration is complete.
# See: plan/phases/ for provider implementation roadmap.
import pulumi
pulumi.export("status", "placeholder")
"""

# ── Blueprint → Component Mappings ──────────────────────────────────────
# Maps blueprint_name → list of (node_id, component_name, label, sort_order, is_optional, default_params, depends_on)

BLUEPRINT_COMPONENTS = {
    "postgresql-ha": [
        ("primary", "postgresql-server", "Primary Node", 0, False, {"role": "primary"}, None),
        ("replica", "postgresql-server", "Streaming Replica", 1, False, {"role": "replica", "read_only": True}, ["primary"]),
        ("pgbouncer", "pgbouncer-pooler", "PgBouncer Pooler", 2, False, None, ["primary"]),
        ("patroni", "patroni-manager", "Patroni (Failover Manager)", 3, False, None, ["primary", "replica"]),
        ("backup_agent", "backup-agent", "WAL-G Backup Agent", 4, False, {"engine": "wal-g", "compression": "lz4"}, ["primary"]),
        ("dr_replica", "postgresql-server", "DR Async Replica", 5, True, {"role": "dr_replica", "async_replication": True}, ["primary"]),
    ],
    "redis-sentinel": [
        ("primary", "redis-server", "Redis Primary", 0, False, {"role": "primary"}, None),
        ("replica", "redis-server", "Redis Replica", 1, False, {"role": "replica", "replica_read_only": True}, ["primary"]),
        ("sentinel", "redis-sentinel-node", "Sentinel Node", 2, False, None, ["primary", "replica"]),
        ("dr_replica", "redis-server", "DR Cross-Region Replica", 3, True, {"role": "dr_replica", "async_replication": True}, ["primary"]),
    ],
    "mongodb-replicaset": [
        ("member", "mongodb-server", "Replica Set Member", 0, False, {"role": "member"}, None),
        ("mongos", "mongos-router", "Mongos Router", 1, True, None, ["member", "config_server"]),
        ("config_server", "mongodb-config-srv", "Config Server", 2, True, None, None),
        ("backup_agent", "backup-agent", "Backup Agent", 3, False, {"engine": "mongodump", "compression": "gzip"}, ["member"]),
        ("dr_secondary", "mongodb-server", "DR Cross-Site Secondary", 4, True, {"role": "dr_secondary", "priority": 0, "votes": 0}, ["member"]),
    ],
    "kubernetes-app-platform": [
        ("control_plane", "k8s-control-plane", "Control Plane Node", 0, False, None, None),
        ("worker", "k8s-worker-node", "Worker Node", 1, False, None, ["control_plane"]),
        ("ingress", "ingress-controller", "Ingress Controller", 2, False, None, ["control_plane", "worker"]),
        ("cert_manager", "cert-manager", "Cert-Manager", 3, False, None, ["control_plane"]),
        ("velero", "velero-backup", "Velero Backup", 4, False, None, ["control_plane"]),
        ("dr_cluster", "k8s-control-plane", "DR Standby Cluster", 5, True, {"role": "dr_standby"}, None),
    ],
    "container-web-service": [
        ("container", "app-container", "App Container", 0, False, None, None),
        ("load_balancer", "load-balancer", "Load Balancer", 1, False, None, ["container"]),
        ("tls", "tls-termination", "TLS Termination", 2, False, None, ["load_balancer"]),
        ("health_check", "health-check-probe", "Health Check Probe", 3, False, None, ["container"]),
        ("dr_region", "app-container", "DR Region Deployment", 4, True, {"role": "dr_region"}, None),
    ],
    "kafka-cluster": [
        ("broker", "kafka-broker", "Kafka Broker", 0, False, None, None),
        ("schema_registry", "schema-registry", "Schema Registry", 1, True, None, ["broker"]),
        ("connect", "kafka-connect-worker", "Kafka Connect Worker", 2, True, None, ["broker"]),
        ("mirror_maker", "kafka-mirror-maker", "MirrorMaker 2 (DR)", 3, True, None, ["broker"]),
    ],
    "rabbitmq-cluster": [
        ("node", "rabbitmq-node", "RabbitMQ Node", 0, False, None, None),
        ("haproxy", "load-balancer", "HAProxy LB", 1, False, {"engine": "haproxy"}, ["node"]),
        ("dr_shovel", "rabbitmq-node", "DR Shovel Endpoint", 2, True, {"role": "dr_shovel"}, ["node"]),
    ],
    "minio-distributed": [
        ("node", "minio-node", "MinIO Node", 0, False, None, None),
        ("load_balancer", "load-balancer", "Load Balancer", 1, False, None, ["node"]),
        ("dr_site", "minio-node", "DR Replication Target", 2, True, {"role": "dr_site"}, None),
    ],
    "monitoring-stack": [
        ("prometheus", "prometheus-server", "Prometheus Server", 0, False, None, None),
        ("alertmanager", "alertmanager-cluster", "Alertmanager", 1, False, None, ["prometheus"]),
        ("grafana", "grafana-server", "Grafana", 2, False, None, ["prometheus"]),
        ("thanos_sidecar", "thanos-sidecar", "Thanos Sidecar", 3, True, None, ["prometheus"]),
        ("thanos_store", "thanos-store-gw", "Thanos Store Gateway", 4, True, None, ["thanos_sidecar"]),
        ("node_exporter", "node-exporter", "Node Exporter", 5, False, None, None),
    ],
    "log-aggregation": [
        ("loki_write", "loki-writer", "Loki Write Path", 0, False, None, None),
        ("loki_read", "loki-reader", "Loki Read Path", 1, False, None, ["loki_write"]),
        ("log_shipper", "log-shipper", "Log Shipper (DaemonSet)", 2, False, None, None),
        ("grafana", "grafana-server", "Grafana", 3, False, None, ["loki_read"]),
        ("dr_forwarder", "log-shipper", "DR Log Forwarder", 4, True, {"role": "dr_forwarder"}, ["log_shipper"]),
    ],
    "vpn-gateway": [
        ("gateway_primary", "vpn-gateway-node", "VPN Gateway (Active)", 0, False, {"role": "active"}, None),
        ("gateway_standby", "vpn-gateway-node", "VPN Gateway (Standby)", 1, True, {"role": "standby"}, ["gateway_primary"]),
        ("firewall", "firewall-rules", "Firewall Rules", 2, False, None, ["gateway_primary"]),
        ("dns", "dns-resolver", "DNS Resolver", 3, False, None, ["gateway_primary"]),
        ("dr_gateway", "vpn-gateway-node", "DR Standby Gateway", 4, True, {"role": "dr_standby"}, None),
    ],
    "reverse-proxy-waf": [
        ("proxy", "reverse-proxy", "Reverse Proxy", 0, False, None, None),
        ("waf", "waf-engine", "WAF Engine", 1, False, None, ["proxy"]),
        ("rate_limiter", "rate-limiter", "Rate Limiter", 2, False, None, ["proxy"]),
        ("gslb", "reverse-proxy", "GSLB Controller", 3, True, {"role": "gslb"}, None),
    ],
}

# ── Variable Bindings ───────────────────────────────────────────────────
# Maps blueprint_name → list of (direction, variable_name, target_node_id, target_parameter, transform_expr)

VARIABLE_BINDINGS = {
    "postgresql-ha": [
        # INPUT bindings
        ("INPUT", "instance_size", "primary", "instance_size", None),
        ("INPUT", "instance_size", "replica", "instance_size", None),
        ("INPUT", "replicas", "replica", "replica_count", None),
        ("INPUT", "storage_gb", "primary", "storage_gb", None),
        ("INPUT", "storage_gb", "replica", "storage_gb", None),
        ("INPUT", "pg_version", "primary", "pg_version", None),
        ("INPUT", "pg_version", "replica", "pg_version", None),
        ("INPUT", "enable_dr_replica", "dr_replica", "enabled", None),
        ("INPUT", "dr_region", "dr_replica", "region", None),
        ("INPUT", "backup_retention_days", "backup_agent", "retention_full", None),
        ("INPUT", "max_connections", "pgbouncer", "max_client_conn", None),
        # OUTPUT bindings
        ("OUTPUT", "connection_string", "pgbouncer", "connection_string", None),
        ("OUTPUT", "primary_host", "primary", "host", None),
        ("OUTPUT", "replica_hosts", "replica", "hosts", None),
        ("OUTPUT", "pgbouncer_host", "pgbouncer", "host", None),
        ("OUTPUT", "dr_replica_host", "dr_replica", "host", None),
    ],
    "redis-sentinel": [
        ("INPUT", "instance_size", "primary", "instance_size", None),
        ("INPUT", "instance_size", "replica", "instance_size", None),
        ("INPUT", "maxmemory_gb", "primary", "maxmemory_gb", None),
        ("INPUT", "maxmemory_gb", "replica", "maxmemory_gb", None),
        ("INPUT", "persistence", "primary", "persistence", None),
        ("INPUT", "sentinel_quorum", "sentinel", "quorum", None),
        ("INPUT", "enable_dr", "dr_replica", "enabled", None),
        ("OUTPUT", "sentinel_addresses", "sentinel", "addresses", None),
        ("OUTPUT", "master_name", "primary", "master_name", None),
        ("OUTPUT", "connection_string", "primary", "connection_string", None),
    ],
    "mongodb-replicaset": [
        ("INPUT", "instance_size", "member", "instance_size", None),
        ("INPUT", "storage_gb", "member", "storage_gb", None),
        ("INPUT", "mongo_version", "member", "mongo_version", None),
        ("INPUT", "replica_members", "member", "replica_count", None),
        ("INPUT", "enable_sharding", "mongos", "enabled", None),
        ("INPUT", "enable_sharding", "config_server", "enabled", None),
        ("INPUT", "enable_dr_secondary", "dr_secondary", "enabled", None),
        ("INPUT", "dr_region", "dr_secondary", "region", None),
        ("OUTPUT", "connection_string", "member", "connection_string", None),
        ("OUTPUT", "replica_set_name", "member", "replica_set_name", None),
        ("OUTPUT", "member_hosts", "member", "hosts", None),
    ],
    "kubernetes-app-platform": [
        ("INPUT", "k8s_version", "control_plane", "k8s_version", None),
        ("INPUT", "k8s_version", "worker", "k8s_version", None),
        ("INPUT", "control_plane_nodes", "control_plane", "replica_count", None),
        ("INPUT", "worker_node_size", "worker", "instance_size", None),
        ("INPUT", "worker_min_count", "worker", "min_count", None),
        ("INPUT", "worker_max_count", "worker", "max_count", None),
        ("INPUT", "cni_plugin", "worker", "cni_plugin", None),
        ("INPUT", "enable_dr_cluster", "dr_cluster", "enabled", None),
        ("INPUT", "dr_region", "dr_cluster", "region", None),
        ("INPUT", "storage_class", "worker", "storage_class", None),
        ("OUTPUT", "api_server_endpoint", "control_plane", "api_endpoint", None),
        ("OUTPUT", "kubeconfig_secret", "control_plane", "kubeconfig_secret", None),
        ("OUTPUT", "ingress_lb_ip", "ingress", "lb_ip", None),
        ("OUTPUT", "dr_api_server_endpoint", "dr_cluster", "api_endpoint", None),
    ],
    "container-web-service": [
        ("INPUT", "container_image", "container", "image", None),
        ("INPUT", "replicas", "container", "replicas", None),
        ("INPUT", "cpu_limit", "container", "cpu_limit", None),
        ("INPUT", "memory_limit_mb", "container", "memory_limit_mb", None),
        ("INPUT", "port", "container", "port", None),
        ("INPUT", "health_check_path", "health_check", "path", None),
        ("INPUT", "health_check_path", "container", "health_check_path", None),
        ("INPUT", "enable_tls", "tls", "enabled", None),
        ("INPUT", "enable_dr_region", "dr_region", "enabled", None),
        ("INPUT", "dr_region", "dr_region", "region", None),
        ("OUTPUT", "service_url", "load_balancer", "service_url", None),
        ("OUTPUT", "lb_address", "load_balancer", "address", None),
        ("OUTPUT", "dr_service_url", "dr_region", "service_url", None),
    ],
    "kafka-cluster": [
        ("INPUT", "broker_count", "broker", "replica_count", None),
        ("INPUT", "instance_size", "broker", "instance_size", None),
        ("INPUT", "storage_gb_per_broker", "broker", "storage_gb", None),
        ("INPUT", "replication_factor", "broker", "replication_factor", None),
        ("INPUT", "min_insync_replicas", "broker", "min_insync_replicas", None),
        ("INPUT", "enable_schema_registry", "schema_registry", "enabled", None),
        ("INPUT", "enable_dr_mirror", "mirror_maker", "enabled", None),
        ("INPUT", "dr_region", "mirror_maker", "target_region", None),
        ("OUTPUT", "bootstrap_servers", "broker", "bootstrap_servers", None),
        ("OUTPUT", "schema_registry_url", "schema_registry", "url", None),
        ("OUTPUT", "dr_bootstrap_servers", "mirror_maker", "target_bootstrap_servers", None),
    ],
    "rabbitmq-cluster": [
        ("INPUT", "node_count", "node", "replica_count", None),
        ("INPUT", "instance_size", "node", "instance_size", None),
        ("INPUT", "queue_type", "node", "queue_type", None),
        ("INPUT", "enable_management_ui", "node", "management_enabled", None),
        ("INPUT", "enable_dr_shovel", "dr_shovel", "enabled", None),
        ("INPUT", "dr_region", "dr_shovel", "target_region", None),
        ("OUTPUT", "amqp_url", "node", "amqp_url", None),
        ("OUTPUT", "management_url", "node", "management_url", None),
        ("OUTPUT", "dr_amqp_url", "dr_shovel", "amqp_url", None),
    ],
    "minio-distributed": [
        ("INPUT", "node_count", "node", "replica_count", None),
        ("INPUT", "disks_per_node", "node", "disks_per_node", None),
        ("INPUT", "disk_size_gb", "node", "disk_size_gb", None),
        ("INPUT", "erasure_coding", "node", "erasure_coding", None),
        ("INPUT", "enable_tls", "load_balancer", "tls_enabled", None),
        ("INPUT", "enable_site_replication", "dr_site", "enabled", None),
        ("INPUT", "dr_site_endpoint", "dr_site", "endpoint", None),
        ("OUTPUT", "api_endpoint", "load_balancer", "api_endpoint", None),
        ("OUTPUT", "console_endpoint", "load_balancer", "console_endpoint", None),
        ("OUTPUT", "access_key", "node", "access_key", None),
        ("OUTPUT", "secret_key", "node", "secret_key", None),
    ],
    "monitoring-stack": [
        ("INPUT", "retention_days", "prometheus", "retention_days", None),
        ("INPUT", "scrape_interval_seconds", "prometheus", "scrape_interval", None),
        ("INPUT", "alertmanager_nodes", "alertmanager", "replica_count", None),
        ("INPUT", "enable_thanos", "thanos_sidecar", "enabled", None),
        ("INPUT", "enable_thanos", "thanos_store", "enabled", None),
        ("INPUT", "thanos_object_store", "thanos_store", "object_store", None),
        ("INPUT", "grafana_replicas", "grafana", "replica_count", None),
        ("OUTPUT", "prometheus_url", "prometheus", "url", None),
        ("OUTPUT", "grafana_url", "grafana", "url", None),
        ("OUTPUT", "alertmanager_url", "alertmanager", "url", None),
        ("OUTPUT", "thanos_query_url", "thanos_sidecar", "query_url", None),
    ],
    "log-aggregation": [
        ("INPUT", "retention_days", "loki_write", "retention_days", None),
        ("INPUT", "replication_factor", "loki_write", "replication_factor", None),
        ("INPUT", "log_shipper", "log_shipper", "engine", None),
        ("INPUT", "object_store", "loki_write", "object_store", None),
        ("INPUT", "enable_dr_shipping", "dr_forwarder", "enabled", None),
        ("OUTPUT", "loki_push_url", "loki_write", "push_url", None),
        ("OUTPUT", "grafana_url", "grafana", "url", None),
    ],
    "vpn-gateway": [
        ("INPUT", "vpn_protocol", "gateway_primary", "protocol", None),
        ("INPUT", "vpn_protocol", "gateway_standby", "protocol", None),
        ("INPUT", "tunnel_cidr", "gateway_primary", "tunnel_cidr", None),
        ("INPUT", "max_clients", "gateway_primary", "max_clients", None),
        ("INPUT", "enable_ha_pair", "gateway_standby", "enabled", None),
        ("INPUT", "enable_dr_standby", "dr_gateway", "enabled", None),
        ("INPUT", "dr_site", "dr_gateway", "site", None),
        ("OUTPUT", "gateway_endpoint", "gateway_primary", "endpoint", None),
        ("OUTPUT", "client_config_secret", "gateway_primary", "client_config_secret", None),
        ("OUTPUT", "dr_gateway_endpoint", "dr_gateway", "endpoint", None),
    ],
    "reverse-proxy-waf": [
        ("INPUT", "proxy_engine", "proxy", "engine", None),
        ("INPUT", "waf_engine", "waf", "engine", None),
        ("INPUT", "max_rps", "rate_limiter", "max_rps", None),
        ("INPUT", "ssl_policy", "proxy", "ssl_policy", None),
        ("INPUT", "enable_gslb", "gslb", "enabled", None),
        ("INPUT", "regions", "gslb", "regions", None),
        ("OUTPUT", "proxy_vip", "proxy", "vip", None),
        ("OUTPUT", "gslb_fqdn", "gslb", "fqdn", None),
        ("OUTPUT", "waf_dashboard_url", "waf", "dashboard_url", None),
    ],
}


def upgrade() -> None:
    conn = op.get_bind()

    # ── Prerequisites ───────────────────────────────────────────────
    user = conn.execute(sa.text(
        "SELECT id FROM users ORDER BY created_at ASC LIMIT 1"
    )).fetchone()
    if not user:
        return  # No user yet — seed_demo will handle later

    user_id = str(user[0])

    # Provider lookup
    provider = conn.execute(sa.text(
        "SELECT id FROM semantic_providers WHERE name = 'proxmox' AND deleted_at IS NULL LIMIT 1"
    )).fetchone()
    if not provider:
        return
    provider_id = str(provider[0])

    # Semantic type lookup
    stype_map = {}
    for row in conn.execute(sa.text(
        "SELECT name, id FROM semantic_resource_types WHERE deleted_at IS NULL"
    )):
        stype_map[row[0]] = str(row[1])

    # ── 1. Create system components ─────────────────────────────────
    comp_id_map = {}  # name → uuid

    for comp in COMPONENTS:
        stype_id = stype_map.get(comp["stype"])
        if not stype_id:
            continue

        # Check if already exists
        existing = conn.execute(sa.text(
            "SELECT id FROM components WHERE name = :name AND is_system = true AND deleted_at IS NULL LIMIT 1"
        ), {"name": comp["name"]}).fetchone()

        if existing:
            comp_id_map[comp["name"]] = str(existing[0])
            continue

        conn.execute(sa.text("""
            INSERT INTO components (
                id, tenant_id, provider_id, semantic_type_id,
                name, display_name, description, language,
                code, version, is_published, is_system,
                created_by, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), NULL, CAST(:provider_id AS uuid), CAST(:stype_id AS uuid),
                :name, :display_name, :description, :language,
                :code, 1, true, true,
                CAST(:user_id AS uuid), NOW(), NOW()
            )
        """), {
            "provider_id": provider_id,
            "stype_id": stype_id,
            "name": comp["name"],
            "display_name": comp["display"],
            "description": comp["desc"],
            "language": comp["lang"],
            "code": PLACEHOLDER_CODE,
            "user_id": user_id,
        })

        row = conn.execute(sa.text(
            "SELECT id FROM components WHERE name = :name AND is_system = true AND deleted_at IS NULL LIMIT 1"
        ), {"name": comp["name"]}).fetchone()
        if row:
            comp_id_map[comp["name"]] = str(row[0])

    # ── 2. Populate blueprint components ────────────────────────────
    blueprints = conn.execute(sa.text(
        "SELECT id, name FROM service_clusters "
        "WHERE cluster_type = 'stack_blueprint' AND is_system = true AND deleted_at IS NULL"
    )).fetchall()

    bp_id_map = {row[1]: str(row[0]) for row in blueprints}

    for bp_name, components in BLUEPRINT_COMPONENTS.items():
        bp_id = bp_id_map.get(bp_name)
        if not bp_id:
            continue

        for node_id, comp_name, label, sort_order, is_optional, default_params, depends_on in components:
            cid = comp_id_map.get(comp_name)
            if not cid:
                continue

            # Check if already exists (unique constraint on blueprint_id + node_id)
            existing = conn.execute(sa.text(
                "SELECT id FROM stack_blueprint_components "
                "WHERE blueprint_id = CAST(:bp_id AS uuid) AND node_id = :node_id AND deleted_at IS NULL LIMIT 1"
            ), {"bp_id": bp_id, "node_id": node_id}).fetchone()
            if existing:
                continue

            conn.execute(sa.text("""
                INSERT INTO stack_blueprint_components (
                    id, blueprint_id, component_id, node_id, label,
                    sort_order, is_optional, default_parameters, depends_on,
                    created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), CAST(:bp_id AS uuid), CAST(:comp_id AS uuid),
                    :node_id, :label,
                    :sort_order, :is_optional,
                    CAST(:default_params AS jsonb), CAST(:depends_on AS jsonb),
                    NOW(), NOW()
                )
            """), {
                "bp_id": bp_id,
                "comp_id": cid,
                "node_id": node_id,
                "label": label,
                "sort_order": sort_order,
                "is_optional": is_optional,
                "default_params": json.dumps(default_params) if default_params else None,
                "depends_on": json.dumps(depends_on) if depends_on else None,
            })

    # ── 3. Populate variable bindings ───────────────────────────────
    for bp_name, bindings in VARIABLE_BINDINGS.items():
        bp_id = bp_id_map.get(bp_name)
        if not bp_id:
            continue

        for direction, var_name, target_node, target_param, transform in bindings:
            # Check if already exists
            existing = conn.execute(sa.text(
                "SELECT id FROM stack_variable_bindings "
                "WHERE blueprint_id = CAST(:bp_id AS uuid) "
                "AND direction = :dir AND variable_name = :var "
                "AND target_node_id = :node AND target_parameter = :param "
                "AND deleted_at IS NULL LIMIT 1"
            ), {
                "bp_id": bp_id, "dir": direction, "var": var_name,
                "node": target_node, "param": target_param,
            }).fetchone()
            if existing:
                continue

            conn.execute(sa.text("""
                INSERT INTO stack_variable_bindings (
                    id, blueprint_id, direction, variable_name,
                    target_node_id, target_parameter, transform_expression,
                    created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), CAST(:bp_id AS uuid), :direction, :var_name,
                    :target_node_id, :target_parameter, :transform,
                    NOW(), NOW()
                )
            """), {
                "bp_id": bp_id,
                "direction": direction,
                "var_name": var_name,
                "target_node_id": target_node,
                "target_parameter": target_param,
                "transform": transform,
            })


def downgrade() -> None:
    conn = op.get_bind()

    # Remove variable bindings for system blueprints
    conn.execute(sa.text(
        "DELETE FROM stack_variable_bindings WHERE blueprint_id IN "
        "(SELECT id FROM service_clusters WHERE is_system = true AND cluster_type = 'stack_blueprint')"
    ))

    # Remove blueprint components for system blueprints
    conn.execute(sa.text(
        "DELETE FROM stack_blueprint_components WHERE blueprint_id IN "
        "(SELECT id FROM service_clusters WHERE is_system = true AND cluster_type = 'stack_blueprint')"
    ))

    # Remove system components created by this migration
    comp_names = [c["name"] for c in COMPONENTS]
    for name in comp_names:
        conn.execute(sa.text(
            "DELETE FROM components WHERE name = :name AND is_system = true AND tenant_id IS NULL"
        ), {"name": name})
