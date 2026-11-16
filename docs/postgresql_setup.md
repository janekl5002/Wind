# PostgreSQL Setup Guide

This guide helps you set up PostgreSQL with PostGIS for the SeaRoute integration.

## Installation

### macOS (using Homebrew)

```bash
# Install PostgreSQL
brew install postgresql@15

# Start PostgreSQL service
brew services start postgresql@15

# Install PostGIS extension
brew install postgis
```

### Alternative: PostgreSQL.app (macOS GUI)

1. Download from: https://postgresapp.com/
2. Install and launch the app
3. Initialize a new server (if needed)
4. Use the bundled `psql` command-line tool

### Linux (Ubuntu/Debian)

```bash
# Install PostgreSQL and PostGIS
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib postgis

# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Windows

1. Download PostgreSQL from: https://www.postgresql.org/download/windows/
2. Run the installer
3. During installation, include PostGIS extension
4. Or install PostGIS separately: https://postgis.net/windows_downloads/

## Initial Setup

### 1. Create Database User (if needed)

```bash
# Connect to PostgreSQL
psql -U postgres

# Create a user (optional, you can use 'postgres' user)
CREATE USER wind_propulsion WITH PASSWORD 'your_password';
ALTER USER wind_propulsion CREATEDB;

# Exit
\q
```

### 2. Create Database

```bash
# Create database
createdb wind_propulsion

# Or using psql
psql -U postgres -c "CREATE DATABASE wind_propulsion;"
```

### 3. Enable PostGIS Extension

```bash
psql -U postgres -d wind_propulsion -c "CREATE EXTENSION postgis;"
```

### 4. Verify Installation

```bash
psql -U postgres -d wind_propulsion -c "SELECT PostGIS_version();"
```

You should see the PostGIS version number.

## Configuration

Update your `.env` file with PostgreSQL credentials:

```bash
POSTGRES_DB=wind_propulsion
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password_here
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

## Running the Setup

Once PostgreSQL is installed and running:

```bash
python scripts/setup_searoute.py
```

This will:
1. Create the database schema
2. Migrate port data from SQLite
3. Set up all necessary tables and indexes

## Troubleshooting

### Connection Refused

- **PostgreSQL not running**: Start the service
  ```bash
  # macOS (Homebrew)
  brew services start postgresql@15
  
  # Linux
  sudo systemctl start postgresql
  ```

### Permission Denied

- Check that your user has permission to create databases
- Try using the `postgres` superuser account

### PostGIS Extension Not Found

- Install PostGIS package:
  ```bash
  # macOS
  brew install postgis
  
  # Linux
  sudo apt-get install postgis
  ```

### Port Already in Use

- Check if PostgreSQL is already running:
  ```bash
  # macOS
  brew services list
  
  # Linux
  sudo systemctl status postgresql
  ```

## Alternative: Docker

If you prefer using Docker:

```bash
# Run PostgreSQL with PostGIS
docker run --name postgres-postgis \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=wind_propulsion \
  -p 5432:5432 \
  -d postgis/postgis:15-3.4

# Connect to it
psql -h localhost -U postgres -d wind_propulsion
```

## Next Steps

After PostgreSQL is set up:

1. Run the setup script: `python scripts/setup_searoute.py`
2. Start SeaRoute service (if needed)
3. Run the example: `python scripts/searoute_example.py`




