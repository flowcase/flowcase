import argparse
import base64
import os
import platform
import random
import re
import string
import sys
import time
import uuid
from werkzeug.middleware.proxy_fix import ProxyFix
from flask import Flask, Request, render_template, make_response, jsonify, request, redirect, url_for, abort, send_from_directory, Response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
from flask_migrate import Migrate
import docker
import psutil
import threading

__version__ = "develop"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.getcwd(), 'data', 'flowcase.db')
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = '/'

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=5000)
parser.add_argument('--debug', action='store_true')
parser.add_argument('--ignore-docker', action='store_true')

args, _ = parser.parse_known_args()

class User(UserMixin, db.Model):
	id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
	username = db.Column(db.String(80), unique=True, nullable=False)
	password = db.Column(db.String(80), nullable=False)
	created_at = db.Column(db.DateTime, server_default=func.now())
	groups = db.Column(db.String(255), nullable=False)
 
	def has_permission(self, permission):
		return Permissions.check_permission(self.id, permission)
 
class Group(db.Model):
	id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
	display_name = db.Column(db.String(80), nullable=False)
	created_at = db.Column(db.DateTime, server_default=func.now())
	protected = db.Column(db.Boolean, nullable=False) #Protected groups cannot be deleted
	perm_admin_panel = db.Column(db.Boolean, nullable=False)
	perm_view_instances = db.Column(db.Boolean, nullable=False)
	perm_edit_instances = db.Column(db.Boolean, nullable=False)
	perm_view_users = db.Column(db.Boolean, nullable=False)
	perm_edit_users = db.Column(db.Boolean, nullable=False)
	perm_view_droplets = db.Column(db.Boolean, nullable=False)
	perm_edit_droplets = db.Column(db.Boolean, nullable=False)
	perm_view_groups = db.Column(db.Boolean, nullable=False)
	perm_edit_groups = db.Column(db.Boolean, nullable=False)
 
class Droplet(db.Model):
	id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
	display_name = db.Column(db.String(80), nullable=False)
	description = db.Column(db.String(255), nullable=True)
	image_path = db.Column(db.String(255), nullable=True)
	droplet_type = db.Column(db.String(80), nullable=False)
	container_docker_image = db.Column(db.String(255), nullable=True)
	container_docker_registry = db.Column(db.String(255), nullable=True)
	container_cores = db.Column(db.Integer, nullable=True)
	container_memory = db.Column(db.Integer, nullable=True)
	server_ip = db.Column(db.String(255), nullable=True)
	server_port = db.Column(db.Integer, nullable=True)
	server_username = db.Column(db.String(255), nullable=True)
	server_password = db.Column(db.String(255), nullable=True)
 
class DropletInstance(db.Model):
	id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
	droplet_id = db.Column(db.String(36), db.ForeignKey('droplet.id'), nullable=False)
	user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
	created_at = db.Column(db.DateTime, server_default=func.now())
	updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())
 
