"""
Overview: Container sandbox executor — runs user-authored code in ephemeral Docker containers.
Architecture: Sandboxed execution engine for automated activities (Section 11.5)
Dependencies: docker, asyncio, json
Concepts: Container isolation, resource limits, timeout enforcement, stdin/stdout JSON protocol
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default container configuration
DEFAULT_IMAGE = "python:3.12-slim"
DEFAULT_MEMORY_LIMIT = "256m"
DEFAULT_CPU_PERIOD = 100000
DEFAULT_CPU_QUOTA = 50000  # 50% of one CPU
DEFAULT_NETWORK_MODE = "none"


class SandboxError(Exception):
    def __init__(self, message: str, code: str = "SANDBOX_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class SandboxResult:
    """Result from a sandbox execution."""

    def __init__(
        self,
        success: bool,
        output: dict[str, Any] | None = None,
        error: str | None = None,
        exit_code: int = -1,
        stderr: str = "",
    ):
        self.success = success
        self.output = output
        self.error = error
        self.exit_code = exit_code
        self.stderr = stderr


class ContainerSandboxExecutor:
    """Executes activity code in ephemeral Docker containers with resource limits."""

    def __init__(self):
        self._docker_client = None

    def _get_client(self):
        """Lazy-load Docker client."""
        if self._docker_client is None:
            try:
                import docker
                self._docker_client = docker.from_env()
            except ImportError:
                raise SandboxError(
                    "Docker SDK not installed. Install with: pip install docker",
                    "DOCKER_NOT_AVAILABLE",
                )
            except Exception as e:
                raise SandboxError(
                    f"Cannot connect to Docker daemon: {e}",
                    "DOCKER_NOT_AVAILABLE",
                )
        return self._docker_client

    async def execute(
        self,
        source_code: str,
        input_data: dict[str, Any],
        runtime_config: dict[str, Any] | None = None,
        timeout_seconds: int = 300,
    ) -> SandboxResult:
        """Execute code in an ephemeral container.

        Protocol:
        - Input is passed via stdin as JSON
        - Output is read from stdout as JSON
        - Errors are captured from stderr
        """
        config = runtime_config or {}
        image = config.get("image", DEFAULT_IMAGE)
        memory_limit = config.get("memory_limit", DEFAULT_MEMORY_LIMIT)
        cpu_period = config.get("cpu_period", DEFAULT_CPU_PERIOD)
        cpu_quota = config.get("cpu_quota", DEFAULT_CPU_QUOTA)
        network_mode = config.get("network_mode", DEFAULT_NETWORK_MODE)

        # Build the wrapper script that reads stdin JSON, runs user code, outputs JSON
        wrapper_script = self._build_wrapper(source_code)
        input_json = json.dumps(input_data)

        try:
            return await asyncio.wait_for(
                self._run_container(
                    image=image,
                    wrapper_script=wrapper_script,
                    input_json=input_json,
                    memory_limit=memory_limit,
                    cpu_period=cpu_period,
                    cpu_quota=cpu_quota,
                    network_mode=network_mode,
                ),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            return SandboxResult(
                success=False,
                error=f"Execution timed out after {timeout_seconds}s",
                exit_code=-1,
            )
        except SandboxError:
            raise
        except Exception as e:
            logger.exception("Sandbox execution failed")
            return SandboxResult(
                success=False,
                error=f"Sandbox error: {str(e)}",
                exit_code=-1,
            )

    async def _run_container(
        self,
        image: str,
        wrapper_script: str,
        input_json: str,
        memory_limit: str,
        cpu_period: int,
        cpu_quota: int,
        network_mode: str,
    ) -> SandboxResult:
        """Run code in a Docker container (async wrapper around sync Docker SDK)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._run_container_sync,
            image, wrapper_script, input_json,
            memory_limit, cpu_period, cpu_quota, network_mode,
        )

    def _run_container_sync(
        self,
        image: str,
        wrapper_script: str,
        input_json: str,
        memory_limit: str,
        cpu_period: int,
        cpu_quota: int,
        network_mode: str,
    ) -> SandboxResult:
        """Synchronous container execution."""
        client = self._get_client()

        container = None
        try:
            container = client.containers.run(
                image=image,
                command=["python", "-c", wrapper_script],
                stdin_open=True,
                detach=True,
                mem_limit=memory_limit,
                cpu_period=cpu_period,
                cpu_quota=cpu_quota,
                network_mode=network_mode,
                read_only=True,
                tmpfs={"/tmp": "size=64M"},
                security_opt=["no-new-privileges"],
                remove=False,
            )

            # Attach and send input
            sock = container.attach_socket(params={"stdin": 1, "stream": 1})
            sock._sock.sendall((input_json + "\n").encode())
            sock._sock.shutdown(1)  # Close write end
            sock.close()

            # Wait for completion
            result = container.wait(timeout=300)
            exit_code = result.get("StatusCode", -1)

            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace").strip()
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace").strip()

            if exit_code != 0:
                return SandboxResult(
                    success=False,
                    error=stderr or f"Process exited with code {exit_code}",
                    exit_code=exit_code,
                    stderr=stderr,
                )

            # Parse output JSON
            try:
                output = json.loads(stdout) if stdout else {}
            except json.JSONDecodeError:
                return SandboxResult(
                    success=False,
                    error=f"Invalid JSON output: {stdout[:500]}",
                    exit_code=exit_code,
                    stderr=stderr,
                )

            return SandboxResult(
                success=True,
                output=output,
                exit_code=exit_code,
                stderr=stderr,
            )

        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

    def _build_wrapper(self, user_code: str) -> str:
        """Build a wrapper script that handles stdin/stdout JSON protocol."""
        # Escape the user code for embedding in a string
        escaped = user_code.replace("\\", "\\\\").replace("'", "\\'")
        return f'''
import sys, json

def _run():
    input_data = json.loads(sys.stdin.readline())

    # User-defined namespace
    ns = {{"input": input_data, "output": {{}}}}

    user_code = \\'{escaped}\\'
    exec(user_code, ns)

    result = ns.get("output", {{}})
    if not isinstance(result, dict):
        result = {{"result": result}}

    print(json.dumps(result))

try:
    _run()
except Exception as e:
    print(json.dumps({{"error": str(e)}}), file=sys.stderr)
    sys.exit(1)
'''


class WebhookExecutor:
    """Executes an activity via HTTP webhook (POST)."""

    async def execute(
        self,
        webhook_url: str,
        input_data: dict[str, Any],
        timeout_seconds: int = 300,
        headers: dict[str, str] | None = None,
    ) -> SandboxResult:
        """POST input data to webhook URL, expect JSON response."""
        try:
            import httpx
        except ImportError:
            raise SandboxError("httpx not installed", "HTTPX_NOT_AVAILABLE")

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(
                    webhook_url,
                    json=input_data,
                    headers=headers or {},
                )

                if response.status_code >= 400:
                    return SandboxResult(
                        success=False,
                        error=f"Webhook returned {response.status_code}: {response.text[:500]}",
                        exit_code=response.status_code,
                    )

                try:
                    output = response.json()
                except Exception:
                    output = {"response": response.text}

                return SandboxResult(success=True, output=output, exit_code=0)

        except Exception as e:
            return SandboxResult(
                success=False,
                error=f"Webhook error: {str(e)}",
                exit_code=-1,
            )
