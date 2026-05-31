import pytest
from mysql_mcp_server.server import app, list_tools, list_resources, read_resource, call_tool, validate_identifier, get_db_config
from pydantic import AnyUrl


def test_server_initialization():
    """Test that the server initializes correctly."""
    assert app.name == "mysql_mcp_server"


@pytest.mark.asyncio
async def test_list_tools():
    """Test that list_tools returns expected tools."""
    tools = await list_tools()
    assert len(tools) == 3
    assert any(t.name == "execute_sql" for t in tools)
    assert any(t.name == "get_schema_info" for t in tools)
    assert any(t.name == "get_table_sample" for t in tools)


@pytest.mark.asyncio
async def test_call_tool_invalid_name():
    """Test calling a tool with an invalid name."""
    response = await call_tool("invalid_tool", {})
    assert len(response) == 1
    assert "Error calling tool" in response[0].text
    assert "Unknown tool" in response[0].text


@pytest.mark.asyncio
async def test_call_tool_missing_query():
    """Test calling execute_sql without a query."""
    response = await call_tool("execute_sql", {})
    assert len(response) == 1
    assert "Error calling tool" in response[0].text
    assert "Query is required" in response[0].text


def test_validate_identifier_valid():
    """Test validate_identifier with valid names."""
    assert validate_identifier("users") == "users"
    assert validate_identifier("user_table") == "user_table"
    assert validate_identifier("Table123") == "Table123"
    assert validate_identifier("my$table") == "my$table"


def test_validate_identifier_invalid():
    """Test validate_identifier rejects dangerous input."""
    with pytest.raises(ValueError, match="Invalid identifier"):
        validate_identifier("users; DROP TABLE users")
    with pytest.raises(ValueError, match="Invalid identifier"):
        validate_identifier("user table")
    with pytest.raises(ValueError, match="Invalid identifier"):
        validate_identifier("users'--")
    with pytest.raises(ValueError, match="Invalid identifier"):
        validate_identifier("users`inject")


def test_get_db_config_optional_database(monkeypatch):
    """Test that MYSQL_DATABASE is optional."""
    monkeypatch.setenv("MYSQL_USER", "testuser")
    monkeypatch.setenv("MYSQL_PASSWORD", "testpass")
    monkeypatch.delenv("MYSQL_DATABASE", raising=False)

    config = get_db_config()
    assert "database" not in config
    assert config["user"] == "testuser"


def test_get_db_config_with_database(monkeypatch):
    """Test that MYSQL_DATABASE is included when set."""
    monkeypatch.setenv("MYSQL_USER", "testuser")
    monkeypatch.setenv("MYSQL_PASSWORD", "testpass")
    monkeypatch.setenv("MYSQL_DATABASE", "mydb")

    config = get_db_config()
    assert config["database"] == "mydb"


def test_get_db_config_missing_user(monkeypatch):
    """Test that missing MYSQL_USER raises ValueError."""
    monkeypatch.delenv("MYSQL_USER", raising=False)
    monkeypatch.setenv("MYSQL_PASSWORD", "testpass")

    with pytest.raises(ValueError, match="Missing required database configuration"):
        get_db_config()


def test_get_db_config_missing_password(monkeypatch):
    """Test that missing MYSQL_PASSWORD raises ValueError."""
    monkeypatch.setenv("MYSQL_USER", "testuser")
    monkeypatch.delenv("MYSQL_PASSWORD", raising=False)

    with pytest.raises(ValueError, match="Missing required database configuration"):
        get_db_config()


@pytest.mark.asyncio
@pytest.mark.skipif(
    not all([
        pytest.importorskip("mysql.connector"),
        pytest.importorskip("mysql_mcp_server")
    ]),
    reason="MySQL connection not available"
)
async def test_list_resources():
    """Test listing resources (requires database connection)."""
    try:
        resources = await list_resources()
        assert isinstance(resources, list)
    except ValueError as e:
        if "Missing required database configuration" in str(e):
            pytest.skip("Database configuration not available")
        raise
