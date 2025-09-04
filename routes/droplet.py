import os
import re
import time
import base64
import json
from typing import Tuple
import docker
import docker.types
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from flask import Blueprint, jsonify, request, render_template, redirect, make_response, send_from_directory
from flask_login import login_required, current_user
import psutil
from __init__ import db, __version__
from models.droplet import Droplet, DropletInstance
from models.user import User, Group
from utils.logger import log
import utils.docker
import threading

def timeout_wrapper(func, timeout_seconds=300):
	"""Execute a function with a timeout, returning (success, result/error)"""
	result = [None]
	error = [None]
	completed_event = threading.Event()
	
	def target():
		try:
			result[0] = func()
		except Exception as e:
			error[0] = str(e)
		finally:
			completed_event.set()
	
	thread = threading.Thread(target=target)
	thread.daemon = True
	thread.start()
	
	# Wait for completion or timeout using Event
	if completed_event.wait(timeout=timeout_seconds):
		if error[0]:
			return False, error[0]
		return True, result[0]
	else:
		return False, "Operation timed out"

droplet_bp = Blueprint('droplet', __name__)

@droplet_bp.route('/api/droplets', methods=['GET'])
@login_required
def get_droplets():
	all_droplets = Droplet.query.all()
	
	# Get user's groups
	user_groups = current_user.get_groups()
	
	# Check if user is in Admin group
	is_admin = False
	for group_id in user_groups:
		group = Group.query.filter_by(id=group_id).first()
		if group and group.display_name == "Admin":
			is_admin = True
			break
	
	# Filter droplets based on group restrictions
	visible_droplets = []
	for droplet in all_droplets:
		# Admin users can see all droplets
		if is_admin:
			visible_droplets.append(droplet)
			continue
			
		# Get droplet's restricted groups
		droplet_groups = []
		if droplet.restricted_groups:
			droplet_groups = droplet.restricted_groups.split(',')
		
		# Check if user shares at least one group with the droplet
		for group_id in user_groups:
			if group_id in droplet_groups:
				visible_droplets.append(droplet)
				break
	
	# Sort droplets by display name
	visible_droplets = sorted(visible_droplets, key=lambda x: x.display_name)
 
	response = {
		"success": True,
		"droplets": []
	}
 
	for droplet in visible_droplets:
		response["droplets"].append({
			"id": droplet.id,
			"display_name": droplet.display_name,
			"description": droplet.description,
			"image_path": droplet.image_path,
			"droplet_type": droplet.droplet_type,
			"container_docker_image": droplet.container_docker_image,
			"container_docker_registry": droplet.container_docker_registry,
			"container_cores": droplet.container_cores,
			"container_memory": droplet.container_memory,
			"server_ip": droplet.server_ip,
			"server_port": droplet.server_port,
		})
 
	return jsonify(response)

@droplet_bp.route('/api/instances', methods=['GET'])
@login_required
def get_instances():
	instances = DropletInstance.query.filter_by(user_id=current_user.id).all()
 
	response = {
		"success": True,
		"instances": []
	}
 
	for instance in instances:
		droplet = Droplet.query.filter_by(id=instance.droplet_id).first()
		
		# Try to get container IP if it exists
		ip = "N/A"
		try:
			container = utils.docker.docker_client.containers.get(f"flowcase_generated_{instance.id}")
			networks = container.attrs['NetworkSettings']['Networks']
			
			# For nginx connectivity, prioritize the default network
			if 'flowcase_default_network' in networks and networks['flowcase_default_network']['IPAddress']:
				ip = networks['flowcase_default_network']['IPAddress']
			
			# If no IP found on default network, check the droplet's specified network
			elif droplet.container_network and droplet.container_network in networks:
				if networks[droplet.container_network]['IPAddress']:
					ip = networks[droplet.container_network]['IPAddress']
			
			# If still no IP found, try other network name variations
			if ip == "N/A":
				for network_name in ['default_network', 'bridge']:
					if network_name in networks and networks[network_name]['IPAddress']:
						ip = networks[network_name]['IPAddress']
						break
		except:
			# Container might not exist or other error
			pass
			
		response["instances"].append({
			"id": instance.id,
			"created_at": instance.created_at,
			"updated_at": instance.updated_at,
			"ip": ip,
			"droplet": {
				"id": droplet.id,
				"display_name": droplet.display_name,
				"description": droplet.description,
				"image_path": droplet.image_path,
				"droplet_type": droplet.droplet_type,
				"container_docker_image": droplet.container_docker_image,
				"container_docker_registry": droplet.container_docker_registry,
				"container_cores": droplet.container_cores,
				"container_memory": droplet.container_memory,
				"server_ip": droplet.server_ip,
				"server_port": droplet.server_port,
			}
		})
 
	return jsonify(response)

