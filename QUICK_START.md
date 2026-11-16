# Quick Start: SeaRoute PostgreSQL Setup

This guide walks you through the complete setup process step by step.

## Step 1: Install PostgreSQL and PostGIS

### Option A: Using Homebrew (macOS - Recommended)

```bash
# Install PostgreSQL
brew install postgresql@15

# Install PostGIS extension
brew install postgis

# Start PostgreSQL service
brew services start postgresql@15

# Verify it's running
brew services list | grep postgresql
```

### Option B: Using Docker (Cross-platform)

```bash
# Run PostgreSQL with PostGIS in Docker
docker run --name postgres-postgis \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=wind_propulsion \
  -p 5432:5432 \
  -d postgis/postgis:15-3.4

# Verify it's running
docker ps | grep postgres
```

### Option C: Download PostgreSQL.app (macOS - GUI)

1. Download from: https://postgresapp.com/
2. Install and launch the app
3. Click "Initialize" to create a new server
4. The bundled `psql` will be in `/Applications/Postgres.app/Contents/Versions/latest/bin/`

## Step 2: Verify PostgreSQL is Running

Run the check script:

```bash
python scripts/check_postgresql.py
```

You should see:
```
✓ PostgreSQL client found
✓ PostgreSQL server is running and accessible
✓ PostGIS extension is available
```

## Step 3: Configure Database Credentials

Edit the `.env` file in the project root:

```bash
# For local PostgreSQL
POSTGRES_DB=wind_propulsion
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres  # or your password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# For Docker (same as above)
# For PostgreSQL.app, use the user from the app
```

**Important**: If you used Docker, the default password is what you set in the docker run command.

## Step 4: Run the Automated Setup

This single command will do everything:

```bash
python scripts/setup_searoute.py
```

What it does:
1. ✅ Creates `.env` file if it doesn't exist
2. ✅ Creates database `wind_propulsion` if it doesn't exist
3. ✅ Enables PostGIS extension
4. ✅ Creates all tables (ports, port_routes)
5. ✅ Creates indexes for performance
6. ✅ Creates views for easy querying
7. ✅ Migrates all port data from SQLite to PostgreSQL

You should see output like:
```
============================================================
SeaRoute PostgreSQL/PostGIS Setup
============================================================

Step 1: Checking .env file...
✓ .env file already exists

Step 2: Setting up PostgreSQL database...
✓ Database 'wind_propulsion' created
✓ PostGIS extension created

Step 3: Creating database schema...
✓ Schema created successfully

Step 4: Migrating port data...
Found 3801 ports to migrate
Successfully migrated 3801 ports to PostgreSQL
Migration complete!

============================================================
✓ Setup complete!
============================================================
```

## Step 5: Test the Integration

Run the example script:

```bash
python scripts/searoute_example.py
```

This will:
- Connect to PostgreSQL
- Look up ports by UN/LOCODE
- Calculate routes (if SeaRoute API is running)
- Query cached routes

## Troubleshooting

### "Connection refused" error

**PostgreSQL not running:**
```bash
# macOS (Homebrew)
brew services start postgresql@15

# Docker
docker start postgres-postgis

# Check status
python scripts/check_postgresql.py
```

### "Password authentication failed"

- Check your `.env` file has the correct password
- For Docker: Use the password you set in the docker run command
- For PostgreSQL.app: Check the password in the app settings

### "Database does not exist"

The setup script should create it automatically. If it doesn't:
```bash
# Connect to PostgreSQL
psql -U postgres

# Create database manually
CREATE DATABASE wind_propulsion;

# Enable PostGIS
\c wind_propulsion
CREATE EXTENSION postgis;
```

### "PostGIS extension not found"

Install PostGIS:
```bash
# macOS
brew install postgis

# Docker: Already included in postgis/postgis image
```

## Manual Setup (Alternative)

If the automated script doesn't work, you can do it manually:

```bash
# 1. Create database and enable PostGIS
psql -U postgres -c "CREATE DATABASE wind_propulsion;"
psql -U postgres -d wind_propulsion -c "CREATE EXTENSION postgis;"

# 2. Create schema
psql -U postgres -d wind_propulsion -f databases/postgresql_schema.sql

# 3. Migrate data
python scripts/migrate_to_postgresql.py
```

## Next Steps

Once setup is complete:

1. **Start SeaRoute service** (optional - for route calculation):
   ```bash
   cd searoute/modules/war
   mvn clean package
   # Deploy to Tomcat
   ```

2. **Calculate routes**:
   ```python
   from scripts.searoute_integration import calculate_route
   # ... see docs/searoute_integration.md
   ```

3. **Visualize routes on your map**:
   - Query routes from PostgreSQL
   - Add GeoJSON to your Folium map

## Quick Reference

```bash
# Check PostgreSQL status
python scripts/check_postgresql.py

# Run full setup
python scripts/setup_searoute.py

# Test the integration
python scripts/searoute_example.py

# Query routes directly
psql -U postgres -d wind_propulsion -c "SELECT * FROM port_routes_view LIMIT 5;"
```




