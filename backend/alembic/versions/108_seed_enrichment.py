"""
Overview: Enrich seeded stack blueprints with HA/DR config schemas, slot default_parameters,
    and reservation templates.
Architecture: Alembic data migration for blueprint enhancement (Section 8)
Dependencies: alembic, sqlalchemy
Concepts: Category-specific HA/DR JSON schemas, per-slot infrastructure defaults,
    blueprint-level reservation templates with RPO/RTO targets.

Revision ID: 108
Revises: 107
"""

import json

from alembic import op
import sqlalchemy as sa

revision = "108"
down_revision = "107"
branch_labels = None
depends_on = None


# ── HA Config Schemas by Category ────────────────────────────────────

HA_SCHEMAS = {
    "DATABASE": {
        "schema": {
            "type": "object",
            "properties": {
                "replica_count": {"type": "integer", "minimum": 1, "maximum": 7, "description": "Number of replicas"},
                "failover_mode": {"type": "string", "enum": ["auto", "manual"], "description": "Automatic or manual failover"},
                "health_check_interval_seconds": {"type": "integer", "minimum": 5, "maximum": 300, "description": "Health check interval"},
                "quorum_size": {"type": "integer", "minimum": 1, "maximum": 5, "description": "Quorum for leader election"},
                "max_replication_lag_seconds": {"type": "integer", "minimum": 0, "maximum": 300, "description": "Max tolerable replication lag"},
            },
        },
        "defaults": {
            "replica_count": 2,
            "failover_mode": "auto",
            "health_check_interval_seconds": 10,
            "quorum_size": 2,
            "max_replication_lag_seconds": 30,
        },
    },
    "PLATFORM": {
        "schema": {
            "type": "object",
            "properties": {
                "min_replicas": {"type": "integer", "minimum": 1, "maximum": 50, "description": "Minimum replica count"},
                "pod_disruption_budget_pct": {"type": "integer", "minimum": 0, "maximum": 100, "description": "Pod disruption budget (%)"},
                "rolling_update_max_unavailable_pct": {"type": "integer", "minimum": 0, "maximum": 100, "description": "Max unavailable during rolling update (%)"},
                "health_probe_interval_seconds": {"type": "integer", "minimum": 5, "maximum": 120, "description": "Health probe interval"},
            },
        },
        "defaults": {
            "min_replicas": 2,
            "pod_disruption_budget_pct": 25,
            "rolling_update_max_unavailable_pct": 25,
            "health_probe_interval_seconds": 10,
        },
    },
    "STORAGE": {
        "schema": {
            "type": "object",
            "properties": {
                "erasure_parity": {"type": "integer", "minimum": 1, "maximum": 8, "description": "Erasure coding parity shards"},
                "node_failure_tolerance": {"type": "integer", "minimum": 1, "maximum": 4, "description": "Nodes that can fail without data loss"},
                "rebuild_priority": {"type": "string", "enum": ["low", "normal", "high"], "description": "Rebuild priority on node failure"},
            },
        },
        "defaults": {
            "erasure_parity": 2,
            "node_failure_tolerance": 1,
            "rebuild_priority": "normal",
        },
    },
    "MONITORING": {
        "schema": {
            "type": "object",
            "properties": {
                "replication_factor": {"type": "integer", "minimum": 1, "maximum": 5, "description": "Data replication factor"},
                "deduplication_enabled": {"type": "boolean", "description": "Enable deduplication"},
                "scrape_ha_mode": {"type": "string", "enum": ["active_standby", "active_active"], "description": "HA mode for scraping"},
            },
        },
        "defaults": {
            "replication_factor": 2,
            "deduplication_enabled": True,
            "scrape_ha_mode": "active_standby",
        },
    },
    "NETWORKING": {
        "schema": {
            "type": "object",
            "properties": {
                "vrrp_priority": {"type": "integer", "minimum": 1, "maximum": 254, "description": "VRRP priority for active node"},
                "keepalive_interval_seconds": {"type": "integer", "minimum": 1, "maximum": 30, "description": "Keepalive interval"},
                "preempt_mode": {"type": "boolean", "description": "Allow higher-priority node to preempt"},
            },
        },
        "defaults": {
            "vrrp_priority": 100,
            "keepalive_interval_seconds": 3,
            "preempt_mode": True,
        },
    },
    "COMPUTE": {
        "schema": {
            "type": "object",
            "properties": {
                "min_replicas": {"type": "integer", "minimum": 1, "maximum": 20, "description": "Minimum replica count"},
                "anti_affinity_mode": {"type": "string", "enum": ["preferred", "required"], "description": "Pod anti-affinity mode"},
                "circuit_breaker_threshold": {"type": "number", "minimum": 0, "maximum": 1, "description": "Circuit breaker error rate threshold"},
            },
        },
        "defaults": {
            "min_replicas": 2,
            "anti_affinity_mode": "preferred",
            "circuit_breaker_threshold": 0.5,
        },
    },
    "SECURITY": {
        "schema": {
            "type": "object",
            "properties": {
                "min_replicas": {"type": "integer", "minimum": 2, "maximum": 6, "description": "Minimum proxy replicas"},
                "health_check_interval_seconds": {"type": "integer", "minimum": 5, "maximum": 60, "description": "Backend health check interval"},
                "connection_drain_seconds": {"type": "integer", "minimum": 1, "maximum": 300, "description": "Connection drain timeout"},
            },
        },
        "defaults": {
            "min_replicas": 2,
            "health_check_interval_seconds": 10,
            "connection_drain_seconds": 30,
        },
    },
}