@droplet_bp.route('/api/instance/request', methods=['POST'])
@login_required
def request_new_instance():
	droplet_id = request.json.get('droplet_id')
	droplet = Droplet.query.filter_by(id=droplet_id).first()
	if not droplet:
		return jsonify({"success": False, "error": "Droplet not found"}), 404
		
	# Check if user has access to this droplet
	user_groups = current_user.get_groups()
	
	# Check if user is in Admin group
	is_admin = False
	for group_id in user_groups:
		group = Group.query.filter_by(id=group_id).first()
		if group and group.display_name == "Admin":
			is_admin = True
			break
	
	# Admin users can access all droplets
	if not is_admin:
		# Get droplet's restricted groups
		droplet_groups = []
		if droplet.restricted_groups:
			droplet_groups = droplet.restricted_groups.split(',')
		
		has_access = False
		
		# Check if user shares at least one group with the droplet
		for group_id in user_groups:
			if group_id in droplet_groups:
				has_access = True
				break
		
		if not has_access:
			return jsonify({"success": False, "error": "You don't have access to this droplet"}), 403

	# Check if droplet is a guacamole droplet
	isGuacDroplet: bool = False
	if droplet.droplet_type in ["vnc", "rdp", "ssh"]:
		isGuacDroplet = True

	# Check if system has enough resources to request this droplet, guacamole droplets do not have resource checks
	if not isGuacDroplet:
		success, error = check_resources(droplet)
		if not success:
			return jsonify({"success": False, "error": error}), 400
 
	# Check if docker client is available
	if not utils.docker.docker_client:
		log("ERROR", "Docker client not available")
		return jsonify({"success": False, "error": "Docker service is not available"}), 500

	# Check if docker image is downloaded
	images = utils.docker.docker_client.images.list()
	image_name = droplet.container_docker_image
	if droplet.container_docker_registry and "docker.io" not in droplet.container_docker_registry:
		image_name = droplet.container_docker_registry + "/" + image_name

	image_exists = False
	for image in images:
		if isGuacDroplet and f"flowcaseweb/flowcase-guac:{__version__}" in image.tags:
			image_exists = True
			break

		if image_name in image.tags:
			image_exists = True
			break
		
	if not image_exists:
		log("WARNING", f"Docker image {droplet.container_docker_image} not found. Please wait a few minutes and try again.")
		return jsonify({"success": False, "error": "Docker image not found. Image might still be downloading."}), 400
	
		"""
		try:
			# Use the existing pull_single_image function with timeout
			def pull_with_timeout():
				return utils.docker.pull_single_image(
					droplet.container_docker_registry, 
					droplet.container_docker_image
				)
			
			success, message = timeout_wrapper(pull_with_timeout, timeout_seconds=300)
			
			if not success:
				if "timed out" in message:
					return jsonify({"success": False, "error": "Image download timed out. Please try again or download manually from the admin panel."}), 408
				else:
					log("ERROR", f"Failed to pull Docker image {image_name}: {message}")
					return jsonify({"success": False, "error": f"Failed to download Docker image. Error: {message}"}), 400
			
			log("INFO", f"Successfully pulled Docker image {image_name}")
		except Exception as e:
			log("ERROR", f"Failed to pull Docker image {image_name}: {str(e)}")
			return jsonify({"success": False, "error": f"Failed to download Docker image. Error: {str(e)}"}), 400
		"""

	# Create a new instance
	instance = DropletInstance(droplet_id=droplet_id, user_id=current_user.id)
	db.session.add(instance)
	db.session.commit()
 
	# Create a docker container
	log("INFO", f"Creating new instance for user {current_user.username} with droplet {droplet.display_name}")
 
	name = f"flowcase_generated_{instance.id}"
 
	request_resolution = request.json.get('resolution')
	if len(request_resolution) < 10 and re.match(r"[0-9]+x[0-9]+", request_resolution):
		resolution = request_resolution
	else:
		resolution = "1280x720"
  
	# Persistent Profile using Docker volumes
	volume_mount = None
	if droplet.container_persistent_profile_path and droplet.container_persistent_profile_path != "" and not isGuacDroplet:
		
		# Generate volume name based on user, droplet, and path
		volume_name_template = droplet.container_persistent_profile_path
		
		# Replace variables for volume name
		volume_name = volume_name_template.replace("{user_id}", str(current_user.id))
		volume_name = volume_name.replace("{user_name}", current_user.username)
		volume_name = volume_name.replace("{droplet_id}", str(droplet_id))
		volume_name = volume_name.replace("{droplet_name}", droplet.display_name)
		
		# Create a safe volume name (Docker volume names have restrictions)
		volume_name = re.sub(r'[^a-zA-Z0-9._-]', '_', volume_name)
		volume_name = f"flowcase_profile_{volume_name}"
		
		# Mount to user's home directory in container
		container_path = "/home/flowcase-user"
		
		try:
			# Check if volume exists, create if not
			try:
				utils.docker.docker_client.volumes.get(volume_name)
				log("INFO", f"Using existing Docker volume: {volume_name}")
			except docker.errors.NotFound:
				# Volume doesn't exist, create it
				volume = utils.docker.docker_client.volumes.create(name=volume_name)
				log("INFO", f"Created new Docker volume: {volume_name}")
			
			# Create mount configuration for Docker volume
			volume_mount = docker.types.Mount(
				target=container_path,
				source=volume_name,
				type="volume"
			)
			
		except Exception as e:
			log("ERROR", f"Error setting up Docker volume {volume_name}: {str(e)}")
			db.session.delete(instance)
			db.session.commit()
			return jsonify({"success": False, "error": "Failed to setup persistent profile volume"}), 500
	
	# Create the container
	try:
		# Get the appropriate network for this droplet
		network = utils.docker.get_network_for_droplet(droplet)
		log("INFO", f"Using network {network} for droplet {droplet.display_name}")
		
		# Create container with the specific network
		if not isGuacDroplet:
			container = utils.docker.docker_client.containers.run(
				image=image_name,
				name=name,
				environment={"DISPLAY": ":1", "VNC_PW": current_user.auth_token, "VNC_RESOLUTION": resolution},
				detach=True,
				network=network,
				mem_limit=f"{droplet.container_memory}000000",
				cpu_shares=int(droplet.container_cores * 1024),
				mounts=[volume_mount] if volume_mount else None,
			)
		else: # Guacamole droplet
			container = utils.docker.docker_client.containers.run(
				image=f"flowcaseweb/flowcase-guac:{__version__}",
				name=name,
				environment={"GUAC_KEY": current_user.auth_token[:32]},
				detach=True,
				network=network,
			)
		
		# If using a non-default network, also connect to the default network for nginx connectivity
		if network != "flowcase_default_network":
			try:
				default_network = utils.docker.docker_client.networks.get("flowcase_default_network")
				default_network.connect(container.id)
				log("INFO", f"Connected container {name} to flowcase_default_network for nginx connectivity")
			except Exception as e:
				log("WARNING", f"Could not connect container to default network: {str(e)}")
 
		log("INFO", f"Instance created for user {current_user.username} with droplet {droplet.display_name}")
 
		# Wait for container to start and verify it's running with timeout
		max_wait_time = 30  # Maximum wait time in seconds
		check_interval = 1  # Check every 1 second
		waited_time = 0
		
		while waited_time < max_wait_time:
			time.sleep(check_interval)
			waited_time += check_interval
			
			try:
				container.reload()
				if container.status == 'running':
					log("INFO", f"Container {name} is running after {waited_time} seconds")
					break
				elif container.status in ['exited', 'dead']:
					log("ERROR", f"Container {name} failed to start, status: {container.status}")
					# Get container logs for debugging
					try:
						logs = container.logs().decode('utf-8')[-1000:]  # Last 1000 chars
						log("ERROR", f"Container logs: {logs}")
					except:
						pass
					container.remove(force=True)
					db.session.delete(instance)
					db.session.commit()
					return jsonify({"success": False, "error": f"Container failed to start (status: {container.status})"}), 500
			except Exception as e:
				log("ERROR", f"Error checking container status: {str(e)}")
				container.remove(force=True)
				db.session.delete(instance)
				db.session.commit()
				return jsonify({"success": False, "error": "Failed to verify container status"}), 500
		
		# Final check if we timed out
		if waited_time >= max_wait_time:
			log("ERROR", f"Container {name} startup timed out after {max_wait_time} seconds")
			try:
				logs = container.logs().decode('utf-8')[-1000:]  # Last 1000 chars
				log("ERROR", f"Container logs: {logs}")
			except:
				pass
			container.remove(force=True)
			db.session.delete(instance)
			db.session.commit()
			return jsonify({"success": False, "error": "Container startup timed out"}), 500
 
		# Create nginx config - get fresh container info and handle network name variations
		try:
			container = utils.docker.docker_client.containers.get(f"flowcase_generated_{instance.id}")
			networks = container.attrs['NetworkSettings']['Networks']
			
			# For nginx connectivity, prioritize the default network
			ip = None
			
			# First check the default network for nginx connectivity
			if 'flowcase_default_network' in networks and networks['flowcase_default_network']['IPAddress']:
				ip = networks['flowcase_default_network']['IPAddress']
				log("INFO", f"Found container IP {ip} on default network (for nginx connectivity)")
			
			# If no IP found on default network, check the droplet's specified network
			if not ip and droplet.container_network and droplet.container_network in networks:
				if networks[droplet.container_network]['IPAddress']:
					ip = networks[droplet.container_network]['IPAddress']
					log("INFO", f"Found container IP {ip} on specified network {droplet.container_network}")
			
			# If still no IP found, try other network name variations
			if not ip:
				for network_name in ['default_network', 'bridge']:
					if network_name in networks and networks[network_name]['IPAddress']:
						ip = networks[network_name]['IPAddress']
						log("INFO", f"Found container IP {ip} on network {network_name}")
						break
			
			if not ip:
				log("ERROR", f"Could not find IP address for container {name}")
				container.remove(force=True)
				db.session.delete(instance)
				db.session.commit()
				return jsonify({"success": False, "error": "Could not determine container IP address"}), 500
				
		except Exception as e:
			log("ERROR", f"Error getting container network info: {str(e)}")
			container.remove(force=True)
			db.session.delete(instance)
			db.session.commit()
			return jsonify({"success": False, "error": "Failed to get container network information"}), 500

		# Generate nginx configuration
		nginx_config = generate_nginx_config(instance, droplet, ip, current_user)
 
		try:
			write_nginx_config(instance, nginx_config)
		except Exception as e:
			log("ERROR", f"Error writing nginx config: {str(e)}")
			container.remove(force=True)
			db.session.delete(instance)
			db.session.commit()
			return jsonify({"success": False, "error": "Failed to write nginx configuration"}), 500
		
		reload_nginx()
 
	except Exception as e:
		log("ERROR", f"Error creating container for user {current_user.username}: {str(e)}")
		# Cleanup on failure
		try:
			if 'container' in locals():
				container.remove(force=True)
		except:
			pass
		db.session.delete(instance)
		db.session.commit()
		return jsonify({"success": False, "error": f"Failed to create container: {str(e)}"}), 500

	return jsonify({"success": True, "instance_id": instance.id})

