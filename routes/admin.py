import platform
import sys
import os
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy.sql import func
from __init__ import db, bcrypt, __version__
from models.user import User, Group
from models.droplet import Droplet, DropletInstance
from models.registry import Registry
from models.log import Log
from utils.permissions import Permissions
import utils.docker
import subprocess

admin_bp = Blueprint('admin', __name__)

def get_container_ip(container, droplet):
	"""Get the IP address of a container, prioritizing the default network for nginx connectivity"""
	networks = container.attrs['NetworkSettings']['Networks']
	
	# First check the default network for nginx connectivity
	if 'flowcase_default_network' in networks and networks['flowcase_default_network']['IPAddress']:
		return networks['flowcase_default_network']['IPAddress']
	
	# If not found, check the droplet's specified network
	if droplet.container_network and droplet.container_network in networks:
		return networks[droplet.container_network]['IPAddress']
	
	# Fall back to other networks
	for network_name in ['default_network', 'bridge']:
		if network_name in networks and networks[network_name]['IPAddress']:
			return networks[network_name]['IPAddress']
	
	return "N/A"

@admin_bp.route('/system_info', methods=['GET'])
@login_required
def api_admin_system():
	if not Permissions.check_permission(current_user.id, Permissions.ADMIN_PANEL):
		return jsonify({"success": False, "error": "Unauthorized"}), 403

	#Get Nginx version
	nginx_version = None
	try:
		#get docker container
		nginx_container = utils.docker.docker_client.containers.get("flowcase-nginx")
		result = nginx_container.exec_run("nginx -v")
		nginx_version = result.output.decode('utf-8').split("\n")[0].replace("nginx version: nginx/", "")
	except:
		nginx_version = "Unable to get version"

	response = {
		"success": True,
		"system": {
			"hostname": os.popen("hostname").read().strip(),
			"os": f"{platform.system()} {platform.release()}"
		},
		"version": {
			"flowcase": __version__,
			"python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
			"docker": utils.docker.get_docker_version(),
			"nginx": nginx_version,
		},
	}
 
	return jsonify(response)

@admin_bp.route('/users', methods=['GET'])
@login_required
def api_admin_users():
	if not Permissions.check_permission(current_user.id, Permissions.VIEW_USERS):
		return jsonify({"success": False, "error": "Unauthorized"}), 403
	
	users = User.query.all()
 
	response = {
		"success": True,
		"users": []
	}
 
	for user in users:
		response["users"].append({
			"id": user.id,
			"username": user.username,
			"created_at": user.created_at,
			"usertype": user.usertype,
			"protected": user.protected,
			"groups": []
		})
		
		user_groups = user.groups.split(",")
		groups = Group.query.all()
		for group in groups:
			if group.id in user_groups:
				response["users"][-1]["groups"].append({
					"id": group.id,
					"display_name": group.display_name
				})
 
	return jsonify(response)

@admin_bp.route('/instances', methods=['GET'])
@login_required
def api_admin_instances():
	if not Permissions.check_permission(current_user.id, Permissions.VIEW_INSTANCES):
		return jsonify({"success": False, "error": "Unauthorized"}), 403

	if not utils.docker.is_docker_available():
		return jsonify({
			"success": False, 
			"error": "Docker service is not available, can't retrieve instances"
		}), 503

	instances = DropletInstance.query.all()
 
	response = {
		"success": True,
		"instances": []
	}
 
	for instance in instances:
		try:
			droplet = Droplet.query.filter_by(id=instance.droplet_id).first()
			user = User.query.filter_by(id=instance.user_id).first()
			container = utils.docker.docker_client.containers.get(f"flowcase_generated_{instance.id}")
			response["instances"].append({
				"id": instance.id,
				"created_at": instance.created_at,
				"updated_at": instance.updated_at,
				"ip": get_container_ip(container, droplet),
				"droplet": {
					"id": droplet.id,
					"display_name": droplet.display_name,
					"description": droplet.description,
					"container_docker_image": droplet.container_docker_image,
					"container_docker_registry": droplet.container_docker_registry,
					"container_cores": droplet.container_cores,
					"container_memory": droplet.container_memory,
					"container_network": droplet.container_network,
					"image_path": droplet.image_path
				},
				"user": {
					"id": user.id,
					"username": user.username
				}
			})
		except Exception as e:
			# Skip this instance if we can't get container info
			continue
 
	return jsonify(response)

