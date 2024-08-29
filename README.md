# 🌊 **Flowcase** 🌊

**Flowcase** is a cutting-edge container streaming platform that provides a free and completely open-source alternative to Kasm Workspaces.

## 🚀 Setup Instructions 🚀

To get started with Flowcase, follow these simple steps:

### 1️⃣ Pull the Docker Image

First, you need to pull the Flowcase Docker image from the repository. Open your terminal and run:

```shell
docker pull flowcaseweb/flowcase:latest
```

### 2️⃣ Create a Docker Network

Next, create a Docker network for Flowcase. This network will facilitate communication between containers:

```shell
docker network create --driver=bridge flowcase_default_network
```

### 3️⃣ Set Up Data Storage

Create a directory on your local machine to store FlowcaseWeb's database. Replace `/path/to/your/data/` with your desired path:

```shell
mkdir /path/to/your/data/
```

### 4️⃣ Run the Flowcase Container

Now, it's time to run the Flowcase container. Ensure you replace `/path/to/your/data/` with the path you created in the previous step:

```shell
docker run -it --network flowcase_default_network -p 8080:80 -v /var/run/docker.sock:/var/run/docker.sock -v /path/to/your/data/:/flowcase/data flowcaseweb/flowcase:0.1.0
```

Note: It is recommended to run the container without the detached flag (-d) as the default user's password will be printed in the terminal.