class Log(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	created_at = db.Column(db.DateTime, server_default=func.now())
	level = db.Column(db.String(8), nullable=False) #DEBUG, INFO, WARNING, ERROR
	message = db.Column(db.String(1024), nullable=False)

def log(level: str, message: str):
	log = Log(level=level, message=message)
	db.session.add(log)
	db.session.commit()
	time = log.created_at.strftime('%Y-%m-%d %H:%M:%S')
	if level != "DEBUG" or args.debug:
		print(f"[{level}] | {time} | {message}")

@login_manager.user_loader
def load_user(user_id):
	return User.query.get(user_id)

@app.route('/')
def index():
	if current_user.is_authenticated:
		return redirect(url_for('dashboard'))
	return render_template('login.html')

@app.errorhandler(404)
def page_not_found(e):
	return render_template('404.html'), 404

@app.route('/dashboard')
@login_required
def dashboard():
	return render_template('dashboard.html')

@app.route('/api/get_system_status', methods=['GET'])
@login_required
def get_system_status():
	status = {
		"success": True,
		"storage": {
			"total": "{:.1f}".format(psutil.disk_usage('/').total / 1024 / 1024 / 1024),
			"used": "{:.1f}".format(psutil.disk_usage('/').used / 1024 / 1024 / 1024),
		},
		"memory": {
			"total": "{:.1f}".format(psutil.virtual_memory().total / 1024 / 1024 / 1024),
			"used": "{:.1f}".format(psutil.virtual_memory().used / 1024 / 1024 / 1024),
		}
	}
	return jsonify(status)

@app.route('/data/droplets/images/<string:image_path>', methods=['GET'])
@login_required
def get_image(image_path: str):
	if not os.path.exists(f"data/droplets/images/{image_path}") or image_path == None:
		return redirect("/static/img/droplet_default.jpg")
	return send_from_directory("data/droplets/images", image_path)

@app.route('/login', methods=['POST'])
def login():
	username = request.form['username']
	password = request.form['password']
	user = User.query.filter_by(username=username).first()
	if user and bcrypt.check_password_hash(user.password, password):
		login_user(user)
		return redirect(url_for('dashboard'))
	else:
		return redirect("/")

@app.route('/logout')
@login_required
def logout():
	logout_user()
	return redirect("/")

def create_user(username, password, groups):
	user = User(username=username, password=bcrypt.generate_password_hash(password).decode('utf-8'), groups=groups)
	db.session.add(user)
	db.session.commit()
 
def first_run():
	os.makedirs("data", exist_ok=True)
	os.makedirs("data/droplets/images", exist_ok=True)
	os.makedirs("data/user/avatar", exist_ok=True)
 
	#check if .firstrun file exists
	if os.path.exists("data/.firstrun"):
		return

	print("Running first time setup...")
  
	#Create Flask secret key, if not already created
	if not os.path.exists("data/secret_key"):
		print("Creating secret key...")
		with open("data/secret_key", "w") as f:
			f.write(''.join(random.choice(string.ascii_letters + string.digits) for i in range(64)))
   
	#Create Default Droplets
	if Droplet.query.count() == 0:
		print("Creating default droplets...")
		default_droplets = [
			{
				"display_name": "Ubuntu 20.04 Base",
				"description": "Ubuntu is a Linux distribution derived from Debian and composed mostly of free and open-source software.",
				"container_docker_image": "flowcaseweb/core-ubuntu-focal:" + __version__,
				"container_docker_registry": "https://index.docker.io/v1/",
				"container_cores": 2,
				"container_memory": 2768,
				"image_path": "https://flowcase.org/static/img/ubuntu.png"
			},
			{
				"display_name": "Doom",
				"description": "Doom is a first-person shooter video game developed by id Software.",
				"container_docker_image": "flowcaseweb/doom:" + __version__,
				"container_docker_registry": "https://index.docker.io/v1/",
				"container_cores": 2,
				"container_memory": 2768,
				"image_path": "https://flowcase.org/static/img/doom.png"
			},
		]
		for droplet in default_droplets:
			new_droplet = Droplet(
				display_name=droplet["display_name"],
				description=droplet["description"],
				droplet_type="container",
				container_docker_image=droplet["container_docker_image"],
				container_docker_registry=droplet["container_docker_registry"],
				container_cores=droplet["container_cores"],
				container_memory=droplet["container_memory"],
				image_path=droplet["image_path"]
			)
			db.session.add(new_droplet)
		db.session.commit()
  
	#create .firstrun file
	with open("data/.firstrun", "w") as f:
		f.write("")
  
def startup():
	log("INFO", "Initializing Flowcase...")

	#Delete all droplet instances
	DropletInstance.query.delete()
	db.session.commit()
 
	#Set secret key
	with open("data/secret_key", "r") as f:
		app.secret_key = f.read()
  
	CreateDefaultGroups()
	
	#create default Admin and User accounts
	if User.query.count() == 0:
		admin_groups = f"[\"{Group.query.filter_by(display_name='Admin').first().id}\",\"{Group.query.filter_by(display_name='User').first().id}\"]"
		user_groups = f"[\"{Group.query.filter_by(display_name='User').first().id}\"]"
		admin_random_password = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(16))
		create_user("admin", admin_random_password, admin_groups)
		user_random_password = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(16))
		create_user("user", user_random_password, user_groups)

		print("Created default users:")
		print(f"Username: admin, Password: {admin_random_password}")
		print(f"Username: user, Password: {user_random_password}")

	try:
		docker_client = docker.from_env()
		docker_client.containers.list()
	except Exception as e:
		log("ERROR", "Docker is not running. Please start Docker and try again.")
		exit(1)
  
	#delete any existing containers
	docker_client = docker.from_env()
	containers = docker_client.containers.list(all=True)
	for container in containers:
		regex = re.compile(r"flowcase_generated_([a-z0-9]+(-[a-z0-9]+)+)", re.IGNORECASE)
		if regex.match(container.name):
			log("INFO", f"Stopping container {container.name}")
			container.stop()
			container.remove()
	
	log("INFO", "Flowcase initialized.")
 
