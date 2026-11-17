#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

flask init-db
flask populate-db

# Build Wealth Manager into SourcePoint's authenticated static route.
npm ci --prefix "Wealth Manager/frontend"
VITE_API_BASE_URL=/wealth-api npm run build --prefix "Wealth Manager/frontend"
mkdir -p static/wealth_manager
cp -R "Wealth Manager/frontend/dist/." static/wealth_manager/
