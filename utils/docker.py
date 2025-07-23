import os
import re
import docker
import threading
import time
from utils.logger import log
from __init__ import __version__

docker_client = None

def init_docker():
	global docker_client
	
	try:
		docker_client = docker.DockerClient(base_url="unix:///var/run/docker.sock")
		docker_client.ping()
  
		return docker_client
		
	except Exception as e:
		print(f"Docker connection failed: {str(e)}")
	return None

def is_docker_available():
	"""Return True if the Docker client is initialized and working"""
	global docker_client
	if not docker_client:
		return False
	
	try:
		docker_client.ping()
		return True
	except Exception:
		return False

def get_docker_version():
	"""Return Docker version or error message if not available"""
	global docker_client
	if not docker_client:
		return "Docker not available"
	
	try:
		return docker_client.version()["Version"]
	except Exception as e:
		return f"Error: {str(e)}"

def cleanup_containers():
	"""Delete any existing flowcase containers"""
	global docker_client
	if not docker_client:
		print("No Docker client available, skipping container cleanup")
		return
		
	try:
		containers = docker_client.containers.list(all=True)
		for container in containers:
			regex = re.compile(r"flowcase_generated_([a-z0-9]+(-[a-z0-9]+)+)", re.IGNORECASE)
			if regex.match(container.name):
				print(f"Stopping container {container.name}")
				try:
					container.stop()
					container.remove()
				except Exception as e:
					print(f"Error stopping container {container.name}: {str(e)}")
	except Exception as e:
		print(f"Error listing containers: {str(e)}")

def pull_images(app):
	"""Pull docker images for droplets"""
	global docker_client
	if not docker_client:
		return
		
	from models.droplet import Droplet
	
	with app.app_context():
		try:
			droplets = Droplet.query.all()
  
			# Add guac image
			droplets.append(Droplet(
				container_docker_registry="https://index.docker.io/v1/",
				container_docker_image="flowcaseweb/flowcase-guac:" + __version__
			))
  
			for droplet in droplets:
				if droplet.container_docker_image is None:
					continue
				log("INFO", f"Pulling Docker image {droplet.container_docker_image}")
				if droplet.container_docker_registry and "docker.io" not in droplet.container_docker_registry:
					# remove trailing slash if present
					registry = droplet.container_docker_registry.rstrip("/")
					image = f"{registry}/{droplet.container_docker_image}"
				else:
					image = droplet.container_docker_image
				tag = image.split(":")[-1] if ":" in image else "latest"
				try:
					docker_client.images.pull(image, tag)
				except Exception as e:
					log("ERROR", f"Error pulling Docker image {droplet.container_docker_image}: {e}")
		except Exception as e:
			log("ERROR", f"Error in pull_images: {str(e)}")

def start_image_pull_thread(app):
	"""Start a thread to continuously pull images"""
	def thread_pull_images():
		while True:
			try:
				with app.app_context():
					pull_images(app)
			except Exception as e:
				print(f"Error in image pull thread: {str(e)}")
			time.sleep(60)
			
	threading.Thread(target=thread_pull_images, daemon=True).start() 