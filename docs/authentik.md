# Traefik + Authentik (optional)

For admins who already run Authentik or want SSO and automatic HTTPS in front
of Flowcase. Most installs do not need this: plain `docker compose up -d`
is enough.

Requires Docker Compose 2.24+.

## 1. Environment

Copy `.env.example` to `.env` and fill it in (`DOMAIN`, `ADMIN_EMAIL`,
`CA_SERVER`, `PG_PASS`, `AUTHENTIK_SECRET_KEY`).

```bash
openssl rand -base64 24   # PG_PASS
openssl rand -base64 32   # AUTHENTIK_SECRET_KEY
```

## 2. Start

```bash
docker compose -f docker-compose.yml -f docker-compose.authentik.yml up -d
```

This adds Traefik, Authentik, Postgres and Redis, removes the published
port 80 from nginx, turns on Traefik's `authentik` middleware for Flowcase,
and starts the web app with `--traefik-authentik`. The middleware and the
flag are set together in that one file on purpose: with the flag on and no
middleware, anyone could send an `X-Authentik-Username` header and log in as
any user.

## 3. Configure Authentik

Open `https://authentik.<DOMAIN>` and log in as `akadmin` (initial password
setup is at `/if/flow/initial-setup/`).

1. **Applications → Providers → Create → Proxy Provider**
   - Name `Flowcase Proxy`, default authorization flow
   - External host `https://<DOMAIN>`
   - Internal host `http://flowcase-nginx:80`
   - Mode: Forward auth (single application)
2. **Applications → Applications → Create**: name `Flowcase`, provider
   `Flowcase Proxy`, launch URL `https://<DOMAIN>`.
3. **Applications → Outposts**: edit the embedded outpost and add the
   `Flowcase` application.
4. **Directory → Users**: create users. Names must match Flowcase usernames;
   unknown names are created in Flowcase on first visit.

Open `https://<DOMAIN>`: you should be sent to the Authentik login.

## Troubleshooting

- **Authentik "Not Found"**: the outpost has no application assigned (step 3).
- **Everyone can log in without Authentik**: you started with the plain
  `docker-compose.yml` only. Use both `-f` files.
- **Logs**: `docker compose -f docker-compose.yml -f docker-compose.authentik.yml logs -f <service>`
- **Back up Authentik's database**:
  `docker compose ... exec postgresql pg_dump -U authentik authentik > backup.sql`
