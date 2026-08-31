# HoneyChain deployment plan

## Current status
- Security remediation pass completed and repo test suite passes.
- Local code is deployment-prepared for a demo prototype.
- Live Vercel/Render deployment has not been executed in this environment because no actual platform credentials or public hosting access were provided.

## Required before public launch
1. In Render, create PostgreSQL in the same region as the web service.
2. In the imported Render web service, set `DATABASE_URL` to the database's Internal Database URL.
3. Set the remaining production secrets and demo password environment variables.
4. Deploy and confirm migration/startup logs.
5. Test `/healthz`, `/readiness`, login, batch creation, PBFT/block finalization, QR verification, and restart persistence.
6. Create the Vercel frontend and set `FRONTEND_URL` in Render to its real origin.

## UI status
- Role-aware login and dashboard navigation are implemented for all seven designations.
- Dashboard cards expose real batch, block, quorum, validator, and database status.
- Public consumer QR verification remains available at `/verify/<qr_id>`.

## Recommended configuration
- Frontend env: VITE_API_BASE_URL
- Backend env: DATABASE_URL, JWT_SECRET, FRONTEND_URL, ENVIRONMENT, PORT
- Production should not use localhost or hardcoded demo secrets.

## Go/no-go
- Go: repo is ready for manual deployment when valid platform credentials are available.
- No-go: claiming an already live public deployment without actual deployment verification.
