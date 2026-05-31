## MySQL Security Configuration

### Creating a Restricted MySQL User

It's crucial to create a dedicated MySQL user with minimal permissions for the MCP server. Never use the root account or a user with full administrative privileges.

#### 1. Create a new MySQL user

```sql
-- Connect as root or administrator
CREATE USER 'mcp_user'@'localhost' IDENTIFIED BY 'your_secure_password';
```

#### 2. Grant minimal required permissions

Basic read-only access (recommended for exploration and analysis):
```sql
-- Grant SELECT permission only
GRANT SELECT ON your_database.* TO 'mcp_user'@'localhost';
```

Standard access (allows data modification but not structural changes):
```sql
-- Grant data manipulation permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON your_database.* TO 'mcp_user'@'localhost';
```

Advanced access (includes ability to create temporary tables for complex queries):
```sql
-- Grant additional permissions for advanced operations
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE TEMPORARY TABLES 
ON your_database.* TO 'mcp_user'@'localhost';
```

#### 3. Apply the permissions
```sql
FLUSH PRIVILEGES;
```

### Additional Security Measures

1. **Network Access**
   - Restrict the user to connecting only from localhost if the MCP server runs on the same machine
   - If remote access is needed, specify exact IP addresses rather than using wildcards

2. **Query Restrictions**
   - Consider using VIEWs to further restrict data access
   - Set appropriate `max_queries_per_hour`, `max_updates_per_hour` limits:
   ```sql
   ALTER USER 'mcp_user'@'localhost' 
   WITH MAX_QUERIES_PER_HOUR 1000
   MAX_UPDATES_PER_HOUR 100;
   ```

3. **Data Access Control**
   - Grant access only to specific tables when possible
   - Use column-level permissions for sensitive data:
   ```sql
   GRANT SELECT (public_column1, public_column2) 
   ON your_database.sensitive_table TO 'mcp_user'@'localhost';
   ```

4. **Regular Auditing**
   - Enable MySQL audit logging for the MCP user
   - Regularly review logs for unusual patterns
   - Periodically review and adjust permissions

### Environment Configuration

When setting up the MCP server, use these restricted credentials in your environment:

```bash
MYSQL_USER=mcp_user
MYSQL_PASSWORD=your_secure_password
MYSQL_DATABASE=your_database
MYSQL_HOST=localhost
```

### Monitoring Usage

To monitor the MCP user's database usage:

```sql
-- Check current connections
SELECT * FROM information_schema.PROCESSLIST 
WHERE user = 'mcp_user';

-- View user privileges
SHOW GRANTS FOR 'mcp_user'@'localhost';

-- Check resource limits
SELECT * FROM mysql.user 
WHERE user = 'mcp_user' AND host = 'localhost';
```

### Best Practices

1. **Regular Password Rotation**
   - Change the MCP user's password periodically
   - Use strong, randomly generated passwords
   - Update application configurations after password changes

2. **Permission Review**
   - Regularly audit granted permissions
   - Remove unnecessary privileges
   - Keep permissions as restrictive as possible

3. **Access Patterns**
   - Monitor query patterns for potential issues
   - Set up alerts for unusual activity
   - Maintain detailed logs of database access

4. **Data Protection**
   - Consider encrypting sensitive columns
   - Use SSL/TLS for database connections (see **SSL/TLS Support** below)
   - Implement data masking where appropriate

### Secure Remote Access (SSH Tunneling)

If your MySQL server is not on the same network as the MCP server, **do not expose MySQL directly to the internet.** Instead, use the built-in SSH tunneling support:

1. Enable SSH tunneling by setting `MYSQL_SSH_ENABLE=true`.
2. Configure your SSH jump host credentials and private key path.
3. The MCP server will establish a secure encrypted tunnel and connect to MySQL over `localhost`, keeping your database port closed to the outside world.

### SSL/TLS Support

For production environments, always encrypt the connection between the MCP server and MySQL.

Use the `MYSQL_SSL_MODE` environment variable to control encryption:
- `REQUIRED`: Ensures the connection is encrypted.
- `VERIFY_CA`: Encrypts and verifies the server's certificate against a CA.
- `VERIFY_IDENTITY`: Encrypts and verifies that the server's hostname matches the certificate.

Specify the CA certificate path using `MYSQL_SSL_CA` if using verification modes.

### SQL Injection Protection

The MCP server includes built-in protection against SQL injection for administrative operations:
- All database and table identifiers provided via resources or tool arguments are strictly validated against a regex whitelist (`^[a-zA-Z0-9_$]+$`).
- Identifiers are automatically quoted with backticks in internal queries.
- Destructive operations in `execute_sql` are flagged via `destructiveHint` to AI agents.