def check_resources(droplet: Droplet) -> Tuple[bool, str]:
	instances = DropletInstance.query.all()
		
	# Collect all droplet IDs and fetch droplets in a single query to avoid N+1 problem
	droplet_ids = [instance.droplet_id for instance in instances]
	droplets = Droplet.query.filter(Droplet.id.in_(droplet_ids)).all() if droplet_ids else []
	droplet_dict = {droplet.id: droplet for droplet in droplets}
	
	total_allocated_memory = 0
	total_allocated_cores = 0
	for instance in instances:
		instance_droplet = droplet_dict.get(instance.droplet_id)
		if instance_droplet:
			total_allocated_cores += instance_droplet.container_cores
			total_allocated_memory += instance_droplet.container_memory
	
	# Get system resources
	system_cores = os.cpu_count()
	total_memory = psutil.virtual_memory().total / 1024 / 1024  # Convert to MB
	
	# Calculate what would be used after adding this droplet
	projected_memory_usage = total_allocated_memory + droplet.container_memory
	projected_core_usage = total_allocated_cores + droplet.container_cores
	
	# Apply reasonable safety margins and allow oversubscription for CPU
	# CPU: Allow 2x oversubscription (containers share CPU efficiently via CPU shares)
	# Memory: Use 85% of total memory to leave room for system operations
	max_allowed_memory = total_memory * 0.85
	max_allowed_cores = system_cores * 2.0
	
	if projected_memory_usage > max_allowed_memory:
		log("ERROR", f"Insufficient memory for user {current_user.username} to request droplet {droplet.display_name} - would use {projected_memory_usage}MB of {max_allowed_memory}MB allowed")
		return False, "Insufficient memory to start this droplet"
	
	if projected_core_usage > max_allowed_cores:
		log("ERROR", f"Insufficient CPU cores for user {current_user.username} to request droplet {droplet.display_name} - would use {projected_core_usage} of {max_allowed_cores} cores allowed")
		return False, "Insufficient CPU cores to start this droplet"
	
	return True, ""

