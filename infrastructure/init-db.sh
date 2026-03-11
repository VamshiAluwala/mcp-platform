#!/bin/sh
# Creates multiple databases on first PostgreSQL startup
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE appdb;
    CREATE DATABASE keycloak;
    GRANT ALL PRIVILEGES ON DATABASE appdb TO postgres;
    GRANT ALL PRIVILEGES ON DATABASE keycloak TO postgres;
EOSQL
