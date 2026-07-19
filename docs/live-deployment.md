# Live Firebase, Firestore, and Deployment Runbook

This runbook connects the existing VenueSignal application to its live Google infrastructure. It does not change the product architecture: the browser uses Firebase Authentication only, all Firestore access remains server-side, and FastAPI derives authorization exclusively from verified Firebase ID-token claims.

## Project values

| Setting | Value |
| --- | --- |
| Firebase / Google Cloud project | `venuesignal` |
| Project number | `726508228584` |
| Firebase Auth domain | `venuesignal.firebaseapp.com` |
| Demo controller email | `admin@venuesignal.com` |
| Cloud Run region | `asia-south1` |
| Cloud Run service | `venuesignal-api` |
| Runtime service identity | `venuesignal-api@venuesignal.iam.gserviceaccount.com` |
| Secret Manager secret | `venuesignal-gemini-key` |

Never put the demo password, Gemini API key, Firebase ID tokens, ADC files, or service-account JSON keys in the repository. The Firebase web API key and web app identifiers are public application configuration, not backend credentials.

## Optional Cloud Run deployment path

The primary submission path now uses Render for the backend and Vercel for the frontend; see [DEPLOY.md](../DEPLOY.md). The remaining sections preserve Cloud Run as a Google-managed alternative. Cloud Run requires billing on project `venuesignal`, which is not currently attached.

## PromptWars demo access

- Demo account email: `admin@venuesignal.com`
- Password: provided separately in the PromptWars submission notes

The signed-out interface pre-fills only the public demo email. It never embeds, retrieves, logs, or displays the password. Rotate the demo password immediately before submission, then place the exact rotated value only in the private PromptWars submission notes.

Final judge-access check:

- [ ] Rotate the demo password.
- [ ] Verify email/password sign-in in a fresh incognito window.
- [ ] Verify the account has the `CONTROLLER` custom claim.
- [ ] Sign out and back in after any claim change to obtain a fresh ID token.
- [ ] Confirm `GET /api/auth/me` reports `CONTROLLER` from server-verified claims.
- [ ] Complete the Guided Demo from the public URL.
- [ ] Provide the exact email and rotated password in the PromptWars submission notes.

## Local modes

The checked-in `.env.example` remains an offline development configuration:

```dotenv
AUTH_MODE=disabled
PERSISTENCE_BACKEND=memory
AI_PROVIDER=local
```

The ignored root `.env` can select the live adapters:

```dotenv
AUTH_MODE=firebase
PERSISTENCE_BACKEND=firestore
FIREBASE_PROJECT_ID=venuesignal
AI_PROVIDER=gemini
GEMINI_MODEL=gemini-2.5-flash
```

Keep `GEMINI_API_KEY` only in the ignored `.env`. Do not set `GOOGLE_APPLICATION_CREDENTIALS` to a downloaded key; local Google client libraries should use user ADC.

## 1. Install and authenticate the CLIs

On macOS, install the Google Cloud CLI and Firebase CLI if they are missing:

```bash
brew install --cask google-cloud-sdk
npm install --global firebase-tools
```

Authenticate the command-line tools and create local Application Default Credentials:

```bash
gcloud auth login
gcloud config set project venuesignal
gcloud auth application-default login
gcloud auth application-default set-quota-project venuesignal
firebase login
```

The signed-in Google account needs access to project `venuesignal`. Assigning custom claims requires Firebase Authentication administration permission; the Firestore smoke test requires Firestore data access. ADC is stored in the operating system's standard gcloud location, outside this repository.

Validate ADC without printing an access token:

```bash
venv/bin/python scripts/firestore_smoke_test.py
```

Do not use `gcloud auth application-default print-access-token` in recorded test output.

## 2. Assign the controller claim

The role tool accepts only `CONTROLLER` and `VIEWER`, preserves unrelated custom claims, and uses Firebase Admin with ADC:

```bash
FIREBASE_PROJECT_ID=venuesignal venv/bin/python scripts/set_firebase_role.py \
  --email admin@venuesignal.com \
  --role CONTROLLER
```

Expected output contains the email, UID, resulting role, and a reminder to refresh the login. It never prints a password, credential, or token.

Custom claims are carried by newly issued ID tokens. After changing the role, sign out of the VenueSignal frontend and sign in again before testing `/api/auth/me`.

## 3. Configure and start the local application