def CreateDefaultGroups():
	if Group.query.count() == 0:
		admin_group = Group(
			display_name="Admin",
			protected=True,
			perm_admin_panel=True,
			perm_view_instances=True,
			perm_edit_instances=True,
			perm_view_users=True,
			perm_edit_users=True,
			perm_view_droplets=True,
			perm_edit_droplets=True,
			perm_view_groups=True,
			perm_edit_groups=True
		)
		db.session.add(admin_group)
		user_group = Group(
			display_name="User",
			protected=True,
			perm_admin_panel=False,
			perm_view_instances=False,
			perm_edit_instances=False,
			perm_view_users=False,
			perm_edit_users=False,
			perm_view_droplets=False,
			perm_edit_droplets=False,
			perm_view_groups=False,
			perm_edit_groups=False
		)
		db.session.add(user_group)
		db.session.commit()
  
#permisions
class Permissions:
	ADMIN_PANEL = "perm_admin_panel"
	VIEW_INSTANCES = "perm_view_instances"
	EDIT_INSTANCES = "perm_edit_instances"
	VIEW_USERS = "perm_view_users"
	EDIT_USERS = "perm_edit_users"
	VIEW_DROPLETS = "perm_view_droplets"
	EDIT_DROPLETS = "perm_edit_droplets"
	VIEW_GROUPS = "perm_view_groups"
	EDIT_GROUPS = "perm_edit_groups"

	def check_permission(userid, permission):
		#go through all groups and check if the user has the permission
		user = User.query.filter_by(id=userid).first()
		groups = user.groups.replace("[", "").replace("]", "").replace("\"", "").split(",")

		for group in groups:
			group = Group.query.filter_by(id=group).first()
   
			if not group: #group not found, most likely deleted
				continue

			if getattr(group, permission):
				return True
		return False
 
@app.route('/api/admin/system_info', methods=['GET'])
@login_required
def api_admin_system():
	if not Permissions.check_permission(current_user.id, Permissions.ADMIN_PANEL):
		return jsonify({"success": False, "error": "Unauthorized"}), 403

	Response = {
		"success": True,
		"system": {
			"hostname": os.popen("hostname").read().strip(),
			"os": f"{platform.system()} {platform.release()}"
		},
		"version": {
			"flowcase": __version__,
			"python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
			"docker": docker.from_env().version()["Version"],
			"nginx": os.popen("nginx -v 2>&1").read().split("\n")[0].replace("nginx version: nginx/", ""),
		},
	}
 
	return jsonify(Response)

@app.route('/api/admin/users', methods=['GET'])
@login_required
def api_admin_users():
	if not Permissions.check_permission(current_user.id, Permissions.VIEW_USERS):
		return jsonify({"success": False, "error": "Unauthorized"}), 403
    
	users = User.query.all()
 
	Response = {
		"success": True,
		"users": []
	}
 
	for user in users:
		Response["users"].append({
			"id": user.id,
			"username": user.username,
			"created_at": user.created_at,
			"groups": []
		})
		
		user_groups = user.groups.replace("[", "").replace("]", "").replace("\"", "").split(",")
		groups = Group.query.all()
		for group in groups:
			if group.id in user_groups:
				Response["users"][-1]["groups"].append({
					"id": group.id,
					"display_name": group.display_name
				})
 
	return jsonify(Response)