# ── DR Config Schemas by Category ────────────────────────────────────

DR_SCHEMAS = {
    "DATABASE": {
        "schema": {
            "type": "object",
            "properties": {
                "replication_mode": {"type": "string", "enum": ["async", "sync", "semi_sync"], "description": "DR replication mode"},
                "rpo_target_seconds": {"type": "integer", "minimum": 0, "maximum": 3600, "description": "RPO target"},
                "rto_target_seconds": {"type": "integer", "minimum": 0, "maximum": 3600, "description": "RTO target"},
                "backup_frequency_hours": {"type": "integer", "minimum": 1, "maximum": 168, "description": "Backup frequency"},
                "pitr_retention_days": {"type": "integer", "minimum": 1, "maximum": 90, "description": "PITR retention"},
                "failover_priority": {"type": "integer", "minimum": 1, "maximum": 10, "description": "Failover priority (lower = higher)"},
            },
        },
        "defaults": {
            "replication_mode": "async",
            "rpo_target_seconds": 60,
            "rto_target_seconds": 300,
            "backup_frequency_hours": 6,
            "pitr_retention_days": 7,
            "failover_priority": 1,
        },
    },
    "PLATFORM": {
        "schema": {
            "type": "object",
            "properties": {
                "cross_region_replication": {"type": "boolean", "description": "Enable cross-region replication"},
                "backup_schedule_cron": {"type": "string", "description": "Backup schedule (cron expression)"},
                "restore_strategy": {"type": "string", "enum": ["full", "incremental", "snapshot"], "description": "Restore strategy"},
                "data_sync_method": {"type": "string", "enum": ["streaming", "snapshot", "etcd_backup"], "description": "Data sync method"},
            },
        },
        "defaults": {
            "cross_region_replication": False,
            "backup_schedule_cron": "0 */6 * * *",
            "restore_strategy": "snapshot",
            "data_sync_method": "etcd_backup",
        },
    },
    "STORAGE": {
        "schema": {
            "type": "object",
            "properties": {
                "site_replication_mode": {"type": "string", "enum": ["active_active", "active_passive"], "description": "Site replication mode"},
                "versioning_enabled": {"type": "boolean", "description": "Enable object versioning"},
                "lifecycle_retention_days": {"type": "integer", "minimum": 1, "maximum": 3650, "description": "Object lifecycle retention"},
            },
        },
        "defaults": {
            "site_replication_mode": "active_passive",
            "versioning_enabled": True,
            "lifecycle_retention_days": 365,
        },
    },
    "MONITORING": {
        "schema": {
            "type": "object",
            "properties": {
                "remote_write_enabled": {"type": "boolean", "description": "Enable remote write to DR"},
                "long_term_retention_days": {"type": "integer", "minimum": 30, "maximum": 3650, "description": "Long-term retention"},
                "config_backup_frequency_hours": {"type": "integer", "minimum": 1, "maximum": 168, "description": "Config backup frequency"},
            },
        },
        "defaults": {
            "remote_write_enabled": True,
            "long_term_retention_days": 365,
            "config_backup_frequency_hours": 24,
        },
    },
    "NETWORKING": {
        "schema": {
            "type": "object",
            "properties": {
                "standby_mode": {"type": "string", "enum": ["active", "passive"], "description": "DR standby mode"},
                "config_sync_interval_seconds": {"type": "integer", "minimum": 10, "maximum": 3600, "description": "Config sync interval"},
                "dns_failover_ttl_seconds": {"type": "integer", "minimum": 5, "maximum": 300, "description": "DNS failover TTL"},
            },
        },
        "defaults": {
            "standby_mode": "passive",
            "config_sync_interval_seconds": 60,
            "dns_failover_ttl_seconds": 30,
        },
    },
    "COMPUTE": {
        "schema": {
            "type": "object",
            "properties": {
                "blue_green_enabled": {"type": "boolean", "description": "Enable blue/green deployments"},
                "canary_percentage": {"type": "integer", "minimum": 1, "maximum": 50, "description": "Canary traffic percentage"},
                "rollback_timeout_seconds": {"type": "integer", "minimum": 30, "maximum": 3600, "description": "Rollback timeout"},
                "image_replication": {"type": "boolean", "description": "Enable cross-region image replication"},
            },
        },
        "defaults": {
            "blue_green_enabled": True,
            "canary_percentage": 10,
            "rollback_timeout_seconds": 300,
            "image_replication": True,
        },
    },
    "SECURITY": {
        "schema": {
            "type": "object",
            "properties": {
                "multi_region_deployment": {"type": "boolean", "description": "Deploy to multiple regions"},
                "gslb_failover_enabled": {"type": "boolean", "description": "Enable GSLB failover"},
                "config_sync_interval_seconds": {"type": "integer", "minimum": 10, "maximum": 3600, "description": "WAF/proxy config sync interval"},
            },
        },
        "defaults": {
            "multi_region_deployment": False,
            "gslb_failover_enabled": False,
            "config_sync_interval_seconds": 300,
        },
    },
}

