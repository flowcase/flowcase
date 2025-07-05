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

**Flowcase** is a free and completely open-source alternative to Kasm Workspaces, enabling secure container streaming for your applications.

## Features

<div align="center">

| Open-Source | Secure Streaming | User-Friendly | Customizable | Multi-Platform |
|:-------------:|:------------------:|:----------------:|:--------------:|:--------------:|
| Completely free and community-driven | Stream applications securely using Docker | Easy to deploy and manage | Supports customization for various use cases | Supports Windows, Linux, and macOS |

</div>

## Prerequisites

Before getting started, ensure you have:

- Docker and Docker Compose installed on your machine
- Sudo/root access
- Basic knowledge of container management

## Setup Instructions

### 1. Download the `docker-compose.yml` file and place it in a folder of your choice.

```shell
curl -L https://raw.githubusercontent.com/flowcase/flowcase/refs/heads/main/docker-compose.yml -o docker-compose.yml
```

### 2. Launch with Docker Compose

```shell
docker compose up
```

> [!NOTE]
> Default admin and user logins will be displayed in the terminal output on initial startup.

### 3. Access Flowcase

Open your browser and navigate to:

```
http://localhost:80
```

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.
Any security issues should be reported to security@flowcase.org.

---
<div align="center">
Made with ❤️ by the Flowcase Team
</div>
