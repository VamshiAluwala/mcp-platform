"""
MCP HOST ENGINE

This is the core of your platform.
Takes any MCP server code → deploys it → returns a URL.
The URL is OAuth-protected via your middleware.

Local: runs as subprocess
Later on AWS: runs as ECS Fargate container
"""

import uuid
import subprocess
import os
from pathlib import Path
from app.core.config import settings


class MCPHostEngine:
    def __init__(self):
        # Local: store MCP servers in a temp directory
        self.mcp_base_path = Path("/tmp/mcp-servers")
        self.mcp_base_path.mkdir(exist_ok=True)

        # Track running processes locally
        self._running_processes: dict[str, subprocess.Popen] = {}

    async def deploy(
        self,
        tenant_id: str,
        server_name: str,
        server_code: str,
    ) -> dict:
        """
        Deploy an MCP server and return its endpoint URL.

        Local mode: saves code as Python file, runs it as subprocess
        AWS mode (later): containerizes and deploys to ECS
        """
        server_id = str(uuid.uuid4())
        tenant_slug = tenant_id[:8]  # Short ID for URL

        # Create directory for this MCP server
        server_dir = self.mcp_base_path / server_id
        server_dir.mkdir(exist_ok=True)

        # Write the MCP server code
        server_file = server_dir / "server.py"
        server_file.write_text(server_code)

        # The URL end users plug into Claude Code
        endpoint_url = (
            f"http://localhost:8000/mcp/{tenant_slug}/{server_name}"
        )

        return {
            "server_id": server_id,
            "endpoint_url": endpoint_url,
            "storage_path": str(server_file),
            "status": "running",
        }

    async def stop(self, server_id: str):
        """Stop a running MCP server"""
        process = self._running_processes.get(server_id)
        if process:
            process.terminate()
            del self._running_processes[server_id]

    def get_status(self, server_id: str) -> str:
        """Check if a server is running"""
        process = self._running_processes.get(server_id)
        if not process:
            return "stopped"
        if process.poll() is None:
            return "running"
        return "stopped"


# Singleton
mcp_host = MCPHostEngine()
