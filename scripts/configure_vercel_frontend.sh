#!/usr/bin/env bash
set -euo pipefail

API_URL="${1:-}"
EXECUTE="${2:-}"

if [[ -z "${API_URL}" || "${API_URL}" != https://* ]]; then
  echo "Usage: scripts/configure_vercel_frontend.sh https://RENDER-BACKEND-URL [--execute]" >&2
  exit 2
fi

API_BASE_URL="${API_URL%/}/api"

if [[ "${EXECUTE}" != "--execute" ]]; then
  echo "Dry-run guard: no Vercel settings changed."
  echo "NEXT_PUBLIC_API_BASE_URL=${API_BASE_URL}"
  echo "Run again with --execute to configure and redeploy venuesignal.vercel.app."
  exit 0
fi

if [[ ! -f apps/web/.vercel/project.json ]]; then
  echo "Vercel project link is missing at apps/web/.vercel/project.json." >&2
  exit 3
fi

vercel env add NEXT_PUBLIC_API_BASE_URL production --value "${API_BASE_URL}" --no-sensitive --force --yes --cwd apps/web
vercel env add NEXT_PUBLIC_AUTH_MODE production --value firebase --no-sensitive --force --yes --cwd apps/web
vercel env add NEXT_PUBLIC_FIREBASE_API_KEY production --value AIzaSyBrsjShOkqM1an6u_X_oq0SxHkStb93bas --no-sensitive --force --yes --cwd apps/web
vercel env add NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN production --value venuesignal.firebaseapp.com --no-sensitive --force --yes --cwd apps/web
vercel env add NEXT_PUBLIC_FIREBASE_PROJECT_ID production --value venuesignal --no-sensitive --force --yes --cwd apps/web
vercel env add NEXT_PUBLIC_FIREBASE_APP_ID production --value 1:726508228584:web:01bcd0c46b26e5d9ca9e5d --no-sensitive --force --yes --cwd apps/web
vercel deploy --prod --yes --cwd apps/web
