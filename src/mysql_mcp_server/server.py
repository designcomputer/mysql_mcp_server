import asyncio
import logging
import os
import sys
import re
import socket
import time
import subprocess
import traceback
from contextlib import contextmanager
from typing import List, Optional, Tuple, Any

import anyio
from mysql.connector import connect, Error
from mcp.server import Server
from mcp.types import Resource, Tool, TextContent, ToolAnnotations, ResourceTemplate
from pydantic import AnyUrl
from dotenv import load_dotenv

# Load environment variables from .env file if it exists.
# This allows for easy local configuration of database and SSH credentials.
load_dotenv()

# Configure logging to provide visibility into server operations.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mysql_mcp_server")

# System databases that are typically filtered out from resource listings.
SYSTEM_DATABASES = {'information_schema', 'mysql', 'performance_schema', 'sys'}

def validate_identifier(name: str) -> str:
    """
    Validate a MySQL identifier (table or database name) to prevent SQL injection.
    Only allows alphanumeric characters, underscores, and dollar signs.
    """
    if not re.match(r'^[a-zA-Z0-9_$]+$', name):
        raise ValueError(f"Invalid identifier '{name}': only alphanumeric, underscore, and $ are allowed")
    return name

@contextmanager
def maybe_ssh_tunnel():
    """
    Context manager that creates an SSH tunnel if MYSQL_SSH_ENABLE is set to true.
    Yields the (host, port) to use for the database connection.
    Contributed by GeorgeLeex (PR #64).
    """
    use_ssh = os.getenv("MYSQL_SSH_ENABLE", "false").lower() == "true"
    if not use_ssh:
        # Default connection parameters if SSH is disabled.
        yield os.getenv("MYSQL_HOST", "localhost"), int(os.getenv("MYSQL_PORT", "3306"))
        return

    # Load SSH configuration from environment variables.
    ssh_host = os.getenv("MYSQL_SSH_HOST")
    ssh_port = int(os.getenv("MYSQL_SSH_PORT", "22"))
    ssh_user = os.getenv("MYSQL_SSH_USER")
    ssh_key = os.getenv("MYSQL_SSH_KEY_PATH")
    remote_host = os.getenv("MYSQL_SSH_REMOTE_HOST", "localhost")
    remote_port = int(os.getenv("MYSQL_SSH_REMOTE_PORT", "3306"))
    local_port = int(os.getenv("MYSQL_LOCAL_PORT", "3330"))

    # Mask SSH key path in logs for security.
    safe_ssh_key = os.path.basename(ssh_key) if ssh_key else None
    logger.info(f"Starting SSH tunnel: {ssh_user}@{ssh_host}:{ssh_port} -> {local_port}:{remote_host}:{remote_port} (key: {safe_ssh_key})")

    # Build the system SSH command for tunneling.
    ssh_cmd = [
        'ssh',
        '-i', ssh_key,
        '-N', # Do not execute a remote command.
        '-o', 'ExitOnForwardFailure=yes', # Exit if tunnel cannot be established.
        '-o', 'BatchMode=yes',            # Non-interactive mode.
        '-L', f'{local_port}:{remote_host}:{remote_port}', # Local port forwarding.
        f'{ssh_user}@{ssh_host}',
        '-p', str(ssh_port)
    ]
    
    try:
        # Start the SSH process in the background.
        ssh_proc = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(2)  # Give the tunnel a moment to establish.
        
        # Check if process died early.
        if ssh_proc.poll() is not None:
            stderr = ssh_proc.stderr.read().decode()
            raise RuntimeError(f"SSH tunnel process exited prematurely: {stderr}")
            
        yield "127.0.0.1", local_port
    except Exception as e:
        logger.error(f"Error starting SSH tunnel: {e}")
        raise
    finally:
        # Ensure the SSH process is terminated when the context is exited.
        logger.info("Terminating SSH tunnel process.")
        try:
            ssh_proc.terminate()
            ssh_proc.wait(timeout=5)
        except Exception as e:
            logger.error(f"Error terminating SSH tunnel: {e}")

