![Tests](https://github.com/designcomputer/mysql_mcp_server/actions/workflows/test.yml/badge.svg)
![PyPI - Downloads](https://img.shields.io/pypi/dm/mysql-mcp-server)
[![smithery badge](https://smithery.ai/badge/mysql-mcp-server)](https://smithery.ai/server/mysql-mcp-server)
# MySQL MCP Server
A Model Context Protocol (MCP) implementation that enables secure interaction with MySQL databases. This server component facilitates communication between AI applications (hosts/clients) and MySQL databases, making database exploration and analysis safer and more structured through a controlled interface.

> **Note**: MySQL MCP Server is not designed to be used as a standalone server, but rather as a communication protocol implementation between AI applications and MySQL databases.

## Features
- List available MySQL tables as resources
- Read table contents
- Execute SQL queries with proper error handling
- Secure database access through environment variables
- Comprehensive logging

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
MYSQL_HOST=localhost     # Database host
MYSQL_PORT=3306         # Optional: Database port (defaults to 3306 if not specified)
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_database

# Optional: Charset and collation settings for compatibility with older MySQL versions
MYSQL_CHARSET=utf8mb4           # Optional: Character set (defaults to utf8mb4)
MYSQL_COLLATION=utf8mb4_unicode_ci  # Optional: Collation (defaults to utf8mb4_unicode_ci)
MYSQL_SQL_MODE=TRADITIONAL      # Optional: SQL mode (defaults to TRADITIONAL)
```

### Troubleshooting Collation Issues
If you encounter the error "Unknown collation: 'utf8mb4_0900_ai_ci'", this typically means you're connecting to an older MySQL version (5.7 or earlier) that doesn't support the newer collation. The server now automatically uses compatible settings, but you can override them:

For MySQL 5.7 and earlier:
```bash
MYSQL_CHARSET=utf8mb4
MYSQL_COLLATION=utf8mb4_unicode_ci
```

For very old MySQL versions (5.6 and earlier):
```bash
MYSQL_CHARSET=utf8
MYSQL_COLLATION=utf8_unicode_ci
```

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
        // Optional: Add these if you encounter collation issues
        // "MYSQL_CHARSET": "utf8mb4",
        // "MYSQL_COLLATION": "utf8mb4_unicode_ci"
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
        // Optional: Add these if you encounter collation issues
        // "MYSQL_CHARSET": "utf8mb4",
        // "MYSQL_COLLATION": "utf8mb4_unicode_ci"
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
git clone https://github.com/yourusername/mysql_mcp_server.git
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
