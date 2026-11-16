-- PostgreSQL/PostGIS Schema for SeaRoute Integration
-- 
-- This schema extends the existing port database with route caching functionality.
-- Assumes you have PostGIS extension installed: CREATE EXTENSION postgis;

-- Ports table (adapted from your existing structure)
-- If migrating from SQLite, you'll need to adapt column names
CREATE TABLE IF NOT EXISTS ports (
    id SERIAL PRIMARY KEY,
    world_port_index_number INTEGER UNIQUE,
    name TEXT,
    main_port_name TEXT,
    alternate_port_name TEXT,
    unlocode TEXT,
    country_code TEXT,
    region_name TEXT,
    world_water_body TEXT,
    harbor_size TEXT,
    harbor_type TEXT,
    harbor_use TEXT,
    lon DOUBLE PRECISION,
    lat DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_ports_unlocode ON ports(unlocode);
CREATE INDEX IF NOT EXISTS idx_ports_world_port_index ON ports(world_port_index_number);
CREATE INDEX IF NOT EXISTS idx_ports_location ON ports(lon, lat);

-- Route cache table
CREATE TABLE IF NOT EXISTS port_routes (
    id BIGSERIAL PRIMARY KEY,
    origin_id INT REFERENCES ports(id),
    dest_id INT REFERENCES ports(id),
    params JSONB,             -- store resolution/avoid settings, etc.
    dist_km DOUBLE PRECISION,
    d_from_km DOUBLE PRECISION,  -- snap-to-network distance from origin
    d_to_km DOUBLE PRECISION,     -- snap-to-network distance to destination
    geom geometry(MultiLineString, 4326),
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (origin_id, dest_id, params)
);

-- Create spatial index for geometry queries
CREATE INDEX IF NOT EXISTS idx_port_routes_geom ON port_routes USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_port_routes_origin ON port_routes(origin_id);
CREATE INDEX IF NOT EXISTS idx_port_routes_dest ON port_routes(dest_id);

-- View for easy querying with port names
CREATE OR REPLACE VIEW port_routes_view AS
SELECT 
    r.id,
    r.origin_id,
    r.dest_id,
    p1.main_port_name AS origin_name,
    p1.unlocode AS origin_unlocode,
    p2.main_port_name AS dest_name,
    p2.unlocode AS dest_unlocode,
    r.params,
    r.dist_km,
    r.d_from_km,
    r.d_to_km,
    ST_AsGeoJSON(r.geom) AS geojson,
    r.created_at
FROM port_routes r
JOIN ports p1 ON p1.id = r.origin_id
JOIN ports p2 ON p2.id = r.dest_id;