The ignored `apps/web/.env.local` should contain:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
NEXT_PUBLIC_AUTH_MODE=firebase
NEXT_PUBLIC_FIREBASE_API_KEY=AIzaSyBrsjShOkqM1an6u_X_oq0SxHkStb93bas
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=venuesignal.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=venuesignal
NEXT_PUBLIC_FIREBASE_APP_ID=1:726508228584:web:01bcd0c46b26e5d9ca9e5d
```

Start the API from the repository root:

```bash
source venv/bin/activate
python -m uvicorn app.main:app --app-dir apps/api --reload --port 8000 --env-file .env
```

Start the frontend in a second terminal:

```bash
cd apps/web
npm ci
npm run dev
```

Readiness should report `persistenceBackend: firestore`, `aiProvider: GEMINI`, and `authMode: firebase`:

```bash
curl --fail --silent http://127.0.0.1:8000/health
curl --fail --silent http://127.0.0.1:8000/ready
```

## 4. Verify real sign-in and server identity

The preferred UI check is:

1. Open `http://localhost:3000`.
2. Sign out if an older session exists.
3. Sign in as `admin@venuesignal.com`.
4. Confirm the identity card reports `Demo Controller` and `CONTROLLER`; Firebase details remain under system details.
5. Confirm browser requests to `/api` include a Firebase bearer token and do not include any client-selected role header.

For a token already held in a local environment variable:

```bash
venv/bin/python scripts/auth_smoke_test.py \
  --api-base http://localhost:8000/api \
  --firebase-id-token "$VENUESIGNAL_FIREBASE_ID_TOKEN" \
  --expect-role CONTROLLER
```

For a local email/password smoke test without printing or saving the password or returned token:

```bash
export NEXT_PUBLIC_FIREBASE_API_KEY=AIzaSyBrsjShOkqM1an6u_X_oq0SxHkStb93bas
export VENUESIGNAL_DEMO_ADMIN_EMAIL=admin@venuesignal.com
read -s VENUESIGNAL_DEMO_ADMIN_PASSWORD
export VENUESIGNAL_DEMO_ADMIN_PASSWORD
venv/bin/python scripts/firebase_login_smoke_test.py --expect-role CONTROLLER
unset VENUESIGNAL_DEMO_ADMIN_PASSWORD
```

If ADC or the backend is not ready yet, append `--auth-only` to verify the Firebase account sign-in independently. That mode confirms Firebase returned an ID token but does not treat its claims as server-authorized.

`GET /api/auth/me` must return HTTP 200 with `role: CONTROLLER` and `authMode: firebase`. The backend verifies the token with Firebase Admin and ignores frontend role assertions. Missing or unknown role claims map to `VIEWER`.

## 5. Verify authorization

Controller acceptance checks:

- `GET /api/venues` returns 200.
- `POST /api/workflow/reports` is allowed.
- operational mutations, incident linking, plan approval, tasks, communications, and resolution are allowed.

For a temporary viewer test, create a disposable email/password user in Firebase Authentication, then assign its claim without placing its password in source control:

```bash
FIREBASE_PROJECT_ID=venuesignal venv/bin/python scripts/set_firebase_role.py \
  --email temporary-viewer@example.invalid \
  --role VIEWER
```

Sign in as that user and obtain a fresh token. `GET /api/venues` must return 200 and `POST /api/workflow/reports` must return 403. Delete the disposable account from Firebase Authentication after the test. A user with no `role` claim must produce the same viewer-only behavior.

## 6. Verify Firestore and rules

Run the isolated live smoke test:

```bash
FIREBASE_PROJECT_ID=venuesignal venv/bin/python scripts/firestore_smoke_test.py
```

It writes, reads, validates, and deletes one document in `venuesignal_smoke_tests`. It does not touch workflow records. Expected output:

```text
Firestore smoke test: PASS
Project: venuesignal
```

The application repositories genuinely use these collections:

- `venuesignal_system` for the operational-state singleton
- `venuesignal_reports` for reports
- `venuesignal_incidents` for incidents, including plans, tasks, communications, recovery, and audit state

The existing repository methods use stable model IDs as Firestore document IDs. No composite indexes are needed by current queries; `firestore.indexes.json` therefore remains empty.

Direct browser access must stay denied. Validate and deploy the checked-in deny-all rules:

```bash
firebase use venuesignal
firebase deploy --only firestore:rules --project venuesignal
```