# ── Slot Default Parameters by Blueprint Name ────────────────────────

SLOT_DEFAULTS = {
    "postgresql-ha": {
        "primary": {"cpu_cores": 4, "memory_gb": 16, "storage_gb": 100, "pg_version": "16", "shared_buffers_pct": 25, "wal_level": "replica"},
        "replica": {"cpu_cores": 4, "memory_gb": 16, "storage_gb": 100, "read_only": True, "streaming_replication": True},
        "pgbouncer": {"pool_mode": "transaction", "max_client_conn": 1000, "default_pool_size": 25},
        "patroni": {"ttl": 30, "loop_wait": 10, "retry_timeout": 10, "maximum_lag_on_failover": 1048576},
        "backup_agent": {"compression": "lz4", "retention_full": 7, "retention_wal": 30, "schedule": "0 2 * * *"},
        "dr_replica": {"cpu_cores": 4, "memory_gb": 16, "storage_gb": 100, "async_replication": True},
    },
    "redis-sentinel": {
        "primary": {"maxmemory_gb": 4, "maxmemory_policy": "allkeys-lru", "persistence": "both"},
        "replica": {"maxmemory_gb": 4, "replica_read_only": True},
        "sentinel": {"down_after_ms": 5000, "failover_timeout_ms": 60000, "parallel_syncs": 1},
        "dr_replica": {"maxmemory_gb": 4, "async_replication": True},
    },
    "mongodb-replicaset": {
        "member": {"cpu_cores": 4, "memory_gb": 16, "storage_gb": 50, "wired_tiger_cache_gb": 8},
        "mongos": {"cpu_cores": 2, "memory_gb": 4, "max_connections": 5000},
        "config_server": {"cpu_cores": 2, "memory_gb": 4, "storage_gb": 10},
        "backup_agent": {"method": "mongodump", "compression": "gzip", "schedule": "0 3 * * *"},
        "dr_secondary": {"cpu_cores": 4, "memory_gb": 16, "storage_gb": 50, "priority": 0, "votes": 0},
    },
    "kubernetes-app-platform": {
        "control_plane": {"cpu_cores": 4, "memory_gb": 8, "disk_gb": 50, "etcd_storage_gb": 20},
        "worker": {"cpu_cores": 8, "memory_gb": 32, "disk_gb": 100, "max_pods": 110},
        "ingress": {"cpu_cores": 2, "memory_gb": 4, "replicas": 2, "type": "nginx"},
        "cert_manager": {"cpu_cores": 1, "memory_gb": 1, "issuer": "letsencrypt"},
        "velero": {"schedule": "0 */6 * * *", "ttl_hours": 168, "storage_location": "minio"},
        "dr_cluster": {"control_plane_nodes": 3, "worker_nodes": 3},
    },
    "container-web-service": {
        "container": {"cpu_limit": "1", "memory_limit_mb": 512, "health_check_path": "/health", "readiness_path": "/ready"},
        "load_balancer": {"algorithm": "round_robin", "health_check_interval_seconds": 10, "sticky_sessions": False},
        "tls": {"min_version": "1.2", "ciphers": "ECDHE-ECDSA-AES256-GCM-SHA384", "hsts_max_age": 31536000},
        "health_check": {"interval_seconds": 10, "timeout_seconds": 5, "unhealthy_threshold": 3},
        "dr_region": {"failover_dns_ttl_seconds": 30, "sync_method": "image_replication"},
    },
    "kafka-cluster": {
        "broker": {"cpu_cores": 4, "memory_gb": 16, "storage_gb": 500, "num_partitions": 12, "log_retention_hours": 168},
        "schema_registry": {"cpu_cores": 2, "memory_gb": 4, "compatibility": "BACKWARD"},
        "connect": {"cpu_cores": 2, "memory_gb": 8, "max_tasks": 10},
        "mirror_maker": {"topics_pattern": ".*", "sync_group_offsets": True, "replication_factor": 3},
    },
    "rabbitmq-cluster": {
        "node": {"cpu_cores": 2, "memory_gb": 8, "disk_free_limit_gb": 5, "vm_memory_high_watermark": 0.6},
        "haproxy": {"maxconn": 10000, "timeout_client_ms": 30000, "timeout_server_ms": 30000},
        "dr_shovel": {"reconnect_delay_seconds": 5, "prefetch_count": 1000},
    },
    "minio-distributed": {
        "node": {"cpu_cores": 4, "memory_gb": 16, "disks_per_node": 4, "disk_size_gb": 500},
        "load_balancer": {"algorithm": "least_connections", "health_check_path": "/minio/health/live"},
        "dr_site": {"bandwidth_limit_mbps": 1000, "sync_mode": "active_passive"},
    },
    "monitoring-stack": {
        "prometheus": {"retention_days": 30, "scrape_interval_seconds": 15, "storage_gb": 100},
        "alertmanager": {"group_wait_seconds": 30, "group_interval_seconds": 300, "repeat_interval_seconds": 3600},
        "grafana": {"anonymous_access": False, "default_theme": "light", "max_concurrent_sessions": 100},
        "thanos_sidecar": {"upload_compacted": True, "min_time": "-2h"},
        "thanos_store": {"chunk_pool_size_gb": 2, "max_concurrent": 20},
        "node_exporter": {"collectors": ["cpu", "diskstats", "filesystem", "loadavg", "meminfo", "netdev"]},
    },
    "log-aggregation": {
        "loki_write": {"cpu_cores": 2, "memory_gb": 8, "replication_factor": 3},
        "loki_read": {"cpu_cores": 2, "memory_gb": 4, "max_concurrent_queries": 20},
        "log_shipper": {"batch_size": 102400, "batch_wait_ms": 1000},
        "grafana": {"anonymous_access": False, "default_datasource": "loki"},
        "dr_forwarder": {"batch_size": 102400, "compression": "snappy"},
    },
    "vpn-gateway": {
        "gateway_primary": {"cpu_cores": 2, "memory_gb": 4, "max_tunnels": 50, "mtu": 1420},
        "gateway_standby": {"cpu_cores": 2, "memory_gb": 4, "priority": 50},
        "firewall": {"default_policy": "deny", "log_dropped": True},
        "dns": {"upstream": ["1.1.1.1", "8.8.8.8"], "cache_ttl_seconds": 300},
        "dr_gateway": {"cpu_cores": 2, "memory_gb": 4, "priority": 10},
    },
    "reverse-proxy-waf": {
        "proxy": {"cpu_cores": 2, "memory_gb": 4, "max_connections": 10000, "keepalive_timeout_seconds": 60},
        "waf": {"paranoia_level": 1, "anomaly_threshold": 5, "rule_engine": "on"},
        "rate_limiter": {"default_rps": 100, "burst_multiplier": 2, "ban_duration_seconds": 600},
        "gslb": {"algorithm": "geolocation", "health_check_interval_seconds": 10},
    },
}

