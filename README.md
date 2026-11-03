# <div align="center">**Flowcase**</div>

<div align="center">

![Flowcase](https://img.shields.io/badge/Status-Development-yellow)
![License](https://img.shields.io/badge/license-MIT-blue)
![Docker](https://img.shields.io/badge/Docker-Required-blue)

**A cutting-edge open-source container streaming platform**

</div>

> [!CAUTION]
> This project is still in development and is not yet ready for production use. We do not currently support upgrading from older versions. Please use with caution.

# What is Flowcase?
**Flowcase** is a free and completely open-source alternative to Kasm Workspaces, enabling secure container streaming for your applications. Stream desktop applications, development environments, and more through your web browser using Docker containers.

## Features

<div align="center">

| Open-Source | Secure Streaming | User-Friendly | Customizable | Multi-Platform |
|:-------------:|:------------------:|:----------------:|:--------------:|:--------------:|
| Completely free and community-driven | Stream applications securely using Docker | Easy to deploy and manage | Supports customization for various use cases | Supports Windows, Linux, and macOS |

</div>


## Requirements
- Docker (Compose)
- System requirements:
  - At least 2GB RAM
  - 10GB free disk space
  - Network access for downloading images

## Installation

### Automatic Installation:
**Windows (PowerShell):**
```powershell
.\install.ps1
```

**Linux/Mac:**
```bash
chmod +x install.sh
./install.sh
```

### Manual Installation:

```bash
git clone https://github.com/flowcase/flowcase.git
cd flowcase
docker compose up -d
docker compose logs web    # shows the generated admin and user passwords
```

Open `http://localhost`. If you want to use another port, use `FLOWCASE_PORT=8080 docker compose up -d`.

Then log in as `admin`, open **Registry** in the admin panel and add droplets.
Images download in the background; give them a few minutes.

## Documentation

- [QUICKSTART.md](QUICKSTART.md): fastest path from zero to a running desktop
- [INSTALL.md](INSTALL.md) and [SETUP.md](SETUP.md): detailed install, configuration, troubleshooting and production notes
- [docs/authentik.md](docs/authentik.md): optional Traefik + Authentik (SSO and automatic HTTPS)
- [DOCS.md](DOCS.md): index of all docs
- [Wiki](https://github.com/flowcase/flowcase/wiki): admin guide, droplets, API

## Security

- Flowcase mounts the Docker socket, so treat the host as trusted-only.
- For SSO and built-in HTTPS see [docs/authentik.md](docs/authentik.md)
  (Traefik + Authentik, optional) and the checklist in [SETUP.md](SETUP.md#production-deployment).

## Production

- Put Flowcase behind HTTPS. The simplest way is your own reverse proxy
  pointing at the `nginx` container (port 80).
- Flowcase mounts the Docker socket, so treat the host as trusted-only.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.