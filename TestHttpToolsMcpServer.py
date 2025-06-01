import asyncio
import logging
import json
import aiohttp
from datetime import datetime
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent
from typing import Any, Optional

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("debug-mcp-server")
server = Server("debug-mcp-server")

http_session: Optional[aiohttp.ClientSession] = None

async def get_http_session() -> aiohttp.ClientSession:
    global http_session
    if http_session is None or http_session.closed:
        timeout = aiohttp.ClientTimeout(total=30)
        http_session = aiohttp.ClientSession(timeout=timeout)
    return http_session

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools."""
    logger.info("Listing tools requested")
    return [
        Tool(
            name="debug_info",
            description="Get server debug information",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
        Tool(
            name="fetch_api_data",
            description="Fetch data from a REST API endpoint",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type":"string",
                        "description": "API endpoint URL"
                    },
                "method": {
                    "type": "string",
                    "enum": ["GET","POST","PUT","DELETE"],
                    "default": "GET",
                    "description": "Http Method"
                },
                "headers": {
                    "type":"object",
                    "description": "Optional HTTP headers",
                    "additionalProperties": {"type":"string"}
                },
                "body": {
                    "type":"string",
                    "description": "Request body (for POST/PUT)"
                }     
                },
                "required":["url"]
            }
        ),
        Tool(
             name="weather_api",
            description="Get weather information for a city",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name"
                    }
                },
                "required": ["city"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool execution with enhanced logging"""
    logger.info(f"Tool called: {name} with args: {arguments}")

    if name == "debug_info":
        debug_data = {
            "server_name": "debug-mcp-server",
            "timestamp": datetime.utcnow().isoformat(),
            "tools_available": ["debug_info", "fetch_api_data", "weather_api"],
            "resources_available": ["config://settings", "debug://logs"],
            "status": "running"
        }   
        return [TextContent(type="text", text=json.dumps(debug_data, indent=2))]

    elif name == "fetch_api_data":
        return await handle_api_call(arguments)
    elif name == "weather_api":
        return await handle_weather_api(arguments)
    else:
        logger.error(f"Unknown tool: {name}")
        return ValueError(f"Unknown tool:{name}")
    
async def handle_api_call(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle generic API calls."""
    url = arguments.get("url")
    method = arguments.get("method", "GET").upper()
    headers = arguments.get("headers", {})
    body = arguments.get("body")
    
    try:
        session = await get_http_session()
        
        # Prepare request parameters
        kwargs = {
            "url": url,
            "headers": headers,
            "ssl": False  # For development - use True in production
        }
        
        if body and method in ["POST", "PUT", "PATCH"]:
            kwargs["data"] = body
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
        
        logger.info(f"Making {method} request to {url}")
        
        async with session.request(method, **kwargs) as response:
            response_text = await response.text()
            
            result = {
                "status_code": response.status,
                "headers": dict(response.headers),
                "body": response_text,
                "url": str(response.url),
                "method": method
            }
            
            logger.info(f"API call completed with status {response.status}")
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
    except aiohttp.ClientError as e:
        logger.error(f"HTTP client error: {e}")
        error_result = {
            "error": "HTTP Client Error",
            "message": str(e),
            "url": url,
            "method": method
        }
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    except Exception as e:
        logger.error(f"Unexpected error during API call: {e}")
        error_result = {
            "error": "Unexpected Error",
            "message": str(e),
            "url": url,
            "method": method
        }
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]

async def handle_weather_api(arguments: dict[str, Any]) -> list[TextContent]:
    """Handle weather API calls using a free service."""
    city = arguments.get("city")
    
    # Using a free weather API (replace with your preferred service)
    url = f"https://api.openweathermap.org/data/2.5/weather"
    
    # Note: You'll need to get a free API key from OpenWeatherMap
    # For demo purposes, we'll use a mock response
    try:
        session = await get_http_session()
        
        params = {
            "q": city,
            "appid": "your_api_key_here",  # Replace with actual API key
            "units": "metric"
        }
        
        # For demo, let's create a mock response
        mock_weather_data = {
            "city": city,
            "temperature": "22°C",
            "description": "Partly cloudy",
            "humidity": "65%",
            "wind_speed": "10 km/h",
            "note": "This is mock data. Replace with real API key for actual data."
        }
        
        logger.info(f"Weather data requested for {city}")
        return [TextContent(type="text", text=json.dumps(mock_weather_data, indent=2))]
        
    except Exception as e:
        logger.error(f"Weather API error: {e}")
        error_result = {
            "error": "Weather API Error",
            "message": str(e),
            "city": city
        }
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]

async def main():
    """Main server function with proper cleanup."""
    logger.info("Starting debug MCP server...")
    
    try:
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
    finally:
        # Clean up HTTP session
        global http_session
        if http_session and not http_session.closed:
            await http_session.close()
            logger.info("HTTP session closed")

if __name__ == "__main__":
    asyncio.run(main())