@admin_bp.route('/droplets', methods=['GET'])
@login_required
def api_admin_droplets():
	if not Permissions.check_permission(current_user.id, Permissions.VIEW_DROPLETS):
		return jsonify({"success": False, "error": "Unauthorized"}), 403

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
			"container_persistent_profile_path": droplet.container_persistent_profile_path,
			"container_network": droplet.container_network,
			"server_ip": droplet.server_ip,
			"server_port": droplet.server_port,
			"server_username": droplet.server_username,
			"server_password": "********************************" if droplet.server_password else None,
			"restricted_groups": droplet.restricted_groups
		})
 
	return jsonify(response)

@admin_bp.route('/droplet', methods=['POST'])
@login_required
def api_admin_edit_droplet():
	if not Permissions.check_permission(current_user.id, Permissions.EDIT_DROPLETS):
		return jsonify({"success": False, "error": "Unauthorized"}), 403

	droplet_id = request.json.get('id')
	droplet = Droplet.query.filter_by(id=droplet_id).first()
 
	create_new = False
	if not droplet or droplet_id == "null":
		create_new = True
		droplet = Droplet()
  
	# Validate input
	droplet.description = request.json.get('description', None)
	if droplet.description == "":
		droplet.description = None
	droplet.image_path = request.json.get('image_path', None)
	if droplet.image_path == "":
		droplet.image_path = None
		
	# Handle restricted groups
	restricted_groups = request.json.get('restricted_groups', [])
	if restricted_groups:
		droplet.restricted_groups = ','.join(restricted_groups)
	else:
		droplet.restricted_groups = None

	droplet.display_name = request.json.get('display_name')
	if not droplet.display_name:
		return jsonify({"success": False, "error": "Display Name is required"}), 400

	droplet.droplet_type = request.json.get('droplet_type')
	if not droplet.droplet_type:
		return jsonify({"success": False, "error": "Droplet Type is required"}), 400
 
	if droplet.droplet_type == "container":
		droplet.container_docker_registry = request.json.get('container_docker_registry')
		if not droplet.container_docker_registry:
			return jsonify({"success": False, "error": "Docker Registry is required"}), 400

		droplet.container_docker_image = request.json.get('container_docker_image')
		if not droplet.container_docker_image:
			return jsonify({"success": False, "error": "Docker Image is required"}), 400
	
		# Ensure cores and memory are integers
		if not request.json.get('container_cores'):
			return jsonify({"success": False, "error": "Cores is required"}), 400
		if not request.json.get('container_memory'):
			return jsonify({"success": False, "error": "Memory is required"}), 400

		try:
			droplet.container_cores = float(request.json.get('container_cores'))
		except:
			return jsonify({"success": False, "error": "Cores must be a number"}), 400
		try:
			droplet.container_memory = float(request.json.get('container_memory'))
		except:
			return jsonify({"success": False, "error": "Memory must be a number"}), 400

		# Check if cores or memory are negative
		if droplet.container_cores < 0:
			return jsonify({"success": False, "error": "Cores cannot be negative"}), 400
		if droplet.container_memory < 0:
			return jsonify({"success": False, "error": "Memory cannot be negative"}), 400

		droplet.container_persistent_profile_path = request.json.get('container_persistent_profile_path')
		if not droplet.container_persistent_profile_path:
			droplet.container_persistent_profile_path = None
			
		droplet.container_network = request.json.get('container_network')
		if not droplet.container_network:
			droplet.container_network = None
  
	elif droplet.droplet_type == "vnc" or droplet.droplet_type == "rdp" or droplet.droplet_type == "ssh":
		droplet.server_ip = request.json.get('server_ip')
		if not droplet.server_ip:
			return jsonify({"success": False, "error": "Server IP is required"}), 400

		droplet.server_port = request.json.get('server_port')
		if not droplet.server_port:
			return jsonify({"success": False, "error": "Server Port is required"}), 400
  
		droplet.server_username = request.json.get('server_username', None)
		if droplet.server_username == "":
			droplet.server_username = None
   
		new_server_password = request.json.get('server_password', None)
		if new_server_password != "********************************":
			droplet.server_password = new_server_password
  
		droplet.container_cores = 1
		droplet.container_memory = 1024
  
	if create_new:
		db.session.add(droplet)
 
	db.session.commit()
 
	return jsonify({
		"success": True,
		"droplet_id": droplet.id
	})

