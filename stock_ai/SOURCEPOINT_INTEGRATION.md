# Stock AI in SourcePoint

The `stock_ai/` directory in this SourcePoint repository is the only Stock AI code source. The top-level SourcePoint Compose stack builds its app and database services from this directory.

SourcePoint serves Stock AI at `/stock-ai` through its authenticated gateway. The Stock AI container and its PostgreSQL database have no published host ports. SourcePoint authorizes every browser request for active, approved admin and developer users, and signs each upstream request with a short-lived token that Stock AI verifies.

## Configure the SourcePoint `.env`

The self-hosted deployment workflow fills in the SSO secret, database password, and dump directory in the server's root `.env` if they are missing. It keeps any non-empty settings already present. For a manual Compose deployment, add these settings to the root SourcePoint `.env` first:

```dotenv
STOCK_AI_SSO_SECRET=<a random secret with at least 32 characters>
STOCK_AI_DB_PASS=<a separate strong database password>
STOCK_AI_DB_DUMP_DIR="/Users/gaurav/Desktop/Stock Db"
# Optional; defaults are stock_market and admin.
# STOCK_AI_DB_NAME=stock_market
# STOCK_AI_DB_USER=admin
# Set this only if the folder contains more than one supported dump.
# STOCK_AI_DB_DUMP_FILE=stock_market.sql
```

The dump directory can contain one `.sql`, `.sql.gz`, `.dump`, `.backup`, or `.tar` file. If it contains multiple supported dumps, set `STOCK_AI_DB_DUMP_FILE` to the chosen filename. The directory is mounted read-only and is excluded from both Docker build contexts.

The dump is restored only when the `stockai_db_data` volume is initialized for the first time. If no dump is present on that first start, the database container logs that it created an empty database, and Stock AI initializes its tables when it starts. A later-added dump is not imported automatically into an existing volume.

Then start SourcePoint with its existing deployment command, for example:

```bash
docker compose up -d --build
```

The application link appears in SourcePoint navigation only for admin and developer accounts. Use the top-level SourcePoint `docker-compose.yml` for development and deployment.
