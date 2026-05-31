# MySQL MCP Server: Common Use Cases & Examples

This document provides AI agents with context and examples on how to effectively use the tools provided by the MySQL MCP Server.

## 1. Database & Table Discovery

When first connecting to a database, you should discover what data is available.

*   **List all tables (Single-DB mode):** Use the `list_resources` capability.
*   **List all databases (Multi-DB mode):** Use `list_resources`. It will return URIs like `mysql://database/my_db`.
*   **List tables in a specific database:** If in multi-DB mode, read the resource URI for that database (e.g., `mysql://database/my_db`) to see its tables.

## 2. Schema Exploration

Before running complex queries, understand the structure and relationships of the tables.

### `get_schema_info`
Use this tool to get detailed column information, data types, and comments.

*   **Overview of all tables:**
    `get_schema_info({})`
*   **Detailed info for one table:**
    `get_schema_info({"table_name": "users"})`

## 3. Data Inspection

Quickly verify the contents of a table without fetching thousands of rows.

### `get_table_sample`
Fetches a small sample of rows (default 5, max 20) along with column names. Useful for understanding data formats (e.g., date formats, status strings).

*   `get_table_sample({"table_name": "orders", "limit": 10})`

## 4. Custom Data Analysis

Perform advanced analysis using standard SQL.

### `execute_sql`
The most powerful tool for custom filtering, joining, and aggregation.

*   **Count records with filtering:**
    `execute_sql({"query": "SELECT count(*) FROM users WHERE active = 1"})`
*   **Joining tables:**
    `execute_sql({"query": "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id LIMIT 10"})`
*   **Inspecting structure (Native):**
    `execute_sql({"query": "DESCRIBE users"})` or `execute_sql({"query": "SHOW CREATE TABLE users"})`

## Security Note for Agents
- The `execute_sql` tool is marked as **destructive**. Be cautious when running queries that modify data (`INSERT`, `UPDATE`, `DELETE`).
- In **Multi-Database Mode**, you must either use fully qualified names (e.g., `SELECT * FROM mydb.users`) or switch databases first using `execute_sql({"query": "USE mydb"})`.
