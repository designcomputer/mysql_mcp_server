[![Tests](https://github.com/designcomputer/mysql_mcp_server/actions/workflows/test.yml/badge.svg)](https://github.com/designcomputer/mysql_mcp_server/actions)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/mysql-mcp-server)](https://pypi.org/project/mysql-mcp-server/)
[![Smithery Badge](https://smithery.ai/badge/designcomputer/mysql-mcp-server)](https://smithery.ai/server/designcomputer/mysql-mcp-server)
[![AgentAudit Safe](https://img.shields.io/badge/AgentAudit-safe-brightgreen)](https://www.agentaudit.dev/packages/mysql-mcp-server)
[![MCPSafe](https://api.mcpsafe.io/badge/github/designcomputer/mysql_mcp_server.svg)](https://mcpsafe.io/registry/github/designcomputer/mysql_mcp_server)
# MySQL MCP Server
A Model Context Protocol (MCP) implementation that enables secure interaction with MySQL databases. This server component facilitates communication between AI applications (hosts/clients) and MySQL databases, making database exploration and analysis safer and more structured through a controlled interface.

> **Note**: MySQL MCP Server supports both standard input/output (STDIO) and Streamable HTTP (SSE) transport modes. The SSE mode is recommended for remote/self-hosted deployments.

## Deployment options
- **Hosted** — [Fronteir AI](https://fronteir.ai/mcp/designcomputer-mysql-mcp-server) runs the server for you; no local setup required.
- **Local** — [Smithery](https://smithery.ai/server/designcomputer/mysql-mcp-server) installs and runs the server on your own machine.

## Features
- List available MySQL tables as resources
- Read table contents
- Execute SQL queries with proper error handling
- **Multi-database mode** (Optional `MYSQL_DATABASE`)
- **SSE/HTTP transport support** (`MCP_TRANSPORT=sse`)
- **SSH Tunneling support**
- **Comprehensive schema information**
- **Table data sampling**
- Secure database access through environment variables
- Comprehensive logging

## Installation
### Manual Installation
```bash
pip install mysql-mcp-server
```

### Installing via Smithery
To install MySQL MCP Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/designcomputer/mysql-mcp-server):
```bash
npx -y @smithery/cli install designcomputer/mysql-mcp-server --client claude
```

## Configuration
Set the following environment variables:
```bash
MYSQL_HOST=localhost     # Database host
MYSQL_PORT=3306         # Optional: Database port (defaults to 3306 if not specified)
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_database # Optional: Omit for multi-database mode

# Advanced Configuration
MYSQL_SSL_MODE=DISABLED  # DISABLED, REQUIRED, VERIFY_CA, VERIFY_IDENTITY
MYSQL_CONNECT_TIMEOUT=10 # Timeout in seconds

# Compatibility (Optional)
MYSQL_CHARSET=utf8mb4
MYSQL_COLLATION=utf8mb4_unicode_ci
MYSQL_AUTH_PLUGIN=       # e.g., mysql_native_password for older MySQL versions
MYSQL_USE_PURE=false     # Use pure Python implementation
MYSQL_RAISE_ON_WARNINGS=false

# SSE Transport (Optional)
MCP_TRANSPORT=stdio      # stdio or sse
MCP_SSE_HOST=0.0.0.0     # Listen on all interfaces (required for Docker/hosting)
PORT=8000                # HTTP port (fallback for MCP_SSE_PORT)

# SSH Tunneling (Optional)
MYSQL_SSH_ENABLE=false   # Set to true to enable
MYSQL_SSH_HOST=          # SSH jump host
MYSQL_SSH_PORT=22        # SSH port
MYSQL_SSH_USER=          # SSH username
MYSQL_SSH_KEY_PATH=      # Path to SSH private key
MYSQL_SSH_REMOTE_HOST=localhost # Host from the perspective of the jump host
MYSQL_SSH_REMOTE_PORT=3306
MYSQL_LOCAL_PORT=3330
```

### Multi-Database Mode
When `MYSQL_DATABASE` is not set, the server operates in multi-database mode:
- `list_resources` returns all user databases (system databases are filtered out)
- Use `USE <database>` in SQL queries to select a database
- Use fully qualified table names like `mydb.mytable`

## Available Tools

### `execute_sql`
Executes any standard SQL query.
- **Arguments:** `query` (string)
- **Features:** Supports `SELECT`, `SHOW`, `DESCRIBE`, and DML (`INSERT`, `UPDATE`, `DELETE`). DML operations are marked with a destructive hint.

### `get_schema_info`
Provides detailed metadata about database structures.
- **Arguments:** `table_name` (optional string)
- **Output:** Column names, types, nullability, default values, and comments.

### `get_table_sample`
Fetches a representative sample of data.
- **Arguments:** `table_name` (string), `limit` (optional integer, max 20)
- **Use Case:** Quickly understand data formats and content without fetching large result sets.

## Usage
### With Claude Desktop
Add this to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "mysql": {
      "command": "uv",
      "args": [
        "--directory",
        "path/to/mysql_mcp_server",
        "run",
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

For more detailed examples and agent-specific guidance, see [MCP_USECASES.md](MCP_USECASES.md).

### With Visual Studio Code
Add this to your `mcp.json`:
```json
{
  "mcpServers": {
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
Note: Will need to install uv for this to work

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
- **Identifier Validation:** Built-in protection against SQL injection via strict regex whitelisting for database and table names.
- **Encrypted Access:** Full support for SSL/TLS and SSH Tunneling for secure remote connections.
- **Log Privacy:** Passwords and SSH private keys are automatically masked in server logs.
- **Least Privilege:** Always use a dedicated MySQL user with minimal required permissions.

See [SECURITY.md](SECURITY.md) for a comprehensive guide on securing your deployment.

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
