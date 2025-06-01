import asyncio
import logging
import json
from datetime import datetime
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent
from typing import Any

# Enhanced logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("debug-mcp-server")

server = Server("debug-mcp-server")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools."""
    logger.info("Listing tools requested")
    return [
        Tool(
            name="echo",
            description="Echo back the input with timestamp and debug info",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Message to echo back"
                    }
                },
                "required": ["message"]
            }
        ),
        Tool(
            name="debug_info",
            description="Get server debug information",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool execution with enhanced logging."""
    logger.info(f"Tool called: {name} with args: {arguments}")
    
    if name == "echo":
        message = arguments.get("message", "")
        timestamp = datetime.utcnow().isoformat()
        response = f"Echo at {timestamp}: {message}"
        logger.info(f"Echo response: {response}")
        return [TextContent(type="text", text=response)]
    
    elif name == "debug_info":
        debug_data = {
            "server_name": "debug-mcp-server",
            "timestamp": datetime.utcnow().isoformat(),
            "tools_available": ["echo", "debug_info"],
            "resources_available": ["config://settings"],
            "status": "running"
        }
        return [TextContent(type="text", text=json.dumps(debug_data, indent=2))]
    
    else:
        logger.error(f"Unknown tool: {name}")
        raise ValueError(f"Unknown tool: {name}")

@server.list_resources()
async def handle_list_resources() -> list[Resource]:
    """List available resources."""
    logger.info("Resources list requested")
    return [
        Resource(
            uri="config://settings",
            name="Application Settings",
            description="Current application configuration",
            mimeType="application/json"
        ),
        Resource(
            uri="debug://logs",
            name="Debug Logs",
            description="Recent server logs",
            mimeType="text/plain"
        )
    ]

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read resource content."""
    logger.info(f"Resource read requested: {uri}")
    
    if uri == "config://settings":
        config = {
            "version": "1.0", 
            "debug": True,
            "last_updated": datetime.utcnow().isoformat()
        }
        return json.dumps(config, indent=2)
    
    elif uri == "debug://logs":
        return f"Debug logs as of {datetime.utcnow().isoformat()}\nServer is running normally."
    
    else:
        logger.error(f"Unknown resource: {uri}")
        raise ValueError(f"Unknown resource: {uri}")

async def main():
    logger.info("Starting debug MCP server...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="debug-mcp-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
