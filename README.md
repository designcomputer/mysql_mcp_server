![Tests](https://github.com/designcomputer/mysql_mcp_server/actions/workflows/test.yml/badge.svg)
![PyPI - Downloads](https://img.shields.io/pypi/dm/mysql-mcp-server)
[![smithery badge](https://smithery.ai/badge/mysql-mcp-server)](https://smithery.ai/server/mysql-mcp-server)
[![MseeP.ai Security Assessment Badge](https://mseep.net/mseep-audited.png)](https://mseep.ai/app/designcomputer-mysql-mcp-server)
# MySQL MCP Server
A Model Context Protocol (MCP) implementation that enables secure interaction with MySQL databases. This server component facilitates communication between AI applications (hosts/clients) and MySQL databases, making database exploration and analysis safer and more structured through a controlled interface.

> **Note**: MySQL MCP Server is not designed to be used as a standalone server, but rather as a communication protocol implementation between AI applications and MySQL databases.

## Features
- List available MySQL tables as resources
- Read table contents
- Execute SQL queries with proper error handling
- Secure database access through environment variables
- Comprehensive logging
- SSL/TLS connection support
- Multi-database mode (optional `MYSQL_DATABASE`)
- SSE/HTTP transport support (`MCP_TRANSPORT=sse`)

## Installation
### Manual Installation
```bash
pip install mysql-mcp-server
```

### Installing via Smithery
To install MySQL MCP Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/mysql-mcp-server):
```bash
npx -y @smithery/cli install mysql-mcp-server --client claude
```

## Configuration
Set the following environment variables:
```bash
MYSQL_HOST=localhost        # Database host (default: localhost)
MYSQL_PORT=3306             # Optional: Database port (default: 3306)
MYSQL_USER=your_username    # Required
MYSQL_PASSWORD=your_password  # Required (can be empty string for no password)
MYSQL_DATABASE=your_database  # Optional: Default database (omit for multi-database mode)
MYSQL_CHARSET=utf8mb4       # Optional: Character set (default: utf8mb4)
MYSQL_COLLATION=utf8mb4_unicode_ci  # Optional: Collation (default: utf8mb4_unicode_ci)
MYSQL_SSL_MODE=DISABLED     # Optional: SSL mode (DISABLED, REQUIRED, VERIFY_CA, VERIFY_IDENTITY)
MYSQL_CONNECT_TIMEOUT=10    # Optional: Connection timeout in seconds (default: 10)
MCP_TRANSPORT=stdio         # Optional: Transport mode (stdio [default] or sse)
MCP_SSE_HOST=127.0.0.1      # Optional: SSE server host (default: 127.0.0.1, only used with MCP_TRANSPORT=sse)
MCP_SSE_PORT=8000           # Optional: SSE server port (default: 8000, only used with MCP_TRANSPORT=sse)
```

### Multi-Database Mode
When `MYSQL_DATABASE` is not set, the server operates in multi-database mode:
- `list_resources` returns all user databases (system databases are filtered out)
- Use `USE <database>` in SQL queries to select a database
- Use fully qualified table names like `mydb.mytable`

```json
"env": {
  "MYSQL_HOST": "localhost",
  "MYSQL_USER": "your_username",
  "MYSQL_PASSWORD": "your_password"
}
```

### SSE/HTTP Transport
To run the server as an HTTP/SSE server (useful for private deployments or agent frameworks):

```bash
pip install "mysql-mcp-server[sse]"
MCP_TRANSPORT=sse mysql_mcp_server
```

Or in Docker:
```bash
docker run -e MCP_TRANSPORT=sse -e MCP_SSE_HOST=0.0.0.0 -e MCP_SSE_PORT=8000 \
  -e MYSQL_USER=... -e MYSQL_PASSWORD=... mysql-mcp-server
```

> **Security note:** The SSE server binds to `127.0.0.1` by default. Only expose to `0.0.0.0` in trusted network environments.

## Usage
### With Claude Desktop
Add this to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "mysql": {
      "command": "uvx",
      "args": [
        "--from",
        "mysql-mcp-server",
        "mysql_mcp_server"
      ],
      "env": {
        "MYSQL_HOST": "localhost",
        "MYSQL_PORT": "3306",
        "MYSQL_USER": "your_username",
        "MYSQL_PASSWORD": "your_password",
        "MYSQL_DATABASE": "your_database"
      }
    }
  }
}
```

### With Visual Studio Code
Add this to your `mcp.json`:
```json
{
  "servers": {
    "mysql": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "--from",
        "mysql-mcp-server",
        "mysql_mcp_server"
      ],
      "env": {
        "MYSQL_HOST": "localhost",
        "MYSQL_PORT": "3306",
        "MYSQL_USER": "your_username",
        "MYSQL_PASSWORD": "your_password",
        "MYSQL_DATABASE": "your_database"
      }
    }
  }
}
```
Note: Will need to install [uv](https://docs.astral.sh/uv/) for this to work.

### SSL Connection Issues
If you encounter SSL-related errors (e.g., `error:0A000102:SSL routines::unsupported protocol`), you can disable SSL:
```json
"env": {
  "MYSQL_SSL_MODE": "DISABLED",
  ...
}
```

### Empty Password
If your MySQL installation uses no password, set `MYSQL_PASSWORD` to an empty string:
```json
"env": {
  "MYSQL_PASSWORD": "",
  ...
}
```

### Debugging with MCP Inspector
While MySQL MCP Server isn't intended to be run standalone or directly from the command line with Python, you can use the MCP Inspector to debug it.

The MCP Inspector provides a convenient way to test and debug your MCP implementation:

```bash
# Install dependencies
pip install -r requirements.txt
# Use the MCP Inspector for debugging (do not run directly with Python)
```

The MySQL MCP Server is designed to be integrated with AI applications like Claude Desktop and should not be run directly as a standalone Python program.

## Development
```bash
# Clone the repository
git clone https://github.com/designcomputer/mysql_mcp_server.git
cd mysql_mcp_server
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
# Install development dependencies
pip install -r requirements-dev.txt
# Run tests
pytest
```

## Security Considerations
- Never commit environment variables or credentials
- Use a database user with minimal required permissions
- Consider implementing query whitelisting for production use
- Monitor and log all database operations
- Do not expose `MYSQL_PASSWORD` as a Docker `ENV` instruction — pass it at runtime

## Security Best Practices
This MCP implementation requires database access to function. For security:
1. **Create a dedicated MySQL user** with minimal permissions
2. **Never use root credentials** or administrative accounts
3. **Restrict database access** to only necessary operations
4. **Enable logging** for audit purposes
5. **Regular security reviews** of database access

See [MySQL Security Configuration Guide](https://github.com/designcomputer/mysql_mcp_server/blob/main/SECURITY.md) for detailed instructions on:
- Creating a restricted MySQL user
- Setting appropriate permissions
- Monitoring database access
- Security best practices

⚠️ IMPORTANT: Always follow the principle of least privilege when configuring database access.

## License
MIT License - see LICENSE file for details.

## Contributing
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
