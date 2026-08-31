# Local PostgreSQL and pgAdmin 4

The local Compose stack exposes PostgreSQL on the host for pgAdmin.

1. Start the stack from the repository root:

   ```powershell
   docker compose up --build
   ```

2. Open pgAdmin 4 and register a new server.
3. Use these connection values:

   - Host: `localhost`
   - Port: `5432`
   - Maintenance database: `honeychain`
   - Username: `honeychain`
   - Password: the value in the local Compose configuration

4. The API uses the container hostname internally:

   `postgresql://honeychain:<password>@db:5432/honeychain`

This document describes the settings; pgAdmin itself was not configured through this development environment.