@admin_bp.route('/droplet', methods=['DELETE'])
@login_required
def api_admin_delete_droplet():
	if not Permissions.check_permission(current_user.id, Permissions.EDIT_DROPLETS):
		return jsonify({"success": False, "error": "Unauthorized"}), 403
	
	droplet_id = request.json.get('id')
	droplet = Droplet.query.filter_by(id=droplet_id).first()
	if not droplet:
		return jsonify({"success": False, "error": "Droplet not found"}), 404
 
	db.session.delete(droplet)
	db.session.commit()
 
	# Delete any instances of this droplet
	instances = DropletInstance.query.filter_by(droplet_id=droplet_id).all()
	
	if utils.docker.is_docker_available():
		for instance in instances:
			try:
				container = utils.docker.docker_client.containers.get(f"flowcase_generated_{instance.id}")
				container.remove(force=True)
			except Exception as e:
				pass  # Container might not exist
			db.session.delete(instance)
			db.session.commit()
	else:
		# Even if Docker is not available, we should still delete the DB records
		for instance in instances:
			db.session.delete(instance)
		db.session.commit()
 
	return jsonify({"success": True})

@admin_bp.route('/instance', methods=['DELETE'])
@login_required
def api_admin_delete_instance():
	if not Permissions.check_permission(current_user.id, Permissions.EDIT_INSTANCES):
		return jsonify({"success": False, "error": "Unauthorized"}), 403

	instance_id = request.json.get('id')
	instance = DropletInstance.query.filter_by(id=instance_id).first()
	if not instance:
		return jsonify({"success": False, "error": "Instance not found"}), 404
 
	if utils.docker.is_docker_available():
		try:
			container = utils.docker.docker_client.containers.get(f"flowcase_generated_{instance.id}")
			container.remove(force=True)
		except Exception as e:
			pass  # Container might not exist
	
	db.session.delete(instance)
	db.session.commit()
 
	return jsonify({"success": True})

@admin_bp.route('/user', methods=['POST'])
@login_required
def api_admin_edit_user():
	if not Permissions.check_permission(current_user.id, Permissions.EDIT_USERS):
		return jsonify({"success": False, "error": "Unauthorized"}), 403

	user_id = request.json.get('id')
	user = User.query.filter_by(id=user_id).first()
 
	create_new = False
	if not user or user_id == "null":
		create_new = True
		user = User()
  
	# Validate input
	username = request.json.get('username')
	if not username:
		return jsonify({"success": False, "error": "Username is required"}), 400
	if " " in username:
		return jsonify({"success": False, "error": "Username cannot contain spaces"}), 400
	
	# Convert username to lowercase for case-insensitive handling
	user.username = username.lower()

	# Special handling for protected users
	if not create_new and user.protected:
		# Protected user's username cannot be changed
		error_msg = "Cannot change username of protected user"
		return jsonify({"success": False, "error": error_msg}), 400
		
		# Get requested groups
		requested_groups = request.json.get('groups', [])
		
		# Special handling for admin user - ensure they remain in Admin group
		if user.username == "admin":
			admin_group = Group.query.filter_by(display_name="Admin").first()
			if admin_group and admin_group.id not in requested_groups:
				# Add admin group back if it was removed
				requested_groups.append(admin_group.id)
	else:
		# For non-protected users, just use the requested groups
		requested_groups = request.json.get('groups', [])
	
	# Build groups string
	groups_string = ""
	for group in requested_groups:
		groups_string += f'{group},'
	user.groups = groups_string[:-1] if groups_string else ""
	
	if not user.groups or user.groups == "" or user.groups == "]":
		return jsonify({"success": False, "error": "Groups are required"}), 400

	# Passwords can only be set, not changed
	if create_new:
		if not request.json.get('password'):
			return jsonify({"success": False, "error": "Password is required"}), 400
		from routes.auth import generate_auth_token
		user.password = bcrypt.generate_password_hash(request.json.get('password')).decode('utf-8')
		user.auth_token = generate_auth_token()
 
	if create_new:
		db.session.add(user)
 
	db.session.commit()
 
	return jsonify({"success": True})

