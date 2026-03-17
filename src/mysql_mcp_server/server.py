import asyncio
import logging
import os
import re
import sys
from mysql.connector import connect, Error
from mcp.server import Server
from mcp.types import Resource, Tool, TextContent, ResourceTemplate
from pydantic import AnyUrl

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mysql_mcp_server")

SYSTEM_DATABASES = {'information_schema', 'mysql', 'performance_schema', 'sys'}


def validate_identifier(name: str) -> str:
    """Validate a MySQL identifier (table/database name) to prevent SQL injection."""
    if not re.match(r'^[a-zA-Z0-9_$]+$', name):
        raise ValueError(f"Invalid identifier '{name}': only alphanumeric, underscore, and $ are allowed")
    return name


def get_db_config():
    """Get database configuration from environment variables."""
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
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": user,
        "password": password,
        "charset": os.getenv("MYSQL_CHARSET", "utf8mb4"),
        "collation": os.getenv("MYSQL_COLLATION", "utf8mb4_unicode_ci"),
        "autocommit": True,
        "sql_mode": os.getenv("MYSQL_SQL_MODE", "TRADITIONAL"),
        "connect_timeout": int(os.getenv("MYSQL_CONNECT_TIMEOUT", "10")),
    }

    if database:
        config["database"] = database
        logger.info(f"Using default database: {database}")
    else:
        logger.info("No default database specified (multi-database mode). Use 'USE <database>' or fully qualified table names.")

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


app = Server("mysql_mcp_server")


@app.list_resources()
async def list_resources() -> list[Resource]:
    """List MySQL tables (or databases if no default database) as resources."""
    config = get_db_config()
    try:
        logger.info(f"Connecting to MySQL with charset: {config.get('charset')}, collation: {config.get('collation')}")
        with connect(**config) as conn:
            logger.info(f"Successfully connected to MySQL server version: {conn.get_server_info()}")
            with conn.cursor() as cursor:
                if "database" not in config:
                    cursor.execute("SHOW DATABASES")
                    databases = cursor.fetchall()
                    logger.info(f"Found databases: {databases}")
                    return [
                        Resource(
                            uri=f"mysql://database/{db[0]}",
                            name=f"Database: {db[0]}",
                            mimeType="text/plain",
                            description=f"MySQL database: {db[0]}"
                        )
                        for db in databases if db[0] not in SYSTEM_DATABASES
                    ]
                else:
                    cursor.execute("SHOW TABLES")
                    tables = cursor.fetchall()
                    logger.info(f"Found tables: {tables}")
                    return [
                        Resource(
                            uri=f"mysql://{table[0]}/data",
                            name=f"Table: {table[0]}",
                            mimeType="text/plain",
                            description=f"Data in table: {table[0]}"
                        )
                        for table in tables
                    ]
    except Error as e:
        error_msg = getattr(e, 'msg', None) or str(e) or 'Unknown MySQL error'
        logger.error(f"Failed to list resources: {error_msg} (errno: {e.errno}, sqlstate: {e.sqlstate})")
        return []


@app.list_resource_templates()
async def list_resource_templates() -> list[ResourceTemplate]:
    """Return available resource templates."""
    return []


@app.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    """Read table contents or list tables in a database."""
    config = get_db_config()
    uri_str = str(uri)
    logger.info(f"Reading resource: {uri_str}")

    if not uri_str.startswith("mysql://"):
        raise ValueError(f"Invalid URI scheme: {uri_str}")

    parts = uri_str[8:].split('/')

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
            logger.error(f"Database error reading database {db_name}: {error_msg} (errno: {e.errno}, sqlstate: {e.sqlstate})")
            raise RuntimeError(f"Database error: {error_msg}")

    table = validate_identifier(parts[0])

    try:
        logger.info(f"Connecting to MySQL with charset: {config.get('charset')}, collation: {config.get('collation')}")
        with connect(**config) as conn:
            logger.info(f"Successfully connected to MySQL server version: {conn.get_server_info()}")
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT * FROM `{table}` LIMIT 100")
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                result = [",".join("" if v is None else str(v) for v in row) for row in rows]
                return "\n".join([",".join(columns)] + result)

    except Error as e:
        error_msg = getattr(e, 'msg', None) or str(e) or 'Unknown MySQL error'
        logger.error(f"Database error reading resource {uri}: {error_msg} (errno: {e.errno}, sqlstate: {e.sqlstate})")
        raise RuntimeError(f"Database error: {error_msg}")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MySQL tools."""
    logger.info("Listing tools...")
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
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute SQL commands."""
    logger.info(f"Calling tool: {name} with arguments: {arguments}")

    if name != "execute_sql":
        raise ValueError(f"Unknown tool: {name}")

    query = arguments.get("query")
    if not query:
        raise ValueError("Query is required")

    config = get_db_config()

    try:
        logger.info(f"Connecting to MySQL with charset: {config.get('charset')}, collation: {config.get('collation')}")
        with connect(**config) as conn:
            logger.info(f"Successfully connected to MySQL server version: {conn.get_server_info()}")
            with conn.cursor() as cursor:
                cursor.execute(query)

                if cursor.description is not None:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    result_lines = [",".join(columns)]
                    result_lines.extend([",".join("" if v is None else str(v) for v in row) for row in rows])
                    return [TextContent(type="text", text="\n".join(result_lines))]
                else:
                    conn.commit()
                    return [TextContent(type="text", text=f"Query executed successfully. Rows affected: {cursor.rowcount}")]

    except Error as e:
        error_msg = getattr(e, 'msg', None) or str(e) or 'Unknown MySQL error'
        logger.error(f"Error executing SQL '{query}': {error_msg} (errno: {e.errno}, sqlstate: {e.sqlstate})")
        return [TextContent(type="text", text=f"Error executing query: {error_msg}")]


async def main():
    """Main entry point to run the MCP server."""
    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()

    print(f"Starting MySQL MCP server (transport: {transport}) with config:", file=sys.stderr)
    config = get_db_config()
    print(f"Host: {config['host']}", file=sys.stderr)
    print(f"Port: {config['port']}", file=sys.stderr)
    print(f"User: {config['user']}", file=sys.stderr)
    print(f"Database: {config.get('database', '(not specified, multi-database mode)')}", file=sys.stderr)

    logger.info("Starting MySQL MCP server...")
    logger.info(f"Database config: {config['host']}/{config.get('database', '*')} as {config['user']}")

    if transport == "sse":
        await _run_sse_server()
    else:
        await _run_stdio_server()


async def _run_stdio_server():
    from mcp.server.stdio import stdio_server
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
    try:
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route
        from starlette.responses import Response
        import uvicorn
    except ImportError:
        logger.error("SSE transport requires additional dependencies. Install with: pip install mysql_mcp_server[sse]")
        raise

    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())
        return Response()

    starlette_app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ]
    )

    host = os.getenv("MCP_SSE_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SSE_PORT", "8000"))
    logger.info(f"Starting SSE server on {host}:{port}")

    server_config = uvicorn.Config(starlette_app, host=host, port=port, log_level="info")
    server = uvicorn.Server(server_config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
