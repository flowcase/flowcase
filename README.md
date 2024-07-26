# Flowcase
A container streaming platform. A Free and completely open-source alternative to Kasm Workspaces.

## Setup

Pull the docker image:
```
docker pull flowcaseweb/flowcase:0.1.0
```

Create a Docker network:
```
docker network create --driver=bridge flowcase_default_network
```

#Create a folder where flowcase will store its database:
```
mkdir /path/to/your/data/
```

#Run the container:
```
docker run -it --network flowcase_default_network -p 8080:80 -v /var/run/docker.sock:/var/run/docker.sock -v /path/to/your/data/:/flowcase/data flowcaseweb/flowcase:0.1.0
```
It is recommend to run without the detached flag (`-d`) as the default user's password will be printed in the terminal.