@admin_bp.route('/user', methods=['DELETE'])
@login_required
def api_admin_delete_user():
	if not Permissions.check_permission(current_user.id, Permissions.EDIT_USERS):
		return jsonify({"success": False, "error": "Unauthorized"}), 403

	user_id = request.json.get('id')
	user = User.query.filter_by(id=user_id).first()
	if not user:
		return jsonify({"success": False, "error": "User not found"}), 404
	
	if user.protected:
		return jsonify({"success": False, "error": "This user is protected. Protected users cannot be deleted."}), 400
	
	db.session.delete(user)
	db.session.commit()
 
	# Delete any instances of this user
	instances = DropletInstance.query.filter_by(user_id=user_id).all()
	
	if utils.docker.is_docker_available():
		for instance in instances:
			try:
				container = utils.docker.docker_client.containers.get(f"flowcase_generated_{instance.id}")
				container.remove(force=True)
			except Exception as e:
				pass  # Container might not exist
			db.session.delete(instance)
			db.session.commit()
	else:
		# Even if Docker is not available, we should still delete the DB records
		for instance in instances:
			db.session.delete(instance)
		db.session.commit()
 
	return jsonify({"success": True})

@admin_bp.route('/groups', methods=['GET'])
@login_required
def api_admin_groups():
	if not Permissions.check_permission(current_user.id, Permissions.VIEW_GROUPS):
		return jsonify({"success": False, "error": "Unauthorized"}), 403

	groups = Group.query.all()
 
	response = {
		"success": True,
		"groups": []
	}
 
	for group in groups:
		response["groups"].append({
			"id": group.id,
			"display_name": group.display_name,
			"protected": group.protected,
			"permissions": {
				"admin_panel": group.perm_admin_panel,
				"view_instances": group.perm_view_instances,
				"edit_instances": group.perm_edit_instances,
				"view_users": group.perm_view_users,
				"edit_users": group.perm_edit_users,
				"view_droplets": group.perm_view_droplets,
				"edit_droplets": group.perm_edit_droplets,
				"view_registry": group.perm_view_registry,
				"edit_registry": group.perm_edit_registry,
				"view_groups": group.perm_view_groups,
				"edit_groups": group.perm_edit_groups
			}
		})
 
	return jsonify(response)

