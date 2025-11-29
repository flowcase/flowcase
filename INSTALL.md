# Installation Guide

This is a quick reference guide. For detailed instructions, see [SETUP.md](SETUP.md).

## Quick Installation

### Automated (Recommended)

**Windows:**
```powershell
.\install.ps1
```

**Linux/Mac:**
```bash
chmod +x install.sh
./install.sh
```

### Manual

1. **Create `.env` file:**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

2. **Start services:**
   ```bash
   docker compose up -d
   ```

3. **Get credentials:**
   ```bash
   docker compose logs -f
   # Look for "Created default users"
   ```

4. **Access:**
   - Open `http://localhost`
   - Login with credentials from logs

## What Gets Installed

- Flowcase web application
- Nginx reverse proxy
- Traefik with automatic HTTPS
- Authentik (optional authentication)
- PostgreSQL database
- Redis cache

## Next Steps

- Read [SETUP.md](SETUP.md) for detailed configuration
- Configure Authentik (optional) - see SETUP.md
- Create your first container/droplet
- Customize settings

## Troubleshooting

See [SETUP.md](SETUP.md#troubleshooting) for detailed troubleshooting.

Quick fixes:
```bash
# Check status
docker compose ps

# View logs
docker compose logs -f

# Restart
docker compose restart

# Reset (⚠️ deletes data)
docker compose down -v
docker compose up -d
```