Do not deploy indexes unless a future, reviewed query actually requires one.

## 7. Persistence restart test

Run with Firebase Auth, Firestore, and Gemini enabled. As the controller:

1. Create a report and confirm an incident.
2. Approve its plan so tasks and communication drafts exist.
3. Apply one operational mutation.
4. Record only the report and incident IDs, never the bearer token.
5. Stop the API process without resetting data.
6. Start the API again with the same ignored `.env`.
7. Sign in again and confirm the report, incident, approved plan, tasks, communications, audit events, and operational context remain.

The restart proof must use `PERSISTENCE_BACKEND=firestore`; the SQLite and fake-Firestore unit tests are separate evidence.

## 8. Live golden flow

Use the frontend's **Load 3-report scenario** action or submit these reports through the authenticated API:

1. `Lift near Section 214 is stuck again. Two wheelchair users are waiting.`
2. `Upper west accessible path is blocked, sending people toward Corridor W3.`
3. `Crowd building near the west stairs after halftime.`

Link the first two reports and confirm `A_LIFT_2`. Verify Gemini extraction and relationship reasoning remain advisory, the deterministic graph produces the 530 m Corridor W3 fallback, and no tasks or communication drafts exist before approval. Approve the plan and confirm the generated work and English, Spanish, and French drafts.

Then mark `A_CORRIDOR_W3` out of service and reassess. The former plan must become `UNSAFE`, the result must state that no verified step-free route exists, any positive route guidance must be withheld, and the proposed revision must be either `GEMINI_REPAIRED` or `DETERMINISTIC_CONTAINMENT`. A second human approval is required.

Restart the backend and confirm the complete golden-flow state is still present in Firestore.

## 9. Secret Manager

Enable the required APIs and select the project:

```bash
gcloud config set project venuesignal
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  firestore.googleapis.com firebaserules.googleapis.com identitytoolkit.googleapis.com \
  secretmanager.googleapis.com
```

Create the expected secret once:

```bash
gcloud secrets describe venuesignal-gemini-key --project venuesignal \
  || gcloud secrets create venuesignal-gemini-key --project venuesignal --replication-policy=automatic
```

Add a secret version without echoing the key:

```bash
read -s GEMINI_API_KEY
export GEMINI_API_KEY
printf '%s' "$GEMINI_API_KEY" \
  | gcloud secrets versions add venuesignal-gemini-key --project venuesignal --data-file=-
unset GEMINI_API_KEY
```

`cloudbuild.yaml` references exactly `venuesignal-gemini-key:latest`. Do not put Gemini configuration in Vercel.

## 10. Cloud Run service identity and IAM

Use a dedicated runtime identity, not the default Compute Engine service account and not a downloaded key:

```bash
gcloud iam service-accounts describe venuesignal-api@venuesignal.iam.gserviceaccount.com \
  --project venuesignal \
  || gcloud iam service-accounts create venuesignal-api \
       --project venuesignal \
       --display-name='VenueSignal Cloud Run API'
```

Grant only runtime access needed by the current code:

```bash
RUNTIME_SA=venuesignal-api@venuesignal.iam.gserviceaccount.com
gcloud projects add-iam-policy-binding venuesignal \
  --member="serviceAccount:$RUNTIME_SA" \
  --role=roles/datastore.user
gcloud projects add-iam-policy-binding venuesignal \
  --member="serviceAccount:$RUNTIME_SA" \
  --role=roles/firebaseauth.viewer
gcloud secrets add-iam-policy-binding venuesignal-gemini-key \
  --project venuesignal \
  --member="serviceAccount:$RUNTIME_SA" \
  --role=roles/secretmanager.secretAccessor
```

`roles/datastore.user` provides application read/write access to Firestore. `roles/firebaseauth.viewer` supplies `firebaseauth.users.get`, needed by revocation-aware token verification, without user mutation. The role-assignment script is an administrative local action and must run under a separately authorized human ADC identity.

The deployment principal also needs permission to attach the runtime identity (`roles/iam.serviceAccountUser`). Cloud Build's default identity varies by project age, so discover it rather than assuming the legacy address:

