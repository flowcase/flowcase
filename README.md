# Flowcase
## FlowcaseWeb

FlowcaseWeb is a container streaming platform that provides a free and completely open-source alternative to Kasm Workspaces.

### Setup

To get started with FlowcaseWeb, follow these steps:

1. Pull the Docker image:

```shell
docker pull flowcaseweb/flowcase:0.1.0
```

2. Create a Docker network:

```shell
docker network create --driver=bridge flowcase_default_network
```

3. Create a folder to store FlowcaseWeb's database:

```shell
mkdir /path/to/your/data/
```

4. Run the container:

```shell
docker run -it --network flowcase_default_network -p 8080:80 -v /var/run/docker.sock:/var/run/docker.sock -v /path/to/your/data/:/flowcase/data flowcaseweb/flowcase:0.1.0
```

Note: It is recommended to run the container without the detached flag (`-d`) as the default user's password will be printed in the terminal.

Enjoy using FlowcaseWeb for your container streaming needs!

