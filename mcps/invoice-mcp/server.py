"""
SAMPLE MCP SERVER — Invoice Processor

This is an example of a vertical MCP you can deploy on your platform.
Upload this code via POST /api/mcp/deploy
Get back a URL → plug into Claude Code → it works instantly.

Tools exposed:
- extract_invoice_data    : Parse invoice PDF/text → structured data
- validate_invoice        : Check for errors, duplicates
- get_invoice_summary     : Summarize invoices for a date range
"""

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import json
from datetime import datetime

app = Server("invoice-processor")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="extract_invoice_data",
            description="Extract structured data from invoice text",
            inputSchema={
                "type": "object",
                "properties": {
                    "invoice_text": {
                        "type": "string",
                        "description": "Raw invoice text or description"
                    }
                },
                "required": ["invoice_text"]
            }
        ),
        Tool(
            name="validate_invoice",
            description="Validate invoice for errors or duplicates",
            inputSchema={
                "type": "object",
                "properties": {
                    "invoice_number": {"type": "string"},
                    "amount": {"type": "number"},
                    "vendor": {"type": "string"},
                },
                "required": ["invoice_number", "amount", "vendor"]
            }
        ),
        Tool(
            name="get_invoice_summary",
            description="Get summary of invoices",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                }
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:

    if name == "extract_invoice_data":
        # In production: use LangChain + Claude to extract real data
        text = arguments.get("invoice_text", "")
        result = {
            "invoice_number": "INV-2024-001",
            "vendor": "Extracted from text",
            "amount": 1500.00,
            "due_date": "2024-02-28",
            "line_items": [],
            "raw_input": text[:100],
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "validate_invoice":
        inv_num = arguments.get("invoice_number")
        amount = arguments.get("amount")
        vendor = arguments.get("vendor")
        result = {
            "valid": True,
            "invoice_number": inv_num,
            "checks": {
                "duplicate": False,
                "amount_reasonable": amount < 1000000,
                "vendor_known": True,
            },
            "warnings": [],
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "get_invoice_summary":
        result = {
            "period": f"{arguments.get('start_date')} to {arguments.get('end_date')}",
            "total_invoices": 47,
            "total_amount": 125430.00,
            "pending_approval": 12,
            "overdue": 3,
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    return [TextContent(type="text", text="Tool not found")]


if __name__ == "__main__":
    import asyncio
    asyncio.run(stdio_server(app))
