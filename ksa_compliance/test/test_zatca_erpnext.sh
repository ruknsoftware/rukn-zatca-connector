#!/bin/bash

SITE_NAME="test-zatca-erpnext"
ADMIN_PASSWORD="4124"
MYSQL_ROOT_PASSWORD="4124"

set -e # Exit immediately if a command fails

echo "🏗️  Creating new site: $SITE_NAME..."

bench new-site $SITE_NAME \
  --mariadb-root-password "$MYSQL_ROOT_PASSWORD" \
  --admin-password "$ADMIN_PASSWORD"

echo "✅ Site created successfully!"

echo "⚙️  Setting site config..."
bench --site $SITE_NAME set-config allow_tests true

echo "📦 Installing ERPNext..."
bench --site $SITE_NAME install-app erpnext

echo "📦 Installing payments..."
bench --site $SITE_NAME install-app payments

echo "📦 Installing KSA Compliance..."
bench --site $SITE_NAME install-app ksa_compliance

echo "🚀 Running migrate..."
bench --site $SITE_NAME migrate

echo "🧪 [STATE 1] Running standard ERPNext tests (KSA app installed, not configured)..."
bench --site $SITE_NAME run-tests --app erpnext

echo "✅ All tests done!"
