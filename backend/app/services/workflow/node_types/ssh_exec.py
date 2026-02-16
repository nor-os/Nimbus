"""
Overview: SSH exec node — connects to a remote host via SSH and executes a command.
Architecture: Integration node type (Section 5)
Dependencies: app.services.workflow.node_types.base, app.services.workflow.expression_engine,
    app.services.crypto.credential_encryption, asyncssh
Concepts: SSH command execution, credential decryption from CloudBackend, asyncssh
"""

from __future__ import annotations

import logging

import asyncssh

from app.services.workflow.expression_engine import (
    ExpressionContext,
    interpolate_string,
)
from app.services.workflow.expression_functions import BUILTIN_FUNCTIONS
from app.services.workflow.node_registry import (
    NodeCategory,
    NodeTypeDefinition,
    PortDef,
    PortDirection,
    PortType,
    get_registry,
)
from app.services.workflow.node_types.base import BaseNodeExecutor, NodeExecutionContext, NodeOutput

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60


class SshExecNodeExecutor(BaseNodeExecutor):
    """Connects to a remote host via SSH and executes a command."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        host_template = context.config.get("host", "")
        port = context.config.get("port", 22)
        username_template = context.config.get("username", "root")
        auth_method = context.config.get("auth_method", "private_key")
        private_key_secret_id = context.config.get("private_key_secret_id", "")
        password_secret_id = context.config.get("password_secret_id", "")
        command_template = context.config.get("command", "")
        timeout = context.config.get("timeout", DEFAULT_TIMEOUT)
        known_hosts_policy = context.config.get("known_hosts_policy", "accept_all")

        expr_ctx = ExpressionContext(
            variables=context.variables,
            nodes=context.node_outputs,
            loop=context.loop_context or {},
            input_data=context.workflow_input,
        )

        host = interpolate_string(str(host_template), expr_ctx, BUILTIN_FUNCTIONS)
        username = interpolate_string(str(username_template), expr_ctx, BUILTIN_FUNCTIONS)
        command = interpolate_string(str(command_template), expr_ctx, BUILTIN_FUNCTIONS)
        private_key_secret_id = interpolate_string(
            str(private_key_secret_id), expr_ctx, BUILTIN_FUNCTIONS
        )
        password_secret_id = interpolate_string(
            str(password_secret_id), expr_ctx, BUILTIN_FUNCTIONS
        )

        if not host:
            return NodeOutput(error="SSH host is required")
        if not command:
            return NodeOutput(error="SSH command is required")

        if context.is_test:
            mock_result = (context.mock_config or {}).get("result", {})
            return NodeOutput(
                data={
                    "stdout": mock_result.get("stdout", ""),
                    "stderr": mock_result.get("stderr", ""),
                    "exit_code": mock_result.get("exit_code", 0),
                    "is_mock": True,
                },
                next_port="out",
            )

        # Resolve credentials from CloudBackend
        try:
            connect_kwargs = await _resolve_ssh_credentials(
                auth_method, private_key_secret_id, password_secret_id
            )
        except Exception as e:
            logger.exception("Failed to resolve SSH credentials: %s", e)
            return NodeOutput(error=f"SSH credential resolution failed: {e}")

        # Determine known_hosts handling
        known_hosts: object = None
        if known_hosts_policy == "accept_all":
            known_hosts = None  # asyncssh accepts all when known_hosts=None
        elif known_hosts_policy == "strict":
            known_hosts = ()  # Use system known_hosts
        # trust_on_first_use: not yet implemented, treat as accept_all

        try:
            async with asyncssh.connect(
                host,
                port=port,
                username=username,
                known_hosts=known_hosts,
                **connect_kwargs,
            ) as conn:
                result = await asyncssh.wait_for(
                    conn.run(command, check=False),
                    timeout=timeout,
                )

            output_data = {
                "stdout": result.stdout or "",
                "stderr": result.stderr or "",
                "exit_code": result.exit_status,
            }

            if result.exit_status != 0:
                return NodeOutput(
                    data=output_data,
                    next_port="error",
                    error=f"Command exited with code {result.exit_status}",
                )

            return NodeOutput(data=output_data, next_port="out")

        except asyncssh.DisconnectError as e:
            return NodeOutput(error=f"SSH connection failed: {e}")
        except asyncssh.ProcessError as e:
            return NodeOutput(error=f"SSH process error: {e}")
        except TimeoutError:
            return NodeOutput(error=f"SSH command timed out after {timeout}s")
        except Exception as e:
            logger.exception("SSH execution failed: %s", e)
            return NodeOutput(error=f"SSH execution failed: {e}")


async def _resolve_ssh_credentials(
    auth_method: str,
    private_key_secret_id: str,
    password_secret_id: str,
) -> dict:
    """Resolve SSH credentials from a CloudBackend record.

    Returns kwargs suitable for asyncssh.connect().
    """
    from sqlalchemy import select

    from app.db.session import async_session_factory
    from app.models.cloud_backend import CloudBackend
    from app.services.crypto.credential_encryption import decrypt_credentials

    if auth_method == "private_key" and private_key_secret_id:
        async with async_session_factory() as db:
            stmt = select(CloudBackend).where(CloudBackend.id == private_key_secret_id)
            result = await db.execute(stmt)
            backend = result.scalar_one_or_none()

        if not backend or not backend.credentials_encrypted:
            raise ValueError(f"SSH key backend not found: {private_key_secret_id}")

        creds = decrypt_credentials(backend.credentials_encrypted)
        private_key_pem = creds.get("private_key", "")
        if not private_key_pem:
            raise ValueError("Backend credentials missing 'private_key' field")

        key = asyncssh.import_private_key(private_key_pem)
        return {"client_keys": [key], "password": None}

    if auth_method == "password" and password_secret_id:
        async with async_session_factory() as db:
            stmt = select(CloudBackend).where(CloudBackend.id == password_secret_id)
            result = await db.execute(stmt)
            backend = result.scalar_one_or_none()

        if not backend or not backend.credentials_encrypted:
            raise ValueError(f"SSH password backend not found: {password_secret_id}")

        creds = decrypt_credentials(backend.credentials_encrypted)
        password = creds.get("password", "")
        if not password:
            raise ValueError("Backend credentials missing 'password' field")

        return {"password": password, "client_keys": []}

    raise ValueError(f"Invalid auth_method '{auth_method}' or missing secret ID")


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="ssh_exec",
        label="SSH Execute",
        category=NodeCategory.INTEGRATION,
        description="Connects to a remote host via SSH and executes a command.",
        icon="&#128421;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Success (exit 0)"),
            PortDef("error", PortDirection.OUTPUT, PortType.FLOW, "Error (non-zero exit)"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "Remote hostname or IP (supports ${expression})",
                },
                "port": {
                    "type": "integer",
                    "default": 22,
                    "description": "SSH port",
                },
                "username": {
                    "type": "string",
                    "default": "root",
                    "description": "SSH username (supports ${expression})",
                },
                "auth_method": {
                    "type": "string",
                    "enum": ["private_key", "password"],
                    "default": "private_key",
                },
                "private_key_secret_id": {
                    "type": "string",
                    "description": "UUID of CloudBackend storing the SSH private key",
                    "x-ui-widget": "secret-picker",
                },
                "password_secret_id": {
                    "type": "string",
                    "description": "UUID of CloudBackend storing the SSH password",
                    "x-ui-widget": "secret-picker",
                },
                "command": {
                    "type": "string",
                    "description": "Shell command to execute (supports ${expression})",
                    "x-ui-widget": "command",
                },
                "timeout": {
                    "type": "number",
                    "default": 60,
                    "description": "Command timeout in seconds",
                },
                "known_hosts_policy": {
                    "type": "string",
                    "enum": ["strict", "trust_on_first_use", "accept_all"],
                    "default": "accept_all",
                },
            },
            "required": ["host", "command"],
        },
        executor_class=SshExecNodeExecutor,
    ))