def get_db_config(host=None, port=None):
    """
    Constructs the database connection configuration dictionary from environment variables.
    Validates that required credentials (USER and PASSWORD) are present.
    """
    user = os.getenv("MYSQL_USER")
    password = os.getenv("MYSQL_PASSWORD")
    database = os.getenv("MYSQL_DATABASE")

    if not user:
        logger.error("Missing required database configuration: MYSQL_USER is required")
        raise ValueError("Missing required database configuration")

    if password is None:
        logger.error("MYSQL_PASSWORD environment variable must be set (can be empty string for no password)")
        raise ValueError("Missing required database configuration")

    config = {
        "host": host or os.getenv("MYSQL_HOST", "localhost"),
        "port": port or int(os.getenv("MYSQL_PORT", "3306")),
        "user": user,
        "password": password,
        "charset": os.getenv("MYSQL_CHARSET", "utf8mb4"),
        "collation": os.getenv("MYSQL_COLLATION", "utf8mb4_unicode_ci"),
        "autocommit": True, # Ensure changes are committed immediately if supported.
        "sql_mode": os.getenv("MYSQL_SQL_MODE", "TRADITIONAL"),
        "connect_timeout": int(os.getenv("MYSQL_CONNECT_TIMEOUT", "10")),
        # Compatibility parameters for older MySQL versions (Issue #31)
        "auth_plugin": os.getenv("MYSQL_AUTH_PLUGIN"),
        "use_pure": os.getenv("MYSQL_USE_PURE", "false").lower() == "true",
        "raise_on_warnings": os.getenv("MYSQL_RAISE_ON_WARNINGS", "false").lower() == "true",
    }
    
    # Remove None values
    config = {k: v for k, v in config.items() if v is not None}
    
    # Allow overriding collation/charset to be empty if needed for older versions.
    if config["charset"] == "": del config["charset"]
    if config["collation"] == "": del config["collation"]

    if database:
        config["database"] = database
        logger.info(f"Using default database: {database}")
    else:
        logger.info("No default database specified (multi-database mode).")

    # Configure SSL parameters based on the MYSQL_SSL_MODE environment variable.
    ssl_mode = os.getenv("MYSQL_SSL_MODE", "").upper()
    if ssl_mode == "DISABLED":
        config["ssl_disabled"] = True
    elif ssl_mode == "REQUIRED":
        config["ssl_verify_cert"] = True
    elif ssl_mode == "VERIFY_CA":
        config["ssl_verify_cert"] = True
        ssl_ca = os.getenv("MYSQL_SSL_CA")
        if ssl_ca:
            config["ssl_ca"] = ssl_ca
    elif ssl_mode == "VERIFY_IDENTITY":
        config["ssl_verify_cert"] = True
        config["ssl_verify_identity"] = True
        ssl_ca = os.getenv("MYSQL_SSL_CA")
        if ssl_ca:
            config["ssl_ca"] = ssl_ca

    return config

# Create the MCP Server instance.
app = Server("mysql_mcp_server")

@app.list_resources()
async def list_resources() -> list[Resource]:
    """
    Lists available MySQL tables (or databases if no default database is configured) as resources.
    This allows AI agents to discover what data is available.
    """
    def _sync_list():
        with maybe_ssh_tunnel() as (host, port):
            config = get_db_config(host, port)
            try:
                with connect(**config) as conn:
                    with conn.cursor() as cursor:
                        if "database" not in config:
                            # Multi-database mode: list available databases.
                            cursor.execute("SHOW DATABASES")
                            databases = cursor.fetchall()
                            return [
                                Resource(
                                    uri=f"mysql://database/{db[0]}",
                                    name=f"database_{db[0]}",
                                    mimeType="text/plain",
                                    description=f"MySQL database: {db[0]}"
                                )
                                for db in databases if db[0] not in SYSTEM_DATABASES
                            ]
                        else:
                            # Single-database mode: list tables in the configured database.
                            cursor.execute("SHOW TABLES")
                            tables = cursor.fetchall()
                            resources = []
                            for table in tables:
                                resources.append(
                                    Resource(
                                        uri=f"mysql://{table[0]}/data",
                                        name=f"table_{table[0]}",
                                        mimeType="text/plain",
                                        description=f"Data in table: {table[0]}"
                                    )
                                )
                            return resources
            except Error as e:
                error_msg = getattr(e, 'msg', None) or str(e) or 'Unknown MySQL error'
                logger.error(f"Failed to list resources: {error_msg}")
                return []
                
    return await anyio.to_thread.run_sync(_sync_list)

