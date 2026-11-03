# Flowcase Setup Guide

This guide provides detailed instructions for setting up Flowcase, including both basic and advanced configurations with Authentik authentication.

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
- [Configuration](#configuration)
- [Accessing Flowcase](#accessing-flowcase)
- [Authentik Integration (Optional)](#authentik-integration-optional)
- [Troubleshooting](#troubleshooting)

## Quick Start

For the fastest setup, use our installation script:

**Windows (PowerShell):**
```powershell
.\install.ps1
```

**Linux/Mac:**
```bash
chmod +x install.sh
./install.sh
```

Or follow the [manual installation](#manual-installation) steps below.

## Prerequisites

Before installing Flowcase, ensure you have:

1. **Docker** (version 20.10 or later)
   - Download: https://www.docker.com/get-started
   - Verify: `docker --version`

2. **Docker Compose** (version 2.0 or later)
   - Usually included with Docker Desktop
   - Verify: `docker compose version`

3. **System Requirements:**
   - At least 2GB RAM
   - 10GB free disk space
   - Network access for downloading images

4. **Permissions:**
   - Linux/Mac: User in `docker` group or `sudo` access
   - Windows: Docker Desktop running with WSL2

## Installation Methods

### Automated Installation (Recommended)

#### Windows

1. Open PowerShell in the Flowcase directory
2. Run the installation script:
   ```powershell
   .\install.ps1
   ```
3. Follow the prompts to configure your environment

#### Linux/Mac

1. Make the script executable:
   ```bash
   chmod +x install.sh
   ```
2. Run the installation script:
   ```bash
   ./install.sh
   ```
3. Follow the prompts to configure your environment

### Manual Installation

#### Step 1: Clone or Download Flowcase

If using git:
```bash
git clone https://github.com/flowcase/flowcase.git
cd flowcase
```

Or download and extract the repository.

#### Step 2: Create Environment File

Create a `.env` file in the Flowcase directory:

**For Local Development:**
```env
DOMAIN=localhost
ADMIN_EMAIL=admin@example.com
CA_SERVER=https://acme-staging-v02.api.letsencrypt.org/directory
PG_PASS=<generate-secure-password>
AUTHENTIK_SECRET_KEY=<generate-secure-key>
```

**For Production:**
```env
DOMAIN=yourdomain.com
ADMIN_EMAIL=admin@yourdomain.com
CA_SERVER=https://acme-v02.api.letsencrypt.org/directory
PG_PASS=<generate-secure-password>
AUTHENTIK_SECRET_KEY=<generate-secure-key>
```

**Generate secure values:**
```bash
# Generate PostgreSQL password (24 characters)
openssl rand -base64 24

# Generate Authentik secret key (32 characters minimum)
openssl rand -base64 32
```

#### Step 3: Start Flowcase

```bash
docker compose up -d
```

The `-d` flag runs containers in detached mode (background).

#### Step 4: View Logs

```bash
docker compose logs -f
```

Look for the default admin credentials in the output:
```
Created default users:
-----------------------
Username: admin
Password: <random-password>
-----------------------
```

## Configuration

### Environment Variables

> These variables are only needed for the optional Traefik + Authentik overlay. A plain `docker compose up -d` needs no `.env`.

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `DOMAIN` | Your domain name | `localhost` or `flowcase.example.com` | Yes |
| `ADMIN_EMAIL` | Email for Let's Encrypt notifications | `admin@example.com` | Yes |
| `CA_SERVER` | ACME certificate authority | Staging: `https://acme-staging-v02.api.letsencrypt.org/directory`<br>Production: `https://acme-v02.api.letsencrypt.org/directory` | Yes |
| `PG_PASS` | PostgreSQL database password | Secure random string | Yes |
| `AUTHENTIK_SECRET_KEY` | Authentik secret key | Secure random string (min 32 chars) | Yes |
| `PG_USER` | PostgreSQL username | `authentik` (default) | No |
| `PG_DB` | PostgreSQL database name | `authentik` (default) | No |
| `AUTHENTIK_IMAGE` | Authentik Docker image | `ghcr.io/goauthentik/server` (default) | No |
| `AUTHENTIK_TAG` | Authentik version tag | `2025.6.4` (default) | No |

### Docker Compose Configuration

The main `docker-compose.yml` includes:
- **Flowcase Web**: Main application server
- **Nginx**: Reverse proxy for Flowcase
- **Traefik**: Reverse proxy and load balancer
- **Authentik**: Identity provider (optional authentication)

### Enabling Authentik

The default `docker-compose.yml` runs only Flowcase (web + nginx). Traefik and
Authentik are an optional overlay. See [docs/authentik.md](docs/authentik.md)
for the full steps; in short:

```bash
docker compose -f docker-compose.yml -f docker-compose.authentik.yml up -d
```

The overlay turns on the Traefik middleware and the `--traefik-authentik` flag
together, so you do not edit `docker-compose.yml` by hand.

## Accessing Flowcase

### Without Authentik (Default)

1. **Access the application:**
   - HTTP: `http://localhost`
   - HTTPS: `https://localhost` (certificate warning expected for localhost)

2. **Default credentials** (displayed in terminal on first startup):
   - Username: `admin`
   - Password: `<random-generated-password>`

3. **Alternative user:**
   - Username: `user`
   - Password: `<random-generated-password>`

### With Authentik Enabled

1. **Access Authentik Admin Panel:**
   - URL: `https://authentik.localhost` (or `https://authentik.yourdomain.com`)
   - Default username: `akadmin`
   - Password: Check terminal logs or reset via command

2. **Access Flowcase:**
   - URL: `https://localhost` (or your domain)
   - You'll be redirected to Authentik for authentication
   - After login, you'll access Flowcase

## Authentik Integration (Optional)

Authentik provides enterprise-grade authentication and authorization. Follow these steps to enable it:

### Step 1: Access Authentik Admin

1. Navigate to `https://authentik.localhost` (or your domain)
2. Log in with default credentials:
   - Username: `akadmin`
   - Password: Check your terminal logs for the initial password

### Step 2: Create Proxy Provider

1. Go to **Applications → Providers**
2. Click **Create** → **Proxy Provider**
3. Configure:
   - **Name**: `Flowcase Proxy`
   - **Authorization flow**: Select default authorization flow
   - **External host**: `https://localhost` (or your domain)
   - **Internal host**: `http://flowcase-nginx:80`
   - **Forward auth (single application)**: ✅ Enabled
   - **Forward auth (domain)**: Leave empty
   - **Cookie domain**: Leave empty
4. Click **Create**

### Step 3: Create Application

1. Go to **Applications → Applications**
2. Click **Create**
3. Configure:
   - **Name**: `Flowcase`
   - **Slug**: `flowcase` (auto-generated)
   - **Provider**: Select `Flowcase Proxy`
   - **Launch URL**: `https://localhost` (or your domain)
4. Click **Create**

### Step 4: Configure Outpost

1. Go to **Applications → Outposts**
2. Find the default outpost (or create one)
3. Edit the outpost:
   - **Name**: `Default Outpost`
   - **Integration**: `Docker`
   - **Type**: `Proxy`
   - **Applications**: Select `Flowcase`
   - **Configuration**: Ensure it's enabled
4. Click **Update**

### Step 5: Enable Authentik Middleware and Flag

Start with the overlay, which sets both together:

```bash
docker compose -f docker-compose.yml -f docker-compose.authentik.yml up -d
```

### Step 6: Create Users in Authentik

1. Go to **Directory → Users**
2. Click **Create**
3. Add users that match Flowcase usernames
4. Assign users to groups as needed

### Step 7: Test Authentication

1. Navigate to `https://localhost` (or your domain)
2. You should be redirected to Authentik login
3. After successful login, you'll access Flowcase

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker compose logs
```

**Common issues:**
- Missing environment variables: Ensure `.env` file exists with all required variables
- Port conflicts: Check if ports 80/443 are already in use
- Insufficient resources: Ensure Docker has enough RAM/CPU allocated

### Can't Access Application

**Without Authentik:**
- Try `http://localhost` instead of `https://localhost`
- Check if containers are running: `docker compose ps`
- Check nginx logs: `docker compose logs nginx`

**With Authentik:**
- Ensure Authentik is configured (see [Authentik Integration](#authentik-integration-optional))
- Check Authentik logs: `docker compose logs authentik_server`
- Verify middleware is enabled in `docker-compose.yml`

### Certificate Warnings

For localhost development, certificate warnings are expected. To fix:
1. Use a proper domain name
2. Update `DOMAIN` in `.env`
3. Ensure DNS points to your server
4. Use production CA_SERVER

### Database Connection Issues

**Reset database:**
```bash
docker compose down -v
docker compose up -d
```

⚠️ **Warning**: This will delete all data!

### Authentik "Not Found" Error

This means Authentik is intercepting requests but the proxy provider isn't configured:
1. Follow [Authentik Integration](#authentik-integration-optional) steps
2. Or temporarily disable Authentik middleware

### Reset Authentik Admin Password

```bash
docker compose exec authentik_server ak create_admin
```

### View Application Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f web
docker compose logs -f nginx
docker compose logs -f traefik
```

### Restart Services

```bash
# Restart all
docker compose restart

# Restart specific service
docker compose restart web
docker compose restart nginx
```

### Stop Flowcase

```bash
docker compose down
```

### Remove Everything (Including Data)

```bash
docker compose down -v
```

⚠️ **Warning**: This permanently deletes all data!

## Production Deployment

### Security Checklist

- [ ] Change all default passwords
- [ ] Use strong `PG_PASS` and `AUTHENTIK_SECRET_KEY`
- [ ] Use production `CA_SERVER`
- [ ] Configure proper domain name
- [ ] Enable Authentik for authentication
- [ ] Set up firewall rules
- [ ] Configure backups
- [ ] Enable monitoring/logging
- [ ] Review and update security settings

### Recommended Production Settings

```env
DOMAIN=flowcase.yourdomain.com
ADMIN_EMAIL=admin@yourdomain.com
CA_SERVER=https://acme-v02.api.letsencrypt.org/directory
PG_PASS=<strong-random-password-32-chars>
AUTHENTIK_SECRET_KEY=<strong-random-key-50-chars>
```

### Backup

**Database backup:**
```bash
docker compose exec postgresql pg_dump -U authentik authentik > backup.sql
```

**Restore:**
```bash
docker compose exec -T postgresql psql -U authentik authentik < backup.sql
```

## Getting Help

- **Documentation**: Check this guide and README.md
- **Issues**: Open an issue on GitHub
- **Security**: See SECURITY.md for security-related concerns

## Next Steps

After setup:
1. Log in with default admin credentials
2. Create your first droplet/container
3. Configure user permissions
4. Set up Authentik (optional but recommended)
5. Customize settings as needed

Enjoy using Flowcase! 🎉

