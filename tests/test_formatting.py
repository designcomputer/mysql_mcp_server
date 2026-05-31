import pytest
from unittest.mock import MagicMock, patch
from mysql_mcp_server.server import call_tool
from mcp.types import TextContent

@pytest.mark.asyncio
@patch("mysql_mcp_server.server.connect")
@patch("mysql_mcp_server.server.get_db_config")
async def test_call_tool_describe_formatting(mock_get_config, mock_connect):
    """Test that DESCRIBE queries are formatted correctly with NULL handling."""
    mock_get_config.return_value = {"database": "test_db"}
    
    # Mock cursor behavior
    mock_cursor = MagicMock()
    mock_cursor.description = [("Field",), ("Type",), ("Null",)]
    # Simulate DESCRIBE output: (Field, Type, Null)
    mock_cursor.fetchall.return_value = [
        ("id", "int", "NO"),
        ("name", "varchar", "YES"),
        ("extra", "text", None) # Test NULL handling
    ]
    
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    response = await call_tool("execute_sql", {"query": "DESCRIBE users"})
    
    assert len(response) == 1
    assert isinstance(response[0], TextContent)
    
    lines = response[0].text.split("\n")
    assert lines[0] == "Field,Type,Null"
    assert lines[1] == "id,int,NO"
    assert lines[2] == "name,varchar,YES"
    assert lines[3] == "extra,text,NULL" # NULL should be converted to string "NULL"

@pytest.mark.asyncio
@patch("mysql_mcp_server.server.connect")
@patch("mysql_mcp_server.server.get_db_config")
async def test_call_tool_empty_results(mock_get_config, mock_connect):
    """Test handling of queries that return no results."""
    mock_get_config.return_value = {"database": "test_db"}
    
    mock_cursor = MagicMock()
    mock_cursor.description = [("id",)]
    mock_cursor.fetchall.return_value = []
    
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    response = await call_tool("execute_sql", {"query": "SELECT * FROM empty_table"})
    
    assert len(response) == 1
    assert "No results returned" in response[0].text

@pytest.mark.asyncio
@patch("mysql_mcp_server.server.connect")
@patch("mysql_mcp_server.server.get_db_config")
async def test_call_tool_show_tables(mock_get_config, mock_connect):
    """Test SHOW TABLES formatting."""
    mock_get_config.return_value = {"database": "test_db"}
    
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [("users",), ("orders",)]
    
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    response = await call_tool("execute_sql", {"query": "SHOW TABLES"})
    
    assert len(response) == 1
    assert "Tables_in_test_db" in response[0].text
    assert "users" in response[0].text
    assert "orders" in response[0].text

@pytest.mark.asyncio
@patch("mysql_mcp_server.server.connect")
@patch("mysql_mcp_server.server.get_db_config")
async def test_list_resources_identifier_safe(mock_get_config, mock_connect):
    """Test that resources have identifier-safe names for strict LLMs (Issue #39)."""
    from mysql_mcp_server.server import list_resources
    
    # Mock for single-database mode
    mock_get_config.return_value = {"database": "test_db", "user": "u", "password": "p"}
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [("users",), ("products",)]
    
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    resources = await list_resources()
    
    assert len(resources) == 2
    # Should be table_name, not "Table: name"
    assert resources[0].name == "table_users"
    assert resources[1].name == "table_products"
    assert str(resources[0].uri) == "mysql://users/data"

@pytest.mark.asyncio
@patch("mysql_mcp_server.server.connect")
@patch("mysql_mcp_server.server.get_db_config")
async def test_list_resources_multi_db_safe(mock_get_config, mock_connect):
    """Test that database resources have identifier-safe names."""
    from mysql_mcp_server.server import list_resources
    
    # Mock for multi-database mode (no "database" in config)
    mock_get_config.return_value = {"user": "u", "password": "p"}
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [("db1",), ("db2",), ("information_schema",)]
    
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    resources = await list_resources()
    
    # information_schema should be filtered out
    assert len(resources) == 2
    # Should be database_name
    assert resources[0].name == "database_db1"
    assert resources[1].name == "database_db2"
    assert str(resources[0].uri) == "mysql://database/db1"