@admin_bp.route('/group', methods=['POST'])
@login_required
def api_admin_edit_group():
	if not Permissions.check_permission(current_user.id, Permissions.EDIT_GROUPS):
		return jsonify({"success": False, "error": "Unauthorized"}), 403

	group_id = request.json.get('id')
	group = Group.query.filter_by(id=group_id).first()
 
	create_new = False
	if not group or group_id == "null":
		create_new = True
		group = Group()
		group.protected = False
	
	# Validate input
	new_display_name = request.json.get('display_name')
	if not new_display_name:
		return jsonify({"success": False, "error": "Display Name is required"}), 400
	
	# Check if this is a protected group and the display name is being changed
	if not create_new and group.protected and group.display_name != new_display_name:
		return jsonify({"success": False, "error": "Cannot change display name of protected group"}), 400
		
	group.display_name = new_display_name
 
	group.perm_admin_panel = request.json.get('perm_admin_panel')
	if not group.perm_admin_panel:
		group.perm_admin_panel = False
 
	group.perm_view_instances = request.json.get('perm_view_instances')
	if not group.perm_view_instances:
		group.perm_view_instances = False
 
	group.perm_edit_instances = request.json.get('perm_edit_instances')
	if not group.perm_edit_instances:
		group.perm_edit_instances = False
 
	group.perm_view_users = request.json.get('perm_view_users')
	if not group.perm_view_users:
		group.perm_view_users = False
 
	group.perm_edit_users = request.json.get('perm_edit_users')
	if not group.perm_edit_users:
		group.perm_edit_users = False
 
	group.perm_view_droplets = request.json.get('perm_view_droplets')
	if not group.perm_view_droplets:
		group.perm_view_droplets = False
 
	group.perm_edit_droplets = request.json.get('perm_edit_droplets')
	if not group.perm_edit_droplets:
		group.perm_edit_droplets = False
  
	group.perm_view_registry = request.json.get('perm_view_registry')
	if not group.perm_view_registry:
		group.perm_view_registry = False
  
	group.perm_edit_registry = request.json.get('perm_edit_registry')
	if not group.perm_edit_registry:
		group.perm_edit_registry = False
 
	group.perm_view_groups = request.json.get('perm_view_groups')
	if not group.perm_view_groups:
		group.perm_view_groups = False
 
	group.perm_edit_groups = request.json.get('perm_edit_groups')
	if not group.perm_edit_groups:
		group.perm_edit_groups = False
 
	if create_new:
		db.session.add(group)
 
	db.session.commit()
 
	return jsonify({"success": True})

@admin_bp.route('/group', methods=['DELETE'])
@login_required
def api_admin_delete_group():
	if not Permissions.check_permission(current_user.id, Permissions.EDIT_GROUPS):
		return jsonify({"success": False, "error": "Unauthorized"}), 403

	group_id = request.json.get('id')
	group = Group.query.filter_by(id=group_id).first()
	if not group:
		return jsonify({"success": False, "error": "Group not found."}), 404
 
	if group.protected:
		return jsonify({"success": False, "error": "This group is protected. Protected groups cannot be deleted."}), 400
 
	db.session.delete(group)
	db.session.commit()
 
	return jsonify({"success": True})

@admin_bp.route('/registry')
@login_required
def api_admin_registry():
	if not Permissions.check_permission(current_user.id, Permissions.VIEW_REGISTRY):
		return jsonify({"success": False, "error": "Unauthorized"}), 403

	import os
	registry_lock = os.environ.get('FLOWCASE_REGISTRY_LOCK')

	response = {
		"success": True,
		"flowcase_version": __version__,
		"registry": [],
		"registry_locked": bool(registry_lock)
	}

	if registry_lock:
		# Return the locked registry from environment variable
		try:
			import requests
			info = requests.get(f"{registry_lock}/info.json").json()
			droplets = requests.get(f"{registry_lock}/droplets.json").json()
		except:
			info = {
				"name": "Failed to get info",
			}
			droplets = []
			from utils.logger import log
			log("ERROR", f"Failed to get registry info from {registry_lock}")
		response["registry"].append({
			"id": "locked",
			"url": registry_lock,
			"info": info,
			"droplets": droplets
		})
	else:
		# Return registries from database
		registry = Registry.query.all()
		for r in registry:
			# Get info
			try:
				import requests
				info = requests.get(f"{r.url}/info.json").json()
				droplets = requests.get(f"{r.url}/droplets.json").json()
			except:
				info = {
					"name": "Failed to get info",
				}
				droplets = []
				from utils.logger import log
				log("ERROR", f"Failed to get registry info from {r.url}")

			response["registry"].append({
				"id": r.id,
				"url": r.url,
				"info": info,
				"droplets": droplets
			})

	return jsonify(response)

