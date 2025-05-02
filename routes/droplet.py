import os
import re
import time
import base64
import json
import docker
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from flask import Blueprint, jsonify, request, render_template, redirect, make_response, send_from_directory
from flask_login import login_required, current_user
import psutil
from __init__ import db, __version__
from models.droplet import Droplet, DropletInstance
from models.user import User
from utils.logger import log
import utils.docker

droplet_bp = Blueprint('droplet', __name__)

@droplet_bp.route('/api/droplets', methods=['GET'])
@login_required
def get_droplets():
	droplets = Droplet.query.all()
	droplets = sorted(droplets, key=lambda x: x.display_name)
 
	response = {
		"success": True,
		"droplets": []
	}
 
	for droplet in droplets:
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
		response["instances"].append({
			"id": instance.id,
			"created_at": instance.created_at,
			"updated_at": instance.updated_at,
			"droplet": {
				"id": droplet.id,
				"display_name": droplet.display_name,
				"description": droplet.description,
				"image_path": droplet.image_path,
				"dorplet_type": droplet.droplet_type,
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

	# Check if droplet is a guacamole droplet
	isGuacDroplet: bool = False
	if droplet.droplet_type in ["vnc", "rdp", "ssh"]:
		isGuacDroplet = True

	# Check if system has enough resources to request this droplet, guacamole droplets do not have resource checks
	if not isGuacDroplet:
		instances = DropletInstance.query.all()
		
		cores = 0
		memory = 0
		for instance in instances:
			cores += Droplet.query.filter_by(id=instance.droplet_id).first().container_cores
			memory += Droplet.query.filter_by(id=instance.droplet_id).first().container_memory
		
		system_cores = os.cpu_count()
		free_memory = psutil.virtual_memory().available / 1024 / 1024
		if cores + droplet.container_cores > system_cores or memory + droplet.container_memory > free_memory:
			log("ERROR", f"Insufficient resources for user {current_user.username} to request droplet {droplet.display_name}")
			return jsonify({"success": False, "error": "Insufficient resources to start this droplet"}), 400
 
	# Check if docker client is available
	if not utils.docker.docker_client:
		log("ERROR", "Docker client not available")
		return jsonify({"success": False, "error": "Docker service is not available"}), 500

	# Check if docker image is downloaded
	images = utils.docker.docker_client.images.list()
	image_exists = False
	for image in images:
		if isGuacDroplet and f"flowcaseweb/flowcase-guac:{__version__}" in image.tags:
			image_exists = True
			break

		if droplet.container_docker_image in image.tags:
			image_exists = True
			break
		
	if not image_exists:
		log("WARNING", f"Docker image {droplet.container_docker_image} not found. Please download the image and try again.")
		return jsonify({"success": False, "error": "Docker image not found. Image might still be downloading."}), 400

	# Create a new instance
	instance = DropletInstance(droplet_id=droplet_id, user_id=current_user.id)
	db.session.add(instance)
	db.session.commit()
 
	# Create a docker container
	log("INFO", f"Creating new instance for user {current_user.username} with droplet {droplet.display_name}")
 
	name = f"flowcase_generated_{instance.id}"
 
	request_resolution = request.json.get('resolution')
	if re.match(r"[0-9]+x[0-9]+", request_resolution):
		resolution = request_resolution
	else:
		resolution = "1280x720"
  
	# Persistant Profile
	if droplet.container_persistent_profile_path and droplet.container_persistent_profile_path != "" and not isGuacDroplet:
		
		profilePath = droplet.container_persistent_profile_path
  
		# Replace variables
		profilePath = profilePath.replace("{user_id}", str(current_user.id))
		profilePath = profilePath.replace("{username}", current_user.username)
		profilePath = profilePath.replace("{droplet_id}", str(droplet_id))
  
		# Ensure path ends with /
		if profilePath[-1] != "/":
			profilePath += "/"

		mount = docker.types.Mount(target="/home/flowcase-user", source=profilePath, type="bind", consistency="[r]private")
  
		# Hack: the first time the mount is created, the container will crash, so we start the container twice
		if not os.path.exists(profilePath + ".bashrc"):
			container = utils.docker.docker_client.containers.run(
				image=droplet.container_docker_image,
				detach=True,
				mem_limit="512000000",
				cpu_shares=int(droplet.container_cores * 1024),
				mounts=[mount],
			)
			time.sleep(1)
			container.stop()
			container.remove(force=True)
	else:
		mount = None
	
	# Create the container
	if not isGuacDroplet:
		container = utils.docker.docker_client.containers.run(
			image=droplet.container_docker_image,
			name=name,
			environment={"DISPLAY": ":1", "VNC_PW": current_user.auth_token, "VNC_RESOLUTION": resolution},
			detach=True,
			network="flowcase_default_network",
			mem_limit=f"{droplet.container_memory}000000",
			cpu_shares=int(droplet.container_cores * 1024),
			mounts=[mount] if mount else None,
		)
	else: # Guacamole droplet
		container = utils.docker.docker_client.containers.run(
			image=f"flowcaseweb/flowcase-guac:{__version__}",
			name=name,
			environment={"GUAC_KEY": current_user.auth_token[:32]},
			detach=True,
			network="flowcase_default_network",
		)
 
	log("INFO", f"Instance created for user {current_user.username} with droplet {droplet.display_name}")
 
	# Wait for container to start
	time.sleep(.25)
 
	# Create nginx config
	container = utils.docker.docker_client.containers.get(f"flowcase_generated_{instance.id}")
	ip = container.attrs['NetworkSettings']['Networks']['flowcase_default_network']['IPAddress']
	
	authHeader = base64.b64encode(b'flowcase_user:' + current_user.auth_token.encode()).decode('utf-8')
 
	if not isGuacDroplet:
		nginx_config = f"""
		location /desktop/{instance.id}/vnc/ {{
			auth_request /droplet_connect;
			auth_request_set $cookie_token $upstream_http_set_cookie;

			proxy_pass https://{ip}:6901/;
	
			proxy_set_header Authorization "Basic {authHeader}";
		}}
	
		location /desktop/{instance.id}/vnc/websockify {{
			auth_request /droplet_connect;
			auth_request_set $cookie_token $upstream_http_set_cookie;

			proxy_pass https://{ip}:6901/websockify/;
			proxy_http_version 1.1;
			proxy_set_header Upgrade $http_upgrade;
			proxy_set_header Connection 'upgrade';
			proxy_set_header Host $host;
			proxy_cache_bypass $http_upgrade;
	
			proxy_read_timeout 86400s;
			proxy_buffering off;
	
			proxy_set_header Authorization "Basic {authHeader}";
		}}
	
		location /desktop/{instance.id}/audio/ {{
			auth_request /droplet_connect;
			auth_request_set $cookie_token $upstream_http_set_cookie;
	
			proxy_pass https://{ip}:4901/;
			proxy_http_version 1.1;
			proxy_set_header Upgrade $http_upgrade;
			proxy_set_header Connection 'upgrade';
			proxy_set_header Host $host;
			proxy_cache_bypass $http_upgrade;
	
			proxy_read_timeout 86400s;
			proxy_buffering off;
	
			proxy_set_header Authorization "Basic {authHeader}";
		}}  
	
		location /desktop/{instance.id}/uploads/ {{
			auth_request /droplet_connect;
			auth_request_set $cookie_token $upstream_http_set_cookie;

			proxy_pass https://{ip}:4902/;
	
			proxy_set_header Authorization "Basic {authHeader}";
		}}
		"""
	
	else: # Guacamole droplet
		nginx_config = f"""
		location /desktop/{instance.id}/vnc/ {{
			auth_request /droplet_connect;
			auth_request_set $cookie_token $upstream_http_set_cookie;

			proxy_pass http://{ip}:8080/;
		}}
  
		location /desktop/{instance.id}/vnc/websockify {{
			auth_request /droplet_connect;
			auth_request_set $cookie_token $upstream_http_set_cookie;

			proxy_pass http://{ip}:8080/websockify/;
			proxy_http_version 1.1;
			proxy_set_header Upgrade $http_upgrade;
			proxy_set_header Connection 'upgrade';
			proxy_set_header Host $host;
			proxy_cache_bypass $http_upgrade;
	
			proxy_read_timeout 86400s;
			proxy_buffering off;
		}}
		"""
 
	# Write nginx config
	with open(f"/flowcase/nginx/containers.d/{instance.id}.conf", "w") as f:
		f.write(nginx_config)
	
	# Send reload signal to Nginx container
	try:
		nginx_container = utils.docker.docker_client.containers.get("flowcase-nginx")
		result = nginx_container.exec_run("nginx -s reload")
		if result.exit_code != 0:
			log("WARNING", f"Failed to reload Nginx: {result.output.decode()}")
		else:
			log("INFO", f"Nginx configuration reloaded successfully for instance {instance.id}")
	except Exception as e:
		log("ERROR", f"Error reloading Nginx configuration: {str(e)}")
 
	return jsonify({"success": True, "instance_id": instance.id})

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

	if instance.user_id != current_user.id:
		return redirect("/")

	using_guac = False
	guac_token = None
	droplet = Droplet.query.filter_by(id=instance.droplet_id).first()
	if droplet.droplet_type in ["vnc", "rdp", "ssh"]:
		using_guac = True
		guac_token = generate_guac_token(Droplet.query.filter_by(id=instance.droplet_id).first(), current_user)

	return render_template('droplet.html', instance_id=instance_id, droplet=droplet, guacamole=using_guac, guac_token=guac_token)

@droplet_bp.route('/data/droplets/images/<string:image_path>', methods=['GET'])
@login_required
def get_image(image_path: str):
	if not os.path.exists(f"data/droplets/images/{image_path}") or image_path == None:
		return redirect("/static/img/droplet_default.jpg")
	return send_from_directory("data/droplets/images", image_path)

@droplet_bp.route('/api/instance/<string:instance_id>/destroy', methods=['GET'])
@login_required
def stop_instance(instance_id: str):
	instance = DropletInstance.query.filter_by(id=instance_id).first()
	if not instance:
		return jsonify({"success": False, "error": "Instance not found"}), 404

	if instance.user_id != current_user.id:
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