@app.list_resource_templates()
async def list_resource_templates() -> list[ResourceTemplate]:
    """
    Returns available resource templates. Currently returns an empty list,
    but implemented for better compatibility with tools like Visual Studio Code.
    """
    return []

@app.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    """
    Reads the content of a specific table or lists tables within a database based on the provided URI.
    """
    def _sync_read():
        with maybe_ssh_tunnel() as (host, port):
            config = get_db_config(host, port)
            uri_str = str(uri)
            if not uri_str.startswith("mysql://"):
                raise ValueError(f"Invalid URI scheme: {uri_str}")

            parts = uri_str[8:].split('/')

            # Handle requests to list tables in a specific database.
            if len(parts) >= 2 and parts[0] == "database":
                db_name = validate_identifier(parts[1])
                try:
                    with connect(**config) as conn:
                        with conn.cursor() as cursor:
                            cursor.execute(f"USE `{db_name}`")
                            cursor.execute("SHOW TABLES")
                            tables = cursor.fetchall()
                            result = [f"Tables in database '{db_name}':"]
                            result.extend([table[0] for table in tables])
                            return "\n".join(result)
                except Error as e:
                    error_msg = getattr(e, 'msg', None) or str(e) or 'Unknown MySQL error'
                    raise RuntimeError(f"Database error: {error_msg}")

            # Handle requests to read data from a specific table.
            table = validate_identifier(parts[0])
            try:
                with connect(**config) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(f"SELECT * FROM `{table}` LIMIT 100")
                        columns = [desc[0] for desc in cursor.description]
                        rows = cursor.fetchall()
                        # Format output as simple CSV-like text.
                        result = [",".join("" if v is None else str(v) for v in row) for row in rows]
                        return "\n".join([",".join(columns)] + result)
            except Error as e:
                error_msg = getattr(e, 'msg', None) or str(e) or 'Unknown MySQL error'
                raise RuntimeError(f"Database error: {error_msg}")

    return await anyio.to_thread.run_sync(_sync_read)