def generate_nginx_config(instance: DropletInstance, droplet: Droplet, ip: str, user: User) -> str:
	authHeader = base64.b64encode(b'flowcase_user:' + user.auth_token.encode()).decode('utf-8')
	container_name = f"flowcase_generated_{instance.id}"
	 
	if droplet.droplet_type == "container":
		nginx_config = open(f"config/nginx/container_template.conf", "r").read()
	else: # Guacamole droplet
		nginx_config = open(f"config/nginx/guac_template.conf", "r").read()

	# Use container name instead of IP as IP address of container droplets will change after docker or system restart
	nginx_config = nginx_config.replace("{container_name}", container_name)
	# Keep IP replacement for backward compatibility with guac_template.conf
	nginx_config = nginx_config.replace("{ip}", ip)
	nginx_config = nginx_config.replace("{authHeader}", authHeader)
	nginx_config = nginx_config.replace("{instance_id}", instance.id)

	return nginx_config

def write_nginx_config(instance: DropletInstance, nginx_config: str):
	with open(f"/flowcase/nginx/containers.d/{instance.id}.conf", "w") as f:
		f.write(nginx_config)

def reload_nginx():
	nginx_container = utils.docker.docker_client.containers.get("flowcase-nginx")
	result = nginx_container.exec_run("nginx -s reload")
	if result.exit_code != 0:
		log("WARNING", f"Failed to reload Nginx: {result.output.decode()}")

