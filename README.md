# <div align="center">🌊 **Flowcase** 🌊</div>

<div align="center">

![Flowcase](https://img.shields.io/badge/Status-Development-yellow)
![License](https://img.shields.io/badge/license-MIT-blue)
![Docker](https://img.shields.io/badge/Docker-Required-blue)

**A cutting-edge open-source container streaming platform**

[Documentation]() • [Installation](#-setup-instructions) • [Discord]() • [Contribute]()

</div>

> [!CAUTION]
> This project is still in development and is not yet ready for production use. Updating Flowcase may cause the database to break. Please use with caution.

<div align="center">

## 🎯 Overview

**Flowcase** provides a free and completely open-source alternative to Kasm Workspaces, enabling secure container streaming for your applications.

</div>

## ✨ Features

<div align="center">

| 🔓 Open-Source | 🔒 Secure Streaming | 🎯 User-Friendly | 🛠 Customizable |
|:-------------:|:------------------:|:----------------:|:--------------:|
| Completely free and community-driven | Stream applications securely using Docker | Easy to deploy and manage | Supports customization for various use cases |

</div>

## 📋 Prerequisites

Before getting started, ensure you have:

- Docker installed on your machine
- Sudo/root access
- Basic knowledge of container management

## 🚀 Setup Instructions

### 1️⃣ Pull the Docker Image

```shell
docker pull flowcaseweb/flowcase:latest
```

### 2️⃣ Create a Docker Network

```shell
docker network create --driver=bridge flowcase_default_network
```

### 3️⃣ Set Up Data Storage

```shell
mkdir /path/to/your/data/
```

### 4️⃣ Run the Flowcase Container

```shell
docker run -it \
  --network flowcase_default_network \
  -p 8080:80 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /path/to/your/data/:/flowcase/data \
  flowcaseweb/flowcase:latest
```

> [!NOTE]
> Run the container without the detached flag (-d) to see the default user's password in the terminal.

---
<div align="center">
Made with ❤️ by the Flowcase Team
</div>