@app.list_tools()
async def list_tools() -> list[Tool]:
    """
    Defines the tools available to AI agents via this MCP server.
    """
    return [
        Tool(
            name="execute_sql",
            description="Execute an SQL query on the MySQL server",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SQL query to execute"
                    }
                },
                "required": ["query"]
            },
            annotations=ToolAnnotations(
                title="Execute SQL",
                readOnlyHint=False, # This tool can perform write operations.
                destructiveHint=True # Warn agents that this can be dangerous.
            )
        ),
        Tool(
            name="get_schema_info",
            description="Get comprehensive schema information (Contributed by GeorgeLeex)",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Optional: Specific table name."
                    }
                }
            }
        ),
        Tool(
            name="get_table_sample",
            description="Get a sample of data from a table (Contributed by GeorgeLeex)",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "Table to sample"},
                    "limit": {"type": "integer", "description": "Rows to return (max 20)"}
                },
                "required": ["table_name"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """
    Dispatches tool calls from AI agents to the appropriate implementation logic.
    """
    try:
        logger.info(f"Calling tool: {name} with arguments: {arguments}")

        if name == "execute_sql":
            query = arguments.get("query")
            if not query:
                raise ValueError("Query is required")
            return await run_query(query)
        
        elif name == "get_schema_info":
            table_name = arguments.get("table_name")
            if table_name:
                # Fetch detailed column metadata for a single table.
                query = f"SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{validate_identifier(table_name)}' ORDER BY ORDINAL_POSITION"
            else:
                # Fetch summary information for all tables.
                query = "SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() ORDER BY TABLE_NAME, ORDINAL_POSITION"
            return await run_query(query)

        elif name == "get_table_sample":
            table_name = validate_identifier(arguments.get("table_name"))
            limit = min(arguments.get("limit", 5), 20)
            query = f"SELECT * FROM `{table_name}` LIMIT {limit}"
            return await run_query(query)

        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        logger.error(f"Error in call_tool: {str(e)}")
        logger.error(traceback.format_exc())
        # Return the error as a TextContent so the client can display it.
        # This addresses Issue #50 where errors were not being reported clearly.
        return [TextContent(type="text", text=f"Error calling tool {name}: {str(e)}")]

async def run_query(query: str) -> list[TextContent]:
    """
    A helper function that handles the execution of a SQL query,
    formatting the results based on the query type (SHOW, DESCRIBE, SELECT, or DML).
    Uses anyio.to_thread.run_sync to prevent blocking the async event loop.
    """
    def _sync_run():
        with maybe_ssh_tunnel() as (host, port):
            config = get_db_config(host, port)
            try:
                with connect(**config) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(query)
                        query_upper = query.strip().upper()

                        # Specific handling for 'SHOW TABLES' to provide a cleaner header.
                        if query_upper.startswith("SHOW TABLES"):
                            tables = cursor.fetchall()
                            db_name = config.get("database", "all databases")
                            result = [f"Tables_in_{db_name}"]
                            result.extend([table[0] for table in tables])
                            return [TextContent(type="text", text="\n".join(result))]

                        # Specific handling for inspection queries to format results clearly.
                        elif any(query_upper.startswith(p) for p in ["DESCRIBE ", "DESC ", "SHOW COLUMNS FROM ", "SHOW FIELDS FROM "]):
                            columns = [desc[0] for desc in cursor.description]
                            rows = cursor.fetchall()
                            results = [",".join(columns)]
                            for row in rows:
                                # Convert None values to the string "NULL" for clarity in output.
                                results.append(",".join(str(v) if v is not None else "NULL" for v in row))
                            return [TextContent(type="text", text="\n".join(results))]

                        # Handling for standard result sets (SELECT, etc.).
                        elif cursor.description is not None:
                            columns = [desc[0] for desc in cursor.description]
                            rows = cursor.fetchall()
                            if not rows:
                                return [TextContent(type="text", text="Query executed successfully. No results returned.")]
                            # Format rows as CSV-like text.
                            result = [",".join("" if v is None else str(v) for v in row) for row in rows]
                            return [TextContent(type="text", text="\n".join([",".join(columns)] + result))]

                        # Handling for Data Manipulation Language (DML) queries like INSERT, UPDATE, DELETE.
                        else:
                            conn.commit() # Ensure changes are persistent.
                            return [TextContent(type="text", text=f"Query executed successfully. Rows affected: {cursor.rowcount}")]

            except Error as e:
                # Extract and log specific MySQL error messages.
                error_msg = getattr(e, 'msg', None) or str(e) or 'Unknown MySQL error'
                logger.error(f"Error executing SQL: {error_msg}")
                return [TextContent(type="text", text=f"Error executing query: {error_msg}")]

    return await anyio.to_thread.run_sync(_sync_run)

async def main():
    """
    Main entry point for the MCP server.
    Supports both STDIO (default) and SSE (HTTP) transport modes.
    """
    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
    if transport == "sse":
        await _run_sse_server()
    else:
        await _run_stdio_server()

async def _run_stdio_server():
    """Runs the server using standard input/output streams."""
    from mcp.server.stdio import stdio_server
    logger.info("Starting MySQL MCP server (STDIO)...")
    async with stdio_server() as (read_stream, write_stream):
        try:
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )
        except Exception as e:
            logger.error(f"Server error: {str(e)}", exc_info=True)
            raise

async def _run_sse_server():
    """
    Runs the server using Server-Sent Events (SSE) over HTTP.
    Requires 'starlette' and 'uvicorn' dependencies.
    """
    try:
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route
        from starlette.responses import Response
        import uvicorn
    except ImportError:
        logger.error("SSE transport requires additional dependencies. Install with: pip install mysql_mcp_server[sse]")
        raise

    logger.info("Starting MySQL MCP server (SSE)...")
    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        """Handler for the SSE connection endpoint."""
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())
        return Response()

    # Define the Starlette application with SSE routes.
    starlette_app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ]
    )

    host = os.getenv("MCP_SSE_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SSE_PORT", "8000"))
    
    # Configure and start the Uvicorn server.
    server_config = uvicorn.Config(starlette_app, host=host, port=port, log_level="info")
    server = uvicorn.Server(server_config)
    await server.serve()

if __name__ == "__main__":
    # Start the asyncio event loop.
    asyncio.run(main())