@admin_bp.route('/registry', methods=['POST', 'DELETE'])
@login_required
def api_admin_edit_registry():
	import os
	registry_lock = os.environ.get('FLOWCASE_REGISTRY_LOCK')
	
	# Block all registry editing when locked
	if registry_lock:
		return jsonify({"success": False, "error": "Registry is locked and cannot be modified"}), 403
	
	if request.method == 'POST':
		if not Permissions.check_permission(current_user.id, Permissions.EDIT_REGISTRY):
			return jsonify({"success": False, "error": "Unauthorized"}), 403

		url = request.json.get('url')
		if not url:
			return jsonify({"success": False, "error": "URL is required"}), 400

		# Check if registry already exists
		registry = Registry.query.filter_by(url=url).first()
		if registry:
			return jsonify({"success": False, "error": "Registry with this URL already exists"}), 400
	
		registry = Registry(url=url)
		db.session.add(registry)
		db.session.commit()
	
		return jsonify({"success": True})

	elif request.method == 'DELETE':
		if not Permissions.check_permission(current_user.id, Permissions.EDIT_REGISTRY):
			return jsonify({"success": False, "error": "Unauthorized"}), 403

		registry_id = request.json.get('id')
		registry = Registry.query.filter_by(id=registry_id).first()
		if not registry:
			return jsonify({"success": False, "error": "Registry not found"}), 404
	
		db.session.delete(registry)
		db.session.commit()
 
		return jsonify({"success": True})

