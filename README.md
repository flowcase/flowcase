# <div align="center">🌊 **Flowcase**</div>

<div align="center">

![Flowcase](https://img.shields.io/badge/Status-Development-yellow)
![License](https://img.shields.io/badge/license-MIT-blue)
![Docker](https://img.shields.io/badge/Docker-Required-blue)

**A cutting-edge open-source container streaming platform**

</div>

> [!CAUTION]
> This project is still in development and is not yet ready for production use. We do not currently support upgrading from older versions. Please use with caution.

## What is Flowcase?

**Flowcase** is a free and completely open-source alternative to Kasm Workspaces, enabling secure container streaming for your applications. Stream desktop applications, development environments, and more through your web browser using Docker containers.

## Features

<div align="center">

| Open-Source | Secure Streaming | User-Friendly | Customizable | Multi-Platform |
|:-------------:|:------------------:|:----------------:|:--------------:|:--------------:|
| Completely free and community-driven | Stream applications securely using Docker | Easy to deploy and manage | Supports customization for various use cases | Supports Windows, Linux, and macOS |

</div>

## Quick Start

### Option 1: Automated Installation (Recommended)

**Windows (PowerShell):**
```powershell
.\install.ps1
```

**Linux/Mac:**
```bash
chmod +x install.sh
./install.sh
```

The installation script will:
- ✅ Check prerequisites
- ✅ Generate secure passwords
- ✅ Create configuration files
- ✅ Start all services
- ✅ Display access information

### Option 2: Manual Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/flowcase/flowcase.git
   cd flowcase
   ```

2. **Create `.env` file:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start Flowcase:**
   ```bash
   docker compose up -d
   ```

4. **View logs for credentials:**
   ```bash
   docker compose logs -f
   ```

5. **Access Flowcase:**
   - Open `http://localhost` or `https://localhost`
   - Use the default admin credentials shown in the logs

## Prerequisites

Before installing Flowcase, ensure you have:

- **Docker** (version 20.10 or later)
  - [Download Docker Desktop](https://www.docker.com/get-started)
  - Verify: `docker --version`

- **Docker Compose** (version 2.0 or later)
  - Usually included with Docker Desktop
  - Verify: `docker compose version`

- **System Requirements:**
  - At least 2GB RAM
  - 10GB free disk space
  - Network access for downloading images

- **Permissions:**
  - Linux/Mac: User in `docker` group or `sudo` access
  - Windows: Docker Desktop running with WSL2

## Documentation

- **[SETUP.md](SETUP.md)** - Comprehensive setup guide with detailed instructions
  - Configuration options
  - Authentik integration
  - Troubleshooting
  - Production deployment

- **[SECURITY.md](SECURITY.md)** - Security information and reporting

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `DOMAIN` | Your domain name | `localhost` or `flowcase.example.com` | Yes |
| `ADMIN_EMAIL` | Email for Let's Encrypt notifications | `admin@example.com` | Yes |
| `CA_SERVER` | ACME certificate authority | Staging: `https://acme-staging-v02.api.letsencrypt.org/directory`<br>Production: `https://acme-v02.api.letsencrypt.org/directory` | Yes |
| `PG_PASS` | PostgreSQL database password | Secure random string | Yes |
| `AUTHENTIK_SECRET_KEY` | Authentik secret key | Secure random string (min 32 chars) | Yes |

**Generate secure values:**
```bash
# Generate PostgreSQL password
openssl rand -base64 24

# Generate Authentik secret key
openssl rand -base64 32
```

### Local Development

For local development, use these settings:

```env
DOMAIN=localhost
ADMIN_EMAIL=admin@example.com
CA_SERVER=https://acme-staging-v02.api.letsencrypt.org/directory
PG_PASS=<generate-secure-password>
AUTHENTIK_SECRET_KEY=<generate-secure-key>
```

### Production

For production deployment:

```env
DOMAIN=flowcase.yourdomain.com
ADMIN_EMAIL=admin@yourdomain.com
CA_SERVER=https://acme-v02.api.letsencrypt.org/directory
PG_PASS=<strong-random-password-32-chars>
AUTHENTIK_SECRET_KEY=<strong-random-key-50-chars>
```

## Accessing Flowcase

### Default Access (Without Authentik)

1. Navigate to `http://localhost` or `https://localhost`
2. Use the default credentials displayed in the terminal logs:
   - Username: `admin`
   - Password: `<random-generated-password>`

### With Authentik (Optional - Requires Setup)

Authentik integration is **disabled by default**. To enable it:

1. **Configure Authentik** (see [SETUP.md](SETUP.md#authentik-integration-optional) for detailed steps):
   - Access Authentik Admin: `https://authentik.localhost`
   - Create a Proxy Provider
   - Create an Application
   - Configure the Outpost

2. **Enable Authentik in docker-compose.yml**:
   - Uncomment the middleware line (line 41): `- traefik.http.routers.flowcase.middlewares=authentik@file`
   - Uncomment the flag (line 24): `--traefik-authentik`
   - Restart: `docker compose restart web nginx traefik`

3. **Access Flowcase**: `https://localhost` (will redirect to Authentik for login)

> [!NOTE]
> Authentik is disabled by default for easier initial setup. Follow the complete setup guide in [SETUP.md](SETUP.md#authentik-integration-optional) to enable it.

## Common Commands

```bash
# Start Flowcase
docker compose up -d

# View logs
docker compose logs -f

# View logs for specific service
docker compose logs -f web

# Stop Flowcase
docker compose down

# Restart services
docker compose restart

# Check service status
docker compose ps
```

## Architecture

Flowcase consists of the following components:

- **Flowcase Web**: Main application server (Flask)
- **Nginx**: Reverse proxy for Flowcase
- **Traefik**: Reverse proxy and load balancer with automatic HTTPS
- **Authentik**: Identity provider (optional, for authentication)
- **PostgreSQL**: Database for Authentik
- **Redis**: Cache for Authentik

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker compose logs

# Check service status
docker compose ps
```

### Can't Access Application

- Ensure containers are running: `docker compose ps`
- Check nginx logs: `docker compose logs nginx`
- Try `http://localhost` instead of `https://localhost`

### Certificate Warnings

For localhost development, certificate warnings are expected. For production:
- Use a proper domain name
- Update `DOMAIN` in `.env`
- Ensure DNS points to your server

### Reset Everything

⚠️ **Warning**: This will delete all data!

```bash
docker compose down -v
docker compose up -d
```

For more troubleshooting help, see [SETUP.md](SETUP.md#troubleshooting).

## Contributing

Contributions are welcome! Please feel free to:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

Please read our contributing guidelines and code of conduct before submitting.

## Security

- **Security Issues**: Please report security vulnerabilities to the maintainers privately (see [SECURITY.md](SECURITY.md))
- **Updates**: Keep your installation updated with the latest releases
- **Credentials**: Always use strong, randomly generated passwords
- **Production**: Follow the production deployment checklist in [SETUP.md](SETUP.md#production-deployment)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: Check [SETUP.md](SETUP.md) for detailed guides
- **Issues**: Open an issue on [GitHub](https://github.com/flowcase/flowcase/issues)
- **Discussions**: Join discussions on [GitHub Discussions](https://github.com/flowcase/flowcase/discussions)

## Roadmap

- [ ] Production-ready release
- [ ] Upgrade/migration support
- [ ] Additional authentication providers
- [ ] Enhanced container management
- [ ] Performance optimizations
- [ ] Additional documentation

---

<div align="center">
Made with ❤️ by the Flowcase Team
</div>