@droplet_bp.route('/api/droplet/<int:droplet_id>/pull-image', methods=['POST'])
@login_required
def pull_droplet_image(droplet_id):
	"""Manually pull a droplet's Docker image"""
	droplet = Droplet.query.filter_by(id=droplet_id).first()
	if not droplet:
		return jsonify({"success": False, "error": "Droplet not found"}), 404

	if not droplet.container_docker_image:
		return jsonify({"success": False, "error": "Droplet has no Docker image configured"}), 400

	# Check if docker client is available
	if not utils.docker.docker_client:
		log("ERROR", "Docker client not available")
		return jsonify({"success": False, "error": "Docker service is not available"}), 500

	try:
		# Use the existing pull_single_image function
		success, message = utils.docker.pull_single_image(
			droplet.container_docker_registry, 
			droplet.container_docker_image
		)
		
		if success:
			return jsonify({"success": True, "message": message})
		else:
			return jsonify({"success": False, "error": message}), 500
			
	except Exception as e:
		log("ERROR", f"Error pulling image for droplet {droplet_id}: {str(e)}")
		return jsonify({"success": False, "error": f"Failed to pull image: {str(e)}"}), 500

def generate_guac_token(droplet: Droplet, user: User) -> str:
	"""Generate a token for the guacamole instance"""
	guac_token = {
		"connection": {
			"type": droplet.droplet_type,
			"settings": {
				"hostname": droplet.server_ip,
				"username": droplet.server_username,
				"password": droplet.server_password,
				"port": droplet.server_port,
			}
		},
	}
 
	def encrypt_token(token, auth_token):
		iv = os.urandom(16)  # 16 bytes for AES
		auth_token = auth_token[:32]
		cipher = AES.new(auth_token, AES.MODE_CBC, iv)
  
		# Convert value to JSON and pad it
		padded_data = pad(json.dumps(token).encode(), AES.block_size)

		# Encrypt data
		encrypted_data = cipher.encrypt(padded_data)

		# Encode the IV and encrypted data
		data = {
			'iv': base64.b64encode(iv).decode('utf-8'),
			'value': base64.b64encode(encrypted_data).decode('utf-8')
		}

		# Convert the data dictionary to JSON and then encode it
		json_data = json.dumps(data)
		return base64.b64encode(json_data.encode()).decode('utf-8')

	return encrypt_token(guac_token, user.auth_token.encode())
 
