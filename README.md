#Pull Image
docker pull flowcaseweb/flowcase:<version>

#Create docker network
docker network create --driver=bridge flowcase_default_network

#Run
docker run -it --network flowcase_default_network -p 8080:80 -v /var/run/docker.sock:/var/run/docker.sock -v /pathtoyourdatafolder/:/flowcase/data flowcaseweb/flowcase:<version>

it is recommended to run the container attached as the admin and user password will be printed to the terminal
