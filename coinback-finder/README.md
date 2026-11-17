# CoinBack Finder module

CoinBack Finder runs as an administrator-only module inside SourcePoint. Open it from the SourcePoint admin navigation or visit `/coinback/` after signing in as an active, approved administrator.

SourcePoint owns the browser session. The SourcePoint web service checks the administrator role for every module page, static asset, and API request, then signs a short-lived identity token for the private CoinBack API. CoinBack's former username/password login is disabled.

The API and scanner share SourcePoint's PostgreSQL database. CoinBack's tables live in the dedicated `coinback` schema so names such as `users` and `products` cannot conflict with SourcePoint's own tables. Compose runs the CoinBack Alembic migrations before starting the API and scanner.

Run the module from the SourcePoint repository root with `docker compose up -d --build`. The frontend and API are internal Compose services; SourcePoint serves them on the same origin. The module does not have its own database or repository.

Set `COINBACK_SSO_SECRET` in SourcePoint's root `.env` to a random value of at least 32 characters. The local workspace has a generated value already; set the same variable in each deployed SourcePoint environment. Keep CoinBack provider settings (for example `GOOGLE_CSE_API_KEY`, `GOOGLE_CSE_ENGINE_ID`, `BRAVE_SEARCH_API_KEY`, and Telegram settings) in the root `.env` for deployment. A local, ignored `coinback-finder/.env` is also read when present.

Product-page fetching remains disabled unless both `PRODUCT_PAGE_FETCH_ENABLED` and `PRODUCT_PAGE_PERMISSION_CONFIRMED` are enabled. Scanner, provider, and notification behavior otherwise continues to use the existing CoinBack configuration.