@app.route('/api/admin/instances', methods=['GET'])
@login_required
def api_admin_instances():
	if not Permissions.check_permission(current_user.id, Permissions.VIEW_INSTANCES):
		return jsonify({"success": False, "error": "Unauthorized"}), 403

	instances = DropletInstance.query.all()
 
	Response = {
		"success": True,
		"instances": []
	}
 
	for instance in instances:
		droplet = Droplet.query.filter_by(id=instance.droplet_id).first()
		user = User.query.filter_by(id=instance.user_id).first()
		docker_client = docker.from_env()
		container = docker_client.containers.get(f"flowcase_generated_{instance.id}")
		Response["instances"].append({
			"id": instance.id,
			"created_at": instance.created_at,
			"updated_at": instance.updated_at,
			"ip": container.attrs['NetworkSettings']['Networks']['flowcase_default_network']['IPAddress'],
			"droplet": {
				"id": droplet.id,
				"display_name": droplet.display_name,
				"description": droplet.description,
				"container_docker_image": droplet.container_docker_image,
				"container_docker_registry": droplet.container_docker_registry,
				"container_cores": droplet.container_cores,
				"container_memory": droplet.container_memory,
				"image_path": droplet.image_path
			},
			"user": {
				"id": user.id,
				"username": user.username
			}
		})
 
	return jsonify(Response)

@app.route('/api/admin/droplets', methods=['GET'])
@login_required
def api_admin_droplets():
	if not Permissions.check_permission(current_user.id, Permissions.VIEW_DROPLETS):
		return jsonify({"success": False, "error": "Unauthorized"}), 403

	droplets = Droplet.query.all()
	droplets = sorted(droplets, key=lambda x: x.display_name)
 
	Response = {
		"success": True,
		"droplets": []
	}
 
	for droplet in droplets:
		Response["droplets"].append({
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
			"server_username": droplet.server_username,
			"server_password": droplet.server_password
		})
 
	return jsonify(Response)

@app.route('/api/admin/edit_droplet', methods=['POST'])
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
  
	#validate input
	droplet.description = request.json.get('description', None)
	if droplet.description == "":
		droplet.description = None
	droplet.image_path = request.json.get('image_path', None)
	if droplet.image_path == "":
		droplet.image_path = None

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
	
		#ensure cores and memory are integers
		if not request.json.get('container_cores'):
			return jsonify({"success": False, "error": "Cores is required"}), 400
		if not request.json.get('container_memory'):
			return jsonify({"success": False, "error": "Memory is required"}), 400

		try:
			droplet.container_cores = int(request.json.get('container_cores'))
		except:
			return jsonify({"success": False, "error": "Cores must be an integer"}), 400
		try:
			droplet.container_memory = int(request.json.get('container_memory'))
		except:
			return jsonify({"success": False, "error": "Memory must be an integer"}), 400
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
		droplet.server_password = request.json.get('server_password', None)
		if droplet.server_password == "":
			droplet.server_password = None
  
		droplet.container_cores = 1
		droplet.container_memory = 1024
  
	
	if create_new:
		db.session.add(droplet)
 
	db.session.commit()
 
	return jsonify({"success": True})

@app.route('/api/admin/delete_droplet', methods=['POST'])
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
 
	#delete any instances of this droplet
	instances = DropletInstance.query.filter_by(droplet_id=droplet_id).all()
	for instance in instances:
		docker_client = docker.from_env()
		container = docker_client.containers.get(f"flowcase_generated_{instance.id}")
		container.remove(force=True)
		db.session.delete(instance)
		db.session.commit()
 
	return jsonify({"success": True})

@app.route('/api/admin/delete_instance', methods=['POST'])
@login_required
def api_admin_delete_instance():
	if not Permissions.check_permission(current_user.id, Permissions.EDIT_INSTANCES):
		return jsonify({"success": False, "error": "Unauthorized"}), 403

	instance_id = request.json.get('id')
	instance = DropletInstance.query.filter_by(id=instance_id).first()
	if not instance:
		return jsonify({"success": False, "error": "Instance not found"}), 404
 
	docker_client = docker.from_env()
	try:
		container = docker_client.containers.get(f"flowcase_generated_{instance.id}")
		container.remove(force=True)
	except:
		pass
	db.session.delete(instance)
	db.session.commit()
 
	return jsonify({"success": True})

