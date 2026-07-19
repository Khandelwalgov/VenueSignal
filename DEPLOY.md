# VenueSignal Deployment

## Final topology

- Frontend: Vercel
- Backend: Render
- Authentication: Firebase Authentication
- Persistence: Firestore
- AI: Gemini API

## Render backend

Create a Python web service from `main` with:

| Setting | Value |
| --- | --- |
| Root directory | `apps/api` |
| Build command | `pip install -r requirements-production.txt` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*" --no-server-header` |
| Health check | `/health` |
| Region | Singapore |

Use [render.yaml](render.yaml) or copy the values from [.env-prod.example](.env-prod.example). `GEMINI_API_KEY` is a private Render environment value. Add the complete Firebase Admin JSON as a Render secret file named `firebase-service-account.json`; `GOOGLE_APPLICATION_CREDENTIALS` must point to `/etc/secrets/firebase-service-account.json`.

Do not set `PORT`. Render supplies it.

## Vercel frontend

Use [apps/web/.env.production.example](apps/web/.env.production.example) as the variable-name checklist. Set these in Vercel Production:

```dotenv
NEXT_PUBLIC_API_BASE_URL=https://YOUR-RENDER-SERVICE.onrender.com/api
NEXT_PUBLIC_AUTH_MODE=firebase
NEXT_PUBLIC_FIREBASE_API_KEY=YOUR_PUBLIC_FIREBASE_WEB_API_KEY
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=venuesignal.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=venuesignal
NEXT_PUBLIC_FIREBASE_APP_ID=YOUR_PUBLIC_FIREBASE_WEB_APP_ID
NEXT_PUBLIC_ENABLE_PUBLIC_DEMO_CREDENTIALS=false
NEXT_PUBLIC_DEMO_EMAIL=
NEXT_PUBLIC_DEMO_PASSWORD=
```

For judge access, set the public-demo flag to `true` and provide the disposable Firebase demo account values only in Vercel Production. These `NEXT_PUBLIC_*` values are intentionally bundled into browser JavaScript. The account must contain only synthetic data, retain its server-authoritative `CONTROLLER` claim, and be rotated or removed after judging.

Never put the Gemini key, Firebase Admin JSON, ID tokens, or private operational credentials in Vercel.

Redeploy Vercel whenever a `NEXT_PUBLIC_*` value changes.

## Firebase

Enable email/password authentication, add the Vercel hostname to Authorized Domains, and assign the demo account's `CONTROLLER` custom claim with `scripts/set_firebase_role.py`. Deploy the checked-in deny-all Firestore client rules.

## Final checks

1. Confirm Render `/health` and `/ready`.
2. Reset the shared demo with `scripts/reset_live_demo.py`.
3. Open Vercel in a fresh private window.
4. Confirm Firebase sign-in and `/api/auth/me` role verification.
5. Complete the tutorial and guided demo.
6. Rotate or remove public demo credentials after judging.
