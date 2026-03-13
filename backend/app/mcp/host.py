from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
import re
import shutil
import time
from textwrap import dedent

from app.core.config import settings


class MCPHostEngine:
    def __init__(self):
        self.mcp_base_path = Path("/tmp/mcp-servers")
        self.mcp_base_path.mkdir(exist_ok=True)
        self._docker_client = None
        self._server_logs: dict[str, list[str]] = {}

    def build_gateway_url(self, server_id: str) -> str:
        return f"{settings.GATEWAY_PUBLIC_URL}/mcp/{server_id}"

    def server_workspace(self, server_id: str) -> Path:
        server_dir = self.mcp_base_path / server_id
        server_dir.mkdir(parents=True, exist_ok=True)
        return server_dir

    def append_log(self, server_id: str, msg: str) -> None:
        timestamp = datetime.utcnow().strftime("%H:%M:%S")
        self._server_logs.setdefault(server_id, []).append(f"[{timestamp}] {msg}")

    async def provision_inline_code(
        self,
        *,
        server_id: str,
        server_code: str,
        entry_file: str = "server.py",
        requirements_txt: str | None = None,
    ) -> Path:
        return await asyncio.to_thread(
            self._provision_inline_code_sync,
            server_id,
            server_code,
            entry_file,
            requirements_txt,
        )

    def _provision_inline_code_sync(
        self,
        server_id: str,
        server_code: str,
        entry_file: str,
        requirements_txt: str | None,
    ) -> Path:
        server_dir = self.server_workspace(server_id)
        file_path = server_dir / entry_file
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(server_code)
        if requirements_txt:
            (server_dir / "requirements.txt").write_text(requirements_txt)
        return server_dir

    def _maybe_adapt_workspace_for_gateway_auth(
        self,
        *,
        server_id: str,
        workspace_dir: Path,
        entry_file: str,
    ) -> None:
        entry_path = workspace_dir / entry_file
        if not entry_path.exists():
            return

        try:
            source = entry_path.read_text()
        except Exception:
            return

        # Detect the specific secure FastMCP Okta template and remove
        # in-container auth because platform Keycloak/Google auth is enforced
        # by the gateway before requests reach the runtime.
        template_markers = (
            "from auth.okta_verifier import create_okta_verifier",
            "from fastmcp.server.auth import require_scopes",
            "from fastmcp.server.middleware import AuthMiddleware",
            'name="Secure Okta MCP Server"',
        )
        if not all(marker in source for marker in template_markers):
            return

        backup_path = entry_path.with_name(f"{entry_path.name}.platform-orig")
        if not backup_path.exists():
            backup_path.write_text(source)

        entry_path.write_text(
            dedent(
                """\
                \"\"\"Platform-adapted FastMCP server secured by the MCP gateway.\"\"\"

                from __future__ import annotations

                from dotenv import load_dotenv
                from fastmcp import FastMCP

                from config import load_settings
                from tools.content_tool import create_content
                from tools.math_tools import add_numbers, subtract_numbers
                from tools.search_tool import search_web

                load_dotenv()
                settings = load_settings()

                mcp = FastMCP(
                    name="Secure MCP Server",
                )


                @mcp.tool()
                def add(a: int, b: int) -> int:
                    return add_numbers(a, b)


                @mcp.tool()
                def subtract(a: int, b: int) -> int:
                    return subtract_numbers(a, b)


                @mcp.tool()
                def tavily_search(query: str) -> dict:
                    return search_web(query)


                @mcp.tool()
                def generate_article(topic: str) -> str:
                    return create_content(topic)


                @mcp.tool()
                def whoami() -> dict:
                    return {
                        "provider": "keycloak",
                        "message": "Authentication is enforced by the platform gateway before requests reach this MCP runtime.",
                    }


                if __name__ == "__main__":
                    mcp.run(
                        transport="http",
                        host=settings.host,
                        port=settings.port,
                        path=settings.path,
                    )
                """
            )
        )
        self.append_log(
            server_id,
            "Detected Okta FastMCP template; switched runtime auth to platform gateway mode (Keycloak/Google via MCP gateway).",
        )

    async def deploy_python_workspace(
        self,
        *,
        server_id: str,
        workspace_dir: Path,
        entry_file: str,
        runtime_port: int,
        runtime_env: dict[str, str] | None = None,
    ) -> dict:
        return await asyncio.to_thread(
            self._deploy_python_workspace_sync,
            server_id,
            Path(workspace_dir),
            entry_file,
            runtime_port,
            runtime_env or {},
        )

    async def register_external_target(
        self,
        *,
        server_id: str,
        upstream_url: str,
        headers: dict | None = None,
        timeout_seconds: int = 30,
    ) -> dict:
        self.append_log(server_id, f"Registered external MCP target: {upstream_url}")
        return {
            "kind": "external",
            "upstream_url": upstream_url.rstrip("/"),
            "headers": headers or {},
            "timeout_seconds": int(timeout_seconds or 30),
        }

    async def stop(self, config: dict | None) -> None:
        await asyncio.to_thread(self._stop_sync, config or {})

    async def get_status(self, config: dict | None) -> str:
        return await asyncio.to_thread(self._get_status_sync, config or {})

    async def get_logs(self, server_id: str, config: dict | None) -> list[str]:
        return await asyncio.to_thread(self._get_logs_sync, server_id, config or {})

    def upstream_url(self, config: dict | None) -> str | None:
        runtime = (config or {}).get("runtime", {})
        if runtime.get("kind") == "docker":
            internal_url = runtime.get("internal_url")
            runtime_path = runtime.get("path")
            if runtime_path:
                return self._join_runtime_url(internal_url, runtime_path)
            return internal_url
        if runtime.get("kind") == "external":
            return runtime.get("upstream_url")
        return None

    def upstream_headers(self, config: dict | None) -> dict:
        runtime = (config or {}).get("runtime", {})
        headers = runtime.get("headers") or {}
        return headers if isinstance(headers, dict) else {}

    def upstream_timeout(self, config: dict | None) -> int:
        runtime = (config or {}).get("runtime", {})
        timeout_value = runtime.get("timeout_seconds") or 30
        try:
            return int(timeout_value)
        except (TypeError, ValueError):
            return 30

    def _docker_client_sync(self):
        if self._docker_client is None:
            try:
                import docker
            except ImportError as exc:
                raise RuntimeError("Docker SDK is not installed in the backend container") from exc
            self._docker_client = docker.from_env()
        return self._docker_client

    def _container_name(self, server_id: str) -> str:
        return f"mcp-gateway-{server_id[:12]}"

    def _image_tag(self, server_id: str) -> str:
        return f"mcp-gateway-{server_id}:latest"

    def _join_runtime_url(self, base_url: str | None, path: str | None) -> str | None:
        if not base_url:
            return None
        if not path:
            return base_url
        return f"{base_url.rstrip('/')}/{path.lstrip('/')}"

    def _runtime_dockerfile(self, server_dir: Path, entry_file: str, runtime_port: int) -> str:
        dockerfile_name = "Dockerfile.gateway"
        dockerfile_path = server_dir / dockerfile_name
        dockerfile_path.write_text(
            "\n".join(
                [
                    "FROM python:3.12-slim",
                    "WORKDIR /app",
                    f"ENV PYTHONUNBUFFERED=1 PORT={runtime_port} MCP_PORT={runtime_port} HOST=0.0.0.0",
                    "RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*",
                    "COPY . .",
                    "RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; elif [ -f pyproject.toml ]; then pip install --no-cache-dir .; fi",
                    f"EXPOSE {runtime_port}",
                    f'CMD ["python", "{entry_file}"]',
                    "",
                ]
            )
        )
        dockerignore_path = server_dir / ".dockerignore"
        if not dockerignore_path.exists():
            dockerignore_path.write_text(".git\n__pycache__\n*.pyc\n.env\n")
        return dockerfile_name

    def _build_image_sync(
        self,
        *,
        server_id: str,
        server_dir: Path,
        dockerfile_name: str,
    ) -> str:
        client = self._docker_client_sync()
        image_tag = self._image_tag(server_id)
        self.append_log(server_id, "Building Docker image")
        try:
            build_output = client.api.build(
                path=str(server_dir),
                dockerfile=dockerfile_name,
                tag=image_tag,
                rm=True,
                decode=True,
            )
            for chunk in build_output:
                stream = chunk.get("stream")
                if stream:
                    for line in stream.splitlines():
                        line = line.strip()
                        if line:
                            self.append_log(server_id, line)
                if chunk.get("error"):
                    raise RuntimeError(chunk["error"])
            client.images.get(image_tag)
            return image_tag
        except Exception as exc:
            self.append_log(server_id, f"Docker build failed: {exc}")
            raise

    def _normalize_runtime_env(self, runtime_env: dict | None) -> dict[str, str]:
        if not runtime_env:
            return {}

        normalized: dict[str, str] = {}
        for raw_key, raw_value in runtime_env.items():
            key = str(raw_key or "").strip()
            if not key:
                continue
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                raise RuntimeError(f"Invalid environment variable name: {key}")
            normalized[key] = "" if raw_value is None else str(raw_value)
        return normalized

    def _deploy_python_workspace_sync(
        self,
        server_id: str,
        workspace_dir: Path,
        entry_file: str,
        runtime_port: int,
        runtime_env: dict[str, str] | None,
    ) -> dict:
        if not workspace_dir.exists():
            raise RuntimeError(f"Workspace not found: {workspace_dir}")
        if not (workspace_dir / entry_file).exists():
            raise RuntimeError(f"Entry file not found: {entry_file}")

        self._maybe_adapt_workspace_for_gateway_auth(
            server_id=server_id,
            workspace_dir=workspace_dir,
            entry_file=entry_file,
        )

        dockerfile_name = self._runtime_dockerfile(workspace_dir, entry_file, runtime_port)
        image_tag = self._build_image_sync(
            server_id=server_id,
            server_dir=workspace_dir,
            dockerfile_name=dockerfile_name,
        )

        client = self._docker_client_sync()
        container_name = self._container_name(server_id)
        try:
            existing = client.containers.get(container_name)
            existing.remove(force=True)
        except Exception:
            pass

        normalized_runtime_env = self._normalize_runtime_env(runtime_env)
        if normalized_runtime_env:
            keys = ", ".join(sorted(normalized_runtime_env))
            self.append_log(server_id, f"Runtime env configured: {keys}")

        self.append_log(server_id, f"Starting container on network {settings.DOCKER_NETWORK}")
        try:
            container = client.containers.run(
                image_tag,
                detach=True,
                name=container_name,
                network=settings.DOCKER_NETWORK,
                environment={
                    "PORT": str(runtime_port),
                    "MCP_PORT": str(runtime_port),
                    "HOST": "0.0.0.0",
                    "PYTHONUNBUFFERED": "1",
                    **normalized_runtime_env,
                },
                labels={
                    "mcp.gateway.server_id": server_id,
                    "mcp.gateway.managed": "true",
                },
            )
        except Exception as exc:
            self.append_log(server_id, f"Container start failed: {exc}")
            raise RuntimeError(f"Container start failed: {exc}") from exc

        for _ in range(6):
            container.reload()
            if container.status in {"exited", "dead"}:
                logs = container.logs(tail=80).decode("utf-8", errors="ignore").strip()
                if logs:
                    for line in logs.splitlines()[-20:]:
                        self.append_log(server_id, line)
                tail_lines = [line.strip() for line in logs.splitlines() if line.strip()]
                summary = " | ".join(tail_lines[-3:]) if tail_lines else "no container logs"
                if len(summary) > 400:
                    summary = summary[-400:]
                raise RuntimeError(f"Container exited during startup: {summary}")
            time.sleep(1)

        internal_url = f"http://{container_name}:{runtime_port}"
        self.append_log(server_id, f"Container {container.name} is running")
        self.append_log(server_id, f"Internal upstream URL: {internal_url}")
        return {
            "kind": "docker",
            "container_id": container.id,
            "container_name": container.name,
            "image_tag": image_tag,
            "network": settings.DOCKER_NETWORK,
            "internal_url": internal_url,
            "path": "/mcp",
            "runtime_port": runtime_port,
            "workspace_dir": str(workspace_dir),
            "entry_file": entry_file,
        }

    def _stop_sync(self, config: dict) -> None:
        runtime = config.get("runtime", {})
        if runtime.get("kind") != "docker":
            return
        container_id = runtime.get("container_id") or runtime.get("container_name")
        if not container_id:
            return
        client = self._docker_client_sync()
        try:
            container = client.containers.get(container_id)
            container.stop(timeout=10)
            container.remove(force=True)
        except Exception:
            return

    def _get_status_sync(self, config: dict) -> str:
        runtime = config.get("runtime", {})
        kind = runtime.get("kind")
        if kind == "external":
            return "running"
        if kind != "docker":
            return "stopped"

        container_id = runtime.get("container_id") or runtime.get("container_name")
        if not container_id:
            return "stopped"
        client = self._docker_client_sync()
        try:
            container = client.containers.get(container_id)
            container.reload()
            return "running" if container.status == "running" else "stopped"
        except Exception:
            return "stopped"

    def _get_logs_sync(self, server_id: str, config: dict) -> list[str]:
        combined = list(self._server_logs.get(server_id, []))
        runtime = config.get("runtime", {})
        if runtime.get("kind") == "docker":
            container_id = runtime.get("container_id") or runtime.get("container_name")
            if container_id:
                client = self._docker_client_sync()
                try:
                    container = client.containers.get(container_id)
                    raw_logs = container.logs(tail=200).decode("utf-8", errors="ignore").strip()
                    if raw_logs:
                        for line in raw_logs.splitlines():
                            formatted = line.strip()
                            if formatted:
                                combined.append(formatted)
                except Exception:
                    pass
        elif runtime.get("kind") == "external":
            combined.append(f"External target: {runtime.get('upstream_url')}")

        # Preserve order while removing exact duplicates.
        deduped: list[str] = []
        seen: set[str] = set()
        for line in combined:
            if line in seen:
                continue
            seen.add(line)
            deduped.append(line)
        return deduped

    async def remove_workspace(self, server_id: str) -> None:
        await asyncio.to_thread(self._remove_workspace_sync, server_id)

    def _remove_workspace_sync(self, server_id: str) -> None:
        shutil.rmtree(self.mcp_base_path / server_id, ignore_errors=True)


mcp_host = MCPHostEngine()
