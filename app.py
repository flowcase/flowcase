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
from flask import Flask, Request, render_template, make_response, jsonify, request, redirect, url_for, abort, send_from_directory, Response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
import docker
import psutil

__version__ = "develop"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.getcwd(), 'data', 'flowcase.db')
db = SQLAlchemy(app)

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
 
class Droplet(db.Model):
	id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
	display_name = db.Column(db.String(80), nullable=False)
	description = db.Column(db.String(255), nullable=False)
	container_docker_image = db.Column(db.String(255), nullable=False)
	container_docker_registry = db.Column(db.String(255), nullable=False)
	container_cores = db.Column(db.Integer, nullable=False)
	container_memory = db.Column(db.Integer, nullable=False)
	image_path = db.Column(db.String(255), nullable=True)
 
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

def create_user(username, password):
	user = User(username=username, password=bcrypt.generate_password_hash(password).decode('utf-8'))
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
 
	#Check that Docker is installed
	if os.system("docker -v") != 0 and not args.ignore_docker:
		print("Docker is not installed. Please install Docker and try again.")
		exit(1)
  
	#Create Flask secret key, if not already created
	if not os.path.exists("data/secret_key"):
		print("Creating secret key...")
		with open("data/secret_key", "w") as f:
			f.write(''.join(random.choice(string.ascii_letters + string.digits) for i in range(64)))
  
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
  
	#create default Admin and User accounts
	if User.query.count() == 0:
		admin_random_password = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(16))
		create_user("admin", admin_random_password)
		user_random_password = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(16))
		create_user("user", user_random_password)

		print("Created default users:")
		print(f"Username: admin, Password: {admin_random_password}")
		print(f"Username: user, Password: {user_random_password}")
  
	#Check if docker is running
	if args.ignore_docker:
		return

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
 
@app.route('/api/admin/system_info', methods=['GET'])
@login_required
def api_admin_system():
    #TODO: check if user has permission to access this route
 
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
    #TODO: check if user has permission to access this route
    
	users = User.query.all()
 
	Response = {
		"success": True,
		"users": []
	}
 
	for user in users:
		Response["users"].append({
			"id": user.id,
			"username": user.username,
			"created_at": user.created_at
		})
 
	return jsonify(Response)

@app.route('/api/admin/instances', methods=['GET'])
@login_required
def api_admin_instances():
	instances = DropletInstance.query.all()
 
	Response = {
		"success": True,
		"instances": []
	}
 
	for instance in instances:
		droplet = Droplet.query.filter_by(id=instance.droplet_id).first()
		user = User.query.filter_by(id=instance.user_id).first()
		Response["instances"].append({
			"id": instance.id,
			"created_at": instance.created_at,
			"updated_at": instance.updated_at,
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

@app.route('/api/admin/edit_droplet', methods=['POST'])
@login_required
def api_admin_edit_droplet():
	droplet_id = request.json.get('id')
	droplet = Droplet.query.filter_by(id=droplet_id).first()
 
	create_new = False
	if not droplet or droplet_id == "null":
		create_new = True
		droplet = Droplet()
  
	#validate input
	droplet.description = request.json.get('description', "")
	droplet.image_path = request.json.get('image_path', None)

	droplet.display_name = request.json.get('display_name')
	if not droplet.display_name:
		return jsonify({"success": False, "error": "Display Name is required"}), 400

	droplet.container_docker_registry = request.json.get('container_docker_registry')
	if not droplet.container_docker_registry:
		return jsonify({"success": False, "error": "Docker Registry is required"}), 400

	droplet.container_docker_image = request.json.get('container_docker_image')
	if not droplet.container_docker_image:
		return jsonify({"success": False, "error": "Docker Image is required"}), 400
 
	#ensure cores and memory are integers
	if not request.json.get('container_cores') or not request.json.get('container_memory'):
		return jsonify({"success": False, "error": "Cores and Memory are required"}), 400
	try:
		droplet.container_cores = int(request.json.get('container_cores'))
		droplet.container_memory = int(request.json.get('container_memory'))
	except:
		return jsonify({"success": False, "error": "Cores and Memory must be integers"}), 400
 
	if create_new:
		db.session.add(droplet)
 
	db.session.commit()
 
	return jsonify({"success": True})

@app.route('/api/admin/delete_droplet', methods=['POST'])
@login_required
def api_admin_delete_droplet():
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

	#Passwords can only be set, not changed
	if create_new:
		print("Creating new user with password: " + request.json.get('password'))
		user.password = bcrypt.generate_password_hash(request.json.get('password')).decode('utf-8')
 
	if create_new:
		db.session.add(user)
 
	db.session.commit()
 
	return jsonify({"success": True})

@app.route('/api/admin/delete_user', methods=['POST'])
@login_required
def api_admin_delete_user():
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
  
@app.route('/api/get_droplets', methods=['GET'])
@login_required
def get_droplets():
	droplets = Droplet.query.all()
 
	Response = {
		"success": True,
		"droplets": []
	}
 
	for droplet in droplets:
		Response["droplets"].append({
			"id": droplet.id,
			"display_name": droplet.display_name,
			"description": droplet.description,
			"container_docker_image": droplet.container_docker_image,
			"container_docker_registry": droplet.container_docker_registry,
			"container_cores": droplet.container_cores,
			"container_memory": droplet.container_memory,
			"image_path": droplet.image_path
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
				"container_docker_image": droplet.container_docker_image,
				"container_docker_registry": droplet.container_docker_registry,
				"container_cores": droplet.container_cores,
				"container_memory": droplet.container_memory,
				"image_path": droplet.image_path
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

	#Check if user has enough resources to request this droplet
	instances = DropletInstance.query.filter_by(user_id=current_user.id).all()
	
	cores = 0
	memory = 0
	for instance in instances:
		cores += Droplet.query.filter_by(id=instance.droplet_id).first().container_cores
		memory += Droplet.query.filter_by(id=instance.droplet_id).first().container_memory
	
	system_cores = os.cpu_count()
	free_memory = psutil.virtual_memory().available / 1024 / 1024
	if cores + droplet.container_cores > system_cores or memory + droplet.container_memory > free_memory:
		log("ERROR", f"Insufficient resources for user {current_user.username} to request droplet {droplet.display_name}")
		return jsonify({"success": False, "error": "Insufficient resources"}), 400

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
		return jsonify({"success": False, "error": "Docker image not found"}), 404

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

if __name__ == '__main__':
	with app.app_context():
		first_run()
		db.create_all()
		startup()
	app.run(debug=args.debug, port=args.port)