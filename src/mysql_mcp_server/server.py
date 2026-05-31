import asyncio
import logging
import os
import sys
import re
import socket
import time
import subprocess
from contextlib import contextmanager
from mysql.connector import connect, Error
from mcp.server import Server
from mcp.types import Resource, Tool, TextContent
from pydantic import AnyUrl
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mysql_mcp_server")

@contextmanager
def maybe_ssh_tunnel():
    """
    Creates an SSH tunnel if MYSQL_SSH_ENABLE is true.
    Contributed by GeorgeLeex (PR #64).
    """
    use_ssh = os.getenv("MYSQL_SSH_ENABLE", "false").lower() == "true"
    if not use_ssh:
        yield os.getenv("MYSQL_HOST", "localhost"), int(os.getenv("MYSQL_PORT", "3306"))
        return

    ssh_host = os.getenv("MYSQL_SSH_HOST")
    ssh_port = int(os.getenv("MYSQL_SSH_PORT", "22"))
    ssh_user = os.getenv("MYSQL_SSH_USER")
    ssh_key = os.getenv("MYSQL_SSH_KEY_PATH")
    remote_host = os.getenv("MYSQL_SSH_REMOTE_HOST", "localhost")
    remote_port = int(os.getenv("MYSQL_SSH_REMOTE_PORT", "3306"))
    local_port = int(os.getenv("MYSQL_LOCAL_PORT", "3330"))

    # Mask SSH key path in logs
    safe_ssh_key = os.path.basename(ssh_key) if ssh_key else None
    logger.info(f"Starting SSH tunnel: {ssh_user}@{ssh_host}:{ssh_port} -> {local_port}:{remote_host}:{remote_port} (key: {safe_ssh_key})")

    # Build the SSH command
    ssh_cmd = [
        'ssh',
        '-i', ssh_key,
        '-N',
        '-L', f'{local_port}:{remote_host}:{remote_port}',
        f'{ssh_user}@{ssh_host}',
        '-p', str(ssh_port)
    ]
    
    try:
        ssh_proc = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(2)  # Wait for tunnel to be ready
        yield "127.0.0.1", local_port
    except Exception as e:
        logger.error(f"Error starting SSH tunnel: {e}")
        raise
    finally:
        logger.info("Terminating SSH tunnel process.")
        try:
            ssh_proc.terminate()
            ssh_proc.wait(timeout=5)
        except Exception as e:
            logger.error(f"Error terminating SSH tunnel: {e}")

def get_db_config(host=None, port=None):
    """Get database configuration from environment variables."""
    config = {
        "host": host or os.getenv("MYSQL_HOST", "localhost"),
        "port": port or int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER"),
        "password": os.getenv("MYSQL_PASSWORD"),
        "database": os.getenv("MYSQL_DATABASE"),
        "charset": os.getenv("MYSQL_CHARSET", "utf8mb4"),
        "collation": os.getenv("MYSQL_COLLATION", "utf8mb4_unicode_ci"),
        "autocommit": True,
        "sql_mode": os.getenv("MYSQL_SQL_MODE", "TRADITIONAL")
    }

    # Remove None values
    config = {k: v for k, v in config.items() if v is not None}

    if not all([config.get("user"), config.get("password"), config.get("database")]):
        logger.error("Missing required database configuration (USER, PASSWORD, DATABASE).")
        raise ValueError("Missing required database configuration")

    return config

# Initialize server
app = Server("mysql_mcp_server")

@app.list_resources()
async def list_resources() -> list[Resource]:
    """List MySQL tables as resources."""
    with maybe_ssh_tunnel() as (host, port):
        config = get_db_config(host, port)
        try:
            with connect(**config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SHOW TABLES")
                    tables = cursor.fetchall()
                    resources = []
                    for table in tables:
                        resources.append(
                            Resource(
                                uri=f"mysql://{table[0]}/data",
                                name=f"Table: {table[0]}",
                                mimeType="text/plain",
                                description=f"Data in table: {table[0]}"
                            )
                        )
                    return resources
        except Error as e:
            logger.error(f"Failed to list resources: {str(e)}")
            return []

@app.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    """Read table contents."""
    with maybe_ssh_tunnel() as (host, port):
        config = get_db_config(host, port)
        uri_str = str(uri)
        if not uri_str.startswith("mysql://"):
            raise ValueError(f"Invalid URI scheme: {uri_str}")

        parts = uri_str[8:].split('/')
        table = parts[0]

        try:
            with connect(**config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SELECT * FROM {table} LIMIT 100")
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    result = [",".join(map(str, row)) for row in rows]
                    return "\n".join([",".join(columns)] + result)
        except Error as e:
            logger.error(f"Database error reading resource {uri}: {str(e)}")
            raise RuntimeError(f"Database error: {str(e)}")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MySQL tools."""
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
            }
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
    """Execute SQL commands."""
    logger.info(f"Calling tool: {name} with arguments: {arguments}")

    if name == "execute_sql":
        query = arguments.get("query")
        if not query:
            raise ValueError("Query is required")
        return await run_query(query)
    
    elif name == "get_schema_info":
        table_name = arguments.get("table_name")
        if table_name:
            query = f"""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table_name}'
                ORDER BY ORDINAL_POSITION
            """
        else:
            query = """
                SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                ORDER BY TABLE_NAME, ORDINAL_POSITION
            """
        return await run_query(query)

    elif name == "get_table_sample":
        table_name = arguments.get("table_name")
        limit = min(arguments.get("limit", 5), 20)
        query = f"SELECT * FROM `{table_name}` LIMIT {limit}"
        return await run_query(query)

    else:
        raise ValueError(f"Unknown tool: {name}")

async def run_query(query: str) -> list[TextContent]:
    """Helper to run a query with current formatting logic and SSH support."""
    with maybe_ssh_tunnel() as (host, port):
        config = get_db_config(host, port)
        try:
            with connect(**config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    query_upper = query.strip().upper()

                    # SHOW TABLES
                    if query_upper.startswith("SHOW TABLES"):
                        tables = cursor.fetchall()
                        result = ["Tables_in_" + config["database"]]
                        result.extend([table[0] for table in tables])
                        return [TextContent(type="text", text="\n".join(result))]

                    # DESCRIBE / SHOW COLUMNS
                    elif any(query_upper.startswith(p) for p in ["DESCRIBE ", "DESC ", "SHOW COLUMNS FROM ", "SHOW FIELDS FROM "]):
                        columns = [desc[0] for desc in cursor.description]
                        rows = cursor.fetchall()
                        results = [",".join(columns)]
                        for row in rows:
                            results.append(",".join(str(v) if v is not None else "NULL" for v in row))
                        return [TextContent(type="text", text="\n".join(results))]

                    # SELECT / Other result sets
                    elif cursor.description is not None:
                        columns = [desc[0] for desc in cursor.description]
                        rows = cursor.fetchall()
                        if not rows:
                            return [TextContent(type="text", text="Query executed successfully. No results returned.")]
                        result = [",".join(map(str, row)) for row in rows]
                        return [TextContent(type="text", text="\n".join([",".join(columns)] + result))]

                    # DML
                    else:
                        conn.commit()
                        return [TextContent(type="text", text=f"Query executed successfully. Rows affected: {cursor.rowcount}")]

        except Error as e:
            logger.error(f"Error executing SQL: {e}")
            return [TextContent(type="text", text=f"Error executing query: {str(e)}")]

async def main():
    """Main entry point to run the MCP server."""
    from mcp.server.stdio import stdio_server
    logger.info("Starting MySQL MCP server...")
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

if __name__ == "__main__":
    asyncio.run(main())
