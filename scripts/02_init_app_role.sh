#!/bin/bash
# Creates a least-privilege application role for the TreeVuln backend.
# The superuser (POSTGRES_USER) is used only for schema management.
set -e

APP_USER="${APP_DB_USER:-treevuln_app}"
APP_PASS="${APP_DB_PASSWORD}"

if [ -z "$APP_PASS" ]; then
    echo "WARNING: APP_DB_PASSWORD not set — skipping app role creation."
    echo "The backend will use the superuser. Set APP_DB_PASSWORD for least-privilege access."
    exit 0
fi

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$APP_USER') THEN
            CREATE ROLE $APP_USER WITH LOGIN PASSWORD '$APP_PASS';
        END IF;
    END
    \$\$;

    -- Permissions de connexion
    GRANT CONNECT ON DATABASE $POSTGRES_DB TO $APP_USER;
    GRANT USAGE ON SCHEMA public TO $APP_USER;

    -- Permissions DML uniquement (pas de CREATE, DROP, ALTER)
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO $APP_USER;
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO $APP_USER;

    -- Permissions par défaut pour les futures tables
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO $APP_USER;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public
        GRANT USAGE, SELECT ON SEQUENCES TO $APP_USER;
EOSQL

echo "Application role '$APP_USER' created with least-privilege permissions."
