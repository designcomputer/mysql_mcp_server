![Tests](https://github.com/designcomputer/mysql_mcp_server/actions/workflows/test.yml/badge.svg)
[![smithery badge](https://smithery.ai/badge/mysql-mcp-server)](https://smithery.ai/server/mysql-mcp-server)
# MySQL MCP Server

A Model Context Protocol (MCP) server that enables secure interaction with MySQL databases. This server allows AI assistants to list tables, read data, and execute SQL queries through a controlled interface, making database exploration and analysis safer and more structured.

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

To install MySQL Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/mysql-mcp-server):

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
      }
    }
  }
}
```

or 
```json
{
  "mcpServers": {
    "mysql": {
      "command": "python",
      "args": [
        "-m", 
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


### As a standalone server

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python -m mysql_mcp_server
```

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

This MCP server requires database access to function. For security:

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