# ── Reservation Templates by Blueprint Name ──────────────────────────

RESERVATION_TEMPLATES = {
    "postgresql-ha": {"type": "WARM_STANDBY", "pct": 80, "rpo": 60, "rto": 300},
    "redis-sentinel": {"type": "HOT_STANDBY", "pct": 100, "rpo": 5, "rto": 60},
    "mongodb-replicaset": {"type": "WARM_STANDBY", "pct": 80, "rpo": 120, "rto": 300},
    "kubernetes-app-platform": {"type": "PILOT_LIGHT", "pct": 50, "rpo": 900, "rto": 1800},
    "container-web-service": {"type": "HOT_STANDBY", "pct": 100, "rpo": 0, "rto": 60},
    "kafka-cluster": {"type": "WARM_STANDBY", "pct": 80, "rpo": 30, "rto": 600},
    "rabbitmq-cluster": {"type": "WARM_STANDBY", "pct": 80, "rpo": 60, "rto": 300},
    "minio-distributed": {"type": "WARM_STANDBY", "pct": 80, "rpo": 30, "rto": 600},
    "monitoring-stack": {"type": "COLD_STANDBY", "pct": 30, "rpo": 300, "rto": 900},
    "log-aggregation": {"type": "COLD_STANDBY", "pct": 30, "rpo": 300, "rto": 1200},
    "vpn-gateway": {"type": "HOT_STANDBY", "pct": 100, "rpo": 0, "rto": 120},
    "reverse-proxy-waf": {"type": "HOT_STANDBY", "pct": 100, "rpo": 0, "rto": 60},
}