@droplet_bp.route('/droplet/<string:instance_id>', methods=['GET'])
@login_required
def droplet(instance_id: str):
	instance = DropletInstance.query.filter_by(id=instance_id).first()
	if not instance:
		return redirect("/")

	# Check if this is the user's own instance
	if instance.user_id == current_user.id:
		pass  # User can access their own instance
	else:
		# Check if user is admin
		user_groups = current_user.get_groups()
		is_admin = False
		for group_id in user_groups:
			group = Group.query.filter_by(id=group_id).first()
			if group and group.display_name == "Admin":
				is_admin = True
				break
		
		# Only admins can access other users' instances
		if not is_admin:
			return redirect("/")

	using_guac = False
	guac_token = None
	droplet = Droplet.query.filter_by(id=instance.droplet_id).first()
	if droplet.droplet_type in ["vnc", "rdp", "ssh"]:
		using_guac = True
		guac_token = generate_guac_token(droplet, current_user)

	return render_template('droplet.html', instance_id=instance_id, droplet=droplet, guacamole=using_guac, guac_token=guac_token)

@droplet_bp.route('/api/instance/<string:instance_id>/destroy', methods=['GET'])
@login_required
def stop_instance(instance_id: str):
	instance = DropletInstance.query.filter_by(id=instance_id).first()
	if not instance:
		return jsonify({"success": False, "error": "Instance not found"}), 404

	# Check if this is the user's own instance
	if instance.user_id == current_user.id:
		pass  # User can stop their own instance
	else:
		# Check if user is admin
		user_groups = current_user.get_groups()
		is_admin = False
		for group_id in user_groups:
			group = Group.query.filter_by(id=group_id).first()
			if group and group.display_name == "Admin":
				is_admin = True
				break
		
		# Only admins can stop other users' instances
		if not is_admin:
			return jsonify({"success": False, "error": "Unauthorized"}), 403

	try:
		if utils.docker.docker_client:
			container = utils.docker.docker_client.containers.get(f"flowcase_generated_{instance.id}")
			container.remove(force=True)
	except Exception as e:
		log("ERROR", f"Error removing container: {str(e)}")
		pass
  
	# Delete nginx config
	if os.path.exists(f"/flowcase/nginx/containers.d/{instance.id}.conf"):
		os.remove(f"/flowcase/nginx/containers.d/{instance.id}.conf")
	
	db.session.delete(instance)
	db.session.commit()
 
	return jsonify({"success": True})