```bash
CLOUD_BUILD_SA="$(gcloud builds get-default-service-account --project venuesignal --format='value(serviceAccountEmail)')"
test -n "$CLOUD_BUILD_SA"
gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_SA" \
  --project venuesignal \
  --member="serviceAccount:$CLOUD_BUILD_SA" \
  --role=roles/iam.serviceAccountUser
gcloud projects add-iam-policy-binding venuesignal \
  --member="serviceAccount:$CLOUD_BUILD_SA" \
  --role=roles/run.admin
gcloud projects add-iam-policy-binding venuesignal \
  --member="serviceAccount:$CLOUD_BUILD_SA" \
  --role=roles/artifactregistry.writer
```

Create the Artifact Registry repository if it does not exist:

```bash
gcloud artifacts repositories describe venuesignal --location asia-south1 --project venuesignal \
  || gcloud artifacts repositories create venuesignal \
       --repository-format=docker --location=asia-south1 --project=venuesignal
```

## 11. Deploy Cloud Run

The stable HTTPS frontend origin is `https://venuesignal.vercel.app`. It is already the guarded Cloud Build default and can still be overridden explicitly:

```bash
gcloud builds submit \
  --project venuesignal \
  --config cloudbuild.yaml \
  --substitutions=_WEB_ORIGIN=https://venuesignal.vercel.app
```

The build deploys `venuesignal-api` with the dedicated service identity, Firestore persistence, Firebase authentication, Gemini, Secret Manager, trusted proxy handling, disabled demo resets, and an exact CORS origin. Cloud Run is transport-public so browser bearer tokens can reach it; FastAPI remains the application authorization boundary.

After deployment:

```bash
gcloud run services describe venuesignal-api \
  --project venuesignal \
  --region asia-south1 \
  --format='value(status.url)'
```

Call `/health` and `/ready`, then use the returned URL plus `/api` as the frontend API base.

## 12. Configure Vercel

Set these values for the production deployment:

```dotenv
NEXT_PUBLIC_AUTH_MODE=firebase
NEXT_PUBLIC_FIREBASE_API_KEY=AIzaSyBrsjShOkqM1an6u_X_oq0SxHkStb93bas
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=venuesignal.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=venuesignal
NEXT_PUBLIC_FIREBASE_APP_ID=1:726508228584:web:01bcd0c46b26e5d9ca9e5d
NEXT_PUBLIC_API_BASE_URL=https://YOUR-CLOUD-RUN-URL/api
```

Redeploy the frontend after changing `NEXT_PUBLIC_*` values because Next.js embeds them at build time. Do not set `GEMINI_API_KEY`, Google credentials, demo passwords, or Firebase ID tokens in Vercel.

Add the final Vercel hostname to Firebase Authentication's authorized domains. Redeploy Cloud Run with `_WEB_ORIGIN` exactly equal to that frontend origin. Do not use `*`, include multiple production origins, or include a URL path.

## 13. Reset the shared demo to canonical base state

Do not enable the public workflow-reset route in production. Use the ADC-backed operator script instead:

```bash
FIREBASE_PROJECT_ID=venuesignal venv/bin/python scripts/reset_live_demo.py
FIREBASE_PROJECT_ID=venuesignal venv/bin/python scripts/reset_live_demo.py \
  --execute --confirm-project venuesignal
```

The first command is read-only and reports current report/incident counts. The second deletes workflow documents and writes a clean operational-state singleton. It never modifies Firebase accounts or credentials. API instances reload shared operational state from Firestore on subsequent requests.

## 14. Final live acceptance record

Capture pass/fail and timestamps for:

- controller custom claim and fresh sign-in
- `/api/auth/me` returning `CONTROLLER` and `firebase`
- viewer read 200 and controller mutation 403
- disposable Firestore smoke document cleanup
- deny-all Firestore rules deployment
- operational/report/incident round trips and restart persistence
- live Gemini golden flow and no-route reassessment
- Cloud Run `/health` and `/ready`
- Vercel-to-Cloud-Run authenticated browser flow
- backend tests, frontend tests, lint, typecheck, build, dependency checks, secret scan, and repository-size gate

Official references: [Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc), [Firebase custom claims](https://firebase.google.com/docs/auth/admin/custom-claims), [Firebase ID-token verification](https://firebase.google.com/docs/auth/admin/verify-id-tokens), [Firestore server IAM](https://cloud.google.com/firestore/docs/security/iam), [Cloud Run service identity](https://cloud.google.com/run/docs/configuring/services/service-identity), and [Secret Manager access](https://cloud.google.com/secret-manager/docs/manage-access-to-secrets).