def upgrade() -> None:
    conn = op.get_bind()

    # Get all seeded stack blueprints
    rows = conn.execute(sa.text(
        "SELECT id, name, category FROM service_clusters "
        "WHERE cluster_type = 'stack_blueprint' AND is_system = true AND deleted_at IS NULL"
    )).fetchall()

    if not rows:
        return

    for row in rows:
        bp_id, bp_name, category = str(row[0]), row[1], row[2]

        # 1. Update HA/DR config schemas
        ha = HA_SCHEMAS.get(category)
        dr = DR_SCHEMAS.get(category)
        if ha or dr:
            conn.execute(sa.text(
                "UPDATE service_clusters SET "
                "ha_config_schema = CAST(:ha_schema AS jsonb), "
                "ha_config_defaults = CAST(:ha_defaults AS jsonb), "
                "dr_config_schema = CAST(:dr_schema AS jsonb), "
                "dr_config_defaults = CAST(:dr_defaults AS jsonb) "
                "WHERE id = CAST(:id AS uuid)"
            ), {
                "id": bp_id,
                "ha_schema": json.dumps(ha["schema"]) if ha else None,
                "ha_defaults": json.dumps(ha["defaults"]) if ha else None,
                "dr_schema": json.dumps(dr["schema"]) if dr else None,
                "dr_defaults": json.dumps(dr["defaults"]) if dr else None,
            })

        # 2. Update slot default_parameters
        slot_defaults = SLOT_DEFAULTS.get(bp_name, {})
        for slot_name, params in slot_defaults.items():
            conn.execute(sa.text(
                "UPDATE service_cluster_slots SET "
                "default_parameters = CAST(:params AS jsonb) "
                "WHERE cluster_id = CAST(:bp_id AS uuid) AND name = :slot_name AND deleted_at IS NULL"
            ), {
                "bp_id": bp_id,
                "slot_name": slot_name,
                "params": json.dumps(params),
            })

        # 3. Create reservation template
        tmpl = RESERVATION_TEMPLATES.get(bp_name)
        if tmpl:
            # Check if already exists
            existing = conn.execute(sa.text(
                "SELECT id FROM blueprint_reservation_templates "
                "WHERE blueprint_id = CAST(:bp_id AS uuid) AND deleted_at IS NULL"
            ), {"bp_id": bp_id}).fetchone()
            if not existing:
                conn.execute(sa.text("""
                    INSERT INTO blueprint_reservation_templates (
                        id, blueprint_id, reservation_type, resource_percentage,
                        rto_seconds, rpo_seconds, auto_create_on_deploy,
                        created_at, updated_at
                    ) VALUES (
                        gen_random_uuid(), CAST(:bp_id AS uuid), :rtype, :pct,
                        :rto, :rpo, true,
                        NOW(), NOW()
                    )
                """), {
                    "bp_id": bp_id,
                    "rtype": tmpl["type"],
                    "pct": tmpl["pct"],
                    "rto": tmpl["rto"],
                    "rpo": tmpl["rpo"],
                })


def downgrade() -> None:
    conn = op.get_bind()
    # Remove reservation templates for system blueprints
    conn.execute(sa.text(
        "DELETE FROM blueprint_reservation_templates WHERE blueprint_id IN "
        "(SELECT id FROM service_clusters WHERE is_system = true AND cluster_type = 'stack_blueprint')"
    ))
    # Clear HA/DR schemas
    conn.execute(sa.text(
        "UPDATE service_clusters SET "
        "ha_config_schema = NULL, ha_config_defaults = NULL, "
        "dr_config_schema = NULL, dr_config_defaults = NULL "
        "WHERE is_system = true AND cluster_type = 'stack_blueprint'"
    ))
    # Clear slot defaults
    conn.execute(sa.text(
        "UPDATE service_cluster_slots SET default_parameters = NULL "
        "WHERE cluster_id IN "
        "(SELECT id FROM service_clusters WHERE is_system = true AND cluster_type = 'stack_blueprint')"
    ))