@app.route('/api/admin/edit_user', methods=['POST'])
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
  
	#validate input
	user.username = request.json.get('username')
	if not user.username:
		return jsonify({"success": False, "error": "Username is required"}), 400
	if " " in user.username:
		return jsonify({"success": False, "error": "Username cannot contain spaces"}), 400

	print(request.json.get('groups'))
	groups_json_string = "["
	for group in request.json.get('groups'):
		groups_json_string += f'"{group}",'
	user.groups = groups_json_string[:-1] + "]"
	if not user.groups or user.groups == "" or user.groups == "]":
		return jsonify({"success": False, "error": "Groups are required"}), 400

	#Passwords can only be set, not changed
	if create_new:
		print("Creating new user with password: " + request.json.get('password'))
		if not request.json.get('password'):
			return jsonify({"success": False, "error": "Password is required"}), 400
		user.password = bcrypt.generate_password_hash(request.json.get('password')).decode('utf-8')
 
	if create_new:
		db.session.add(user)
 
	db.session.commit()
 
	return jsonify({"success": True})

@app.route('/api/admin/delete_user', methods=['POST'])
@login_required
def api_admin_delete_user():
	if not Permissions.check_permission(current_user.id, Permissions.EDIT_USERS):
		return jsonify({"success": False, "error": "Unauthorized"}), 403

	user_id = request.json.get('id')
	user = User.query.filter_by(id=user_id).first()
	if not user:
		return jsonify({"success": False, "error": "User not found"}), 404
 
	db.session.delete(user)
	db.session.commit()
 
	#delete any instances of this user
	instances = DropletInstance.query.filter_by(user_id=user_id).all()
	for instance in instances:
		docker_client = docker.from_env()
		container = docker_client.containers.get(f"flowcase_generated_{instance.id}")
		container.remove(force=True)
		db.session.delete(instance)
		db.session.commit()
 
	return jsonify({"success": True})

@app.route('/api/admin/groups', methods=['GET'])
@login_required
def api_admin_groups():
	if not Permissions.check_permission(current_user.id, Permissions.VIEW_GROUPS):
		return jsonify({"success": False, "error": "Unauthorized"}), 403

	groups = Group.query.all()
 
	Response = {
		"success": True,
		"groups": []
	}
 
	for group in groups:
		Response["groups"].append({
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
				"view_groups": group.perm_view_groups,
				"edit_groups": group.perm_edit_groups
			}
		})
 
	return jsonify(Response)

@app.route('/api/admin/edit_group', methods=['POST'])
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
	
	#validate input
	group.display_name = request.json.get('display_name')
	if not group.display_name:
		return jsonify({"success": False, "error": "Display Name is required"}), 400
 
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

@app.route('/api/admin/delete_group', methods=['POST'])
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

