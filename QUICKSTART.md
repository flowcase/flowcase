# Quick Start Guide

Get Flowcase up and running in 5 minutes!

## Prerequisites

- Docker Desktop installed and running
- 2GB+ RAM available
- 10GB+ free disk space

## Installation

### Step 1: Run Installation Script

**Windows:**
```powershell
.\install.ps1
```

**Linux/Mac:**
```bash
chmod +x install.sh
./install.sh
```

### Step 2: Wait for Services

The script will:
- Generate secure passwords
- Create configuration files
- Start all containers
- Display access information

**First run takes 2-5 minutes** (downloading images)

### Step 3: Get Credentials

Watch the terminal output for:
```
Created default users:
-----------------------
Username: admin
Password: <random-password>
-----------------------
```

Or view logs:
```bash
docker compose logs -f
```

### Step 4: Access Flowcase

1. Open browser: `http://localhost`
2. Login with credentials from Step 3
3. Start creating containers!

## That's It! 🎉

You're now running Flowcase!

## Next Steps

- **Configure Authentik** (optional): See [SETUP.md](SETUP.md#authentik-integration-optional)
- **Create your first droplet**: Use the web interface
- **Customize settings**: Explore the admin panel
- **Read the docs**: Check [SETUP.md](SETUP.md) for advanced configuration

## Common Commands

```bash
# View logs
docker compose logs -f

# Stop Flowcase
docker compose down

# Start Flowcase
docker compose up -d

# Restart
docker compose restart
```

## Troubleshooting

**Can't access?**
- Check containers: `docker compose ps`
- View logs: `docker compose logs -f`
- Try `http://localhost` instead of `https://localhost`

**Need help?**
- See [SETUP.md](SETUP.md#troubleshooting) for detailed troubleshooting
- Check [README.md](README.md) for more information