@admin_bp.route('/logs', methods=['GET'])
@login_required
def api_admin_logs():
	if not current_user.has_permission(Permissions.ADMIN_PANEL):
		return jsonify({"success": False, "error": "You do not have permission to view logs"})
	
	page = request.args.get('page', 1, type=int)
	per_page = request.args.get('per_page', 50, type=int)
	log_type = request.args.get('type', None)
	
	query = Log.query
	
	if log_type and log_type.upper() in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
		query = query.filter(Log.level == log_type.upper())
	
	logs_pagination = query.order_by(Log.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
	logs = logs_pagination.items
	
	return jsonify({
		"success": True,
		"logs": [
			{
				"id": log.id,
				"created_at": log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
				"level": log.level,
				"message": log.message
			} for log in logs
		],
		"pagination": {
			"page": page,
			"per_page": per_page,
			"total": logs_pagination.total,
			"pages": logs_pagination.pages
		}
	}) 

@admin_bp.route('/images/status', methods=['GET'])
@login_required
def api_admin_images_status():
	"""Get the download status of all droplet images"""
	if not Permissions.check_permission(current_user.id, Permissions.VIEW_DROPLETS):
		return jsonify({"success": False, "error": "Unauthorized"}), 403

	if not utils.docker.is_docker_available():
		return jsonify({
			"success": False, 
			"error": "Docker service is not available"
		}), 503

	status = utils.docker.get_images_status()
	
	return jsonify({
		"success": True,
		"images": status
	})

@admin_bp.route('/images/pull', methods=['POST'])
@login_required
def api_admin_pull_image():
	"""Pull a specific droplet image"""
	if not Permissions.check_permission(current_user.id, Permissions.EDIT_DROPLETS):
		return jsonify({"success": False, "error": "Unauthorized"}), 403

	if not utils.docker.is_docker_available():
		return jsonify({
			"success": False, 
			"error": "Docker service is not available"
		}), 503

	droplet_id = request.json.get('droplet_id')
	registry = request.json.get('registry')
	image = request.json.get('image')
	
	# Handle auto-download case where registry and image are provided directly
	if registry and image:
		success, message = utils.docker.pull_single_image(registry, image)
		if success:
			return jsonify({
				"success": True,
				"message": message
			})
		else:
			return jsonify({
				"success": False,
				"error": message
			}), 500
	
	# Handle droplet_id case (existing functionality)
	if not droplet_id:
		return jsonify({"success": False, "error": "Droplet ID is required"}), 400

	# Handle special guac droplet
	if droplet_id == "guac":
		from __init__ import __version__
		registry = "https://index.docker.io/v1/"
		image_name = f"flowcaseweb/flowcase-guac:{__version__}"
	else:
		# Get droplet info
		droplet = Droplet.query.filter_by(id=droplet_id).first()
		if not droplet:
			return jsonify({"success": False, "error": "Droplet not found"}), 404

		if not droplet.container_docker_image:
			return jsonify({"success": False, "error": "Droplet has no Docker image configured"}), 400

		registry = droplet.container_docker_registry
		image_name = droplet.container_docker_image

	# Pull the image
	success, message = utils.docker.pull_single_image(registry, image_name)
	
	if success:
		return jsonify({
			"success": True,
			"message": message
		})
	else:
		return jsonify({
			"success": False,
			"error": message
		}), 500

@admin_bp.route('/images/pull-all', methods=['POST'])
@login_required
def api_admin_pull_all_images():
	"""Pull all droplet images"""
	if not Permissions.check_permission(current_user.id, Permissions.EDIT_DROPLETS):
		return jsonify({"success": False, "error": "Unauthorized"}), 403

	if not utils.docker.is_docker_available():
		return jsonify({
			"success": False, 
			"error": "Docker service is not available"
		}), 503

	try:
		# Use existing pull_images function
		utils.docker.pull_images()
		
		return jsonify({
			"success": True,
			"message": "Started downloading all images. Check logs for progress."
		})
	except Exception as e:
		return jsonify({
			"success": False,
			"error": f"Failed to start image downloads: {str(e)}"
		}), 500 

@admin_bp.route('/images/logs', methods=['GET'])
@login_required
def api_admin_image_logs():
	"""Get recent image download logs and errors"""
	if not Permissions.check_permission(current_user.id, Permissions.VIEW_DROPLETS):
		return jsonify({"success": False, "error": "Unauthorized"}), 403

	try:
		page = request.args.get('page', 1, type=int)
		per_page = request.args.get('per_page', 50, type=int)
		log_type = request.args.get('type', None)
		
		# Build query for logs related to Docker image operations
		query = Log.query.filter(Log.message.like('%Docker image%'))
		
		# Apply log level filter if specified
		if log_type and log_type.upper() in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
			query = query.filter(Log.level == log_type.upper())
		
		# Get paginated results
		logs_pagination = query.order_by(Log.created_at.desc()).paginate(
			page=page, per_page=per_page, error_out=False
		)
		logs = logs_pagination.items
		
		# Format logs for response
		formatted_logs = []
		for log in logs:
			formatted_logs.append({
				"id": log.id,
				"created_at": log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
				"level": log.level,
				"message": log.message
			})
		
		return jsonify({
			"success": True,
			"logs": formatted_logs,
			"pagination": {
				"page": page,
				"per_page": per_page,
				"total": logs_pagination.total,
				"pages": logs_pagination.pages
			}
		})
		
	except Exception as e:
		return jsonify({
			"success": False,
			"error": f"Failed to fetch image logs: {str(e)}"
		}), 500

@admin_bp.route('/networks', methods=['GET'])
def api_admin_networks():
	"""Get list of available Docker networks"""
	if not Permissions.check_permission(current_user.id, Permissions.VIEW_DROPLETS):
		return jsonify({"success": False, "error": "Unauthorized"}), 403

	if not utils.docker.is_docker_available():
		return jsonify({
			"success": False,
			"error": "Docker service is not available"
		}), 503
	
	try:
		all_networks = utils.docker.list_available_networks()
		
		# Filter networks: only include default network and networks starting with lan_ or vlan_
		filtered_networks = []
		for network in all_networks:
			network_name = network["name"]
			if (network_name == "flowcase_default_network" or
				network_name.startswith("lan_") or
				network_name.startswith("vlan_")):
				filtered_networks.append(network)
		
		return jsonify({
			"success": True,
			"networks": filtered_networks
		})
	except Exception as e:
		log("ERROR", f"Error listing networks: {str(e)}")
		return jsonify({"success": False, "error": str(e)}), 500