@app.route('/api/get_droplets', methods=['GET'])
@login_required
def get_droplets():
	droplets = Droplet.query.all()
	droplets = sorted(droplets, key=lambda x: x.display_name)
 
	Response = {
		"success": True,
		"droplets": []
	}
 
	for droplet in droplets:
		Response["droplets"].append({
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
 
	return jsonify(Response)

@app.route('/api/get_instances', methods=['GET'])
@login_required
def get_instances():
	instances = DropletInstance.query.filter_by(user_id=current_user.id).all()
 
	Response = {
		"success": True,
		"instances": []
	}
 
	for instance in instances:
		droplet = Droplet.query.filter_by(id=instance.droplet_id).first()
		Response["instances"].append({
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
 
	return jsonify(Response)

@app.route('/api/request_new_instance', methods=['POST'])
@login_required
def request_new_instance():
	droplet_id = request.json.get('droplet_id')
	droplet = Droplet.query.filter_by(id=droplet_id).first()
	if not droplet:
		return jsonify({"success": False, "error": "Droplet not found"}), 404

	#Check if system has enough resources to request this droplet
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

	docker_client = docker.from_env()
 
	#check if docker image is downloaded
	images = docker_client.images.list()
	image_exists = False
	for image in images:
		if droplet.container_docker_image in image.tags:
			image_exists = True
			break
		
	if not image_exists:
		log("WARNING", f"Docker image {droplet.container_docker_image} not found. Please download the image and try again.")
		return jsonify({"success": False, "error": "Docker image not found. Image might still be downloading."}), 400

	#Create a new instance
	instance = DropletInstance(droplet_id=droplet_id, user_id=current_user.id)
	db.session.add(instance)
	db.session.commit()
 
	#Create a docker container
	log("INFO", f"Creating new instance for user {current_user.username} with droplet {droplet.display_name}")
 
	name = f"flowcase_generated_{instance.id}"
 
	request_resolution = request.json.get('resolution')
	if re.match(r"[0-9]+x[0-9]+", request_resolution):
		resolution = request_resolution
	else:
		resolution = "1280x720"
	
	container = docker_client.containers.run(
		image=droplet.container_docker_image,
		name=name,
		environment={"DISPLAY": ":1", "VNC_PW": current_user.id, "VNC_RESOLUTION": resolution},
		detach=True,
		network="flowcase_default_network",
		mem_limit=f"{droplet.container_memory}000000",
		cpu_shares=droplet.container_cores * 1024,
	)
 
	log("INFO", f"Instance created for user {current_user.username} with droplet {droplet.display_name}")
 
	#Wait for container to start
	time.sleep(.5)
 
	#create nginx config
	container = docker_client.containers.get(f"flowcase_generated_{instance.id}")
	ip = container.attrs['NetworkSettings']['Networks']['flowcase_default_network']['IPAddress']
	
	#TODO: Use a more secure method for generating auth header
	authHeader = base64.b64encode(b'flowcase_user:' + current_user.id.encode()).decode('utf-8')
 
	nginx_config = f"""
 	location /desktop/{instance.id}/vnc/ {{
		proxy_pass https://{ip}:6901/;
  
		proxy_set_header Authorization "Basic {authHeader}";
	}}
 
	location /desktop/{instance.id}/vnc/websockify {{
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
		proxy_pass https://{ip}:4902/;
  
		proxy_set_header Authorization "Basic {authHeader}";
	}}
	"""
 
	#write nginx config
	if os.path.exists("/etc/nginx/"):
		os.makedirs("/etc/nginx/conf.d/containers.d", exist_ok=True)
		with open(f"/etc/nginx/conf.d/containers.d/{instance.id}.conf", "w") as f:
			f.write(nginx_config)
   
		#reload nginx
		os.system("nginx -s reload")
		time.sleep(.75)
 
	return jsonify({"success": True, "instance_id": instance.id})
 
@app.route('/droplet/<string:instance_id>', methods=['GET'])
@login_required
def droplet(instance_id: str):
	instance = DropletInstance.query.filter_by(id=instance_id).first()
	if not instance:
		return redirect("/")

	if instance.user_id != current_user.id:
		return redirect("/")

	return render_template('droplet.html', instance_id=instance_id)

@app.route('/api/instance/<string:instance_id>/destroy', methods=['GET'])
@login_required
def stop_instance(instance_id: str):
	instance = DropletInstance.query.filter_by(id=instance_id).first()
	if not instance:
		return jsonify({"success": False, "error": "Instance not found"}), 404

	if instance.user_id != current_user.id:
		return jsonify({"success": False, "error": "Unauthorized"}), 403

	docker_client = docker.from_env()
	try:
		container = docker_client.containers.get(f"flowcase_generated_{instance.id}")
		container.remove(force=True)
	except:
		pass
  
	#delete nginx config
	if os.path.exists(f"/etc/nginx/conf.d/containers.d/{instance.id}.conf"):
		os.remove(f"/etc/nginx/conf.d/containers.d/{instance.id}.conf")
	
	db.session.delete(instance)
	db.session.commit()
 
	return jsonify({"success": True})

#Auto pull images
def thread_pull_images():
	while True:
		pull_images()
  
def pull_images():
	with app.app_context():
		docker_client = docker.from_env()
		droplets = Droplet.query.all()
		for droplet in droplets:
			if droplet.container_docker_image is None:
				continue
			log("INFO", f"Pulling Docker image {droplet.container_docker_image}")
			image = droplet.container_docker_image.split(":")[0]
			tag = droplet.container_docker_image.split(":")[-1]
			try:
				docker_client.images.pull(image, tag)
			except Exception as e:
				log("ERROR", f"Error pulling Docker image {droplet.container_docker_image}: {e}")

		time.sleep(60)

if __name__ == '__main__':
	with app.app_context():
		db.create_all()
		first_run()
		startup()
	
	threading.Thread(target=thread_pull_images).start()
	
	app.run(debug=args.debug, port=args.port)