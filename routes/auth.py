import secrets
import os
from flask import Blueprint, request, redirect, url_for, render_template, make_response, session, g, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.sql import func
from __init__ import db, bcrypt, login_manager
from models.user import User, Group
from models.droplet import DropletInstance
from utils.logger import log
from utils.setup import needs_setup
from utils.permissions import Permissions
import utils.docker

auth_bp = Blueprint('auth', __name__)

_setup_complete = False

def setup_required():
	"""True until the first admin exists. Once false it stays false for this process."""
	global _setup_complete
	if _setup_complete:
		return False
	if needs_setup():
		return True
	_setup_complete = True
	return False

@auth_bp.before_app_request
def before_request():
	"""
	Global before_request handler to ensure header authentication is processed on all routes.
	This ensures that header-based authentication works even when users access protected routes directly.
	"""
	# Nothing works until the first admin account has been created
	if request.endpoint and not request.endpoint.startswith('static') and request.endpoint != 'auth.setup' and setup_required():
		return redirect(url_for('auth.setup'))

	# Skip authentication check for static files and certain endpoints
	if request.endpoint and (request.endpoint.startswith('static') or
							request.endpoint in ['auth.login', 'auth.logout']):
		return
	
	# Only check external identity if user is not already authenticated
	if not current_user.is_authenticated:
		try:
			if check_external_identity():
				log("INFO", f"User authenticated via header authentication on route: {request.endpoint}")
		except Exception as e:
			log("ERROR", f"Error in before_request header authentication: {str(e)}")

	# A user who must reset their password can only reach the reset page (static files, login and logout returned above)
	if current_user.is_authenticated and current_user.force_password_reset and request.endpoint != 'auth.change_password':
		if request.path.startswith('/api/') or request.path.startswith('/droplet_connect'):
			return jsonify({"success": False, "error": "Password change required"}), 403
		return redirect(url_for('auth.change_password'))

@login_manager.user_loader
def load_user(user_id):
	return User.query.get(user_id)

def user_exists(username):
	"""Check if a user exists"""
	return User.query.filter(func.lower(User.username) == func.lower(username)).first() is not None

def create_external_user(username):
	"""Create a user with a random password and no group membership"""
	# Generate a random password
	random_password = secrets.token_urlsafe(12)
	
	# Get the unassigned group
	unassigned_group = Group.query.filter_by(display_name="Unassigned").first()
	group_id = f"{unassigned_group.id}" if unassigned_group else ""
	
	# Create the user with lowercase username
	user = create_user(username, random_password, group_id, usertype="External")
	
	log("INFO", f"Created external user {username} with random password")
	return user

def check_external_identity():
	"""Check if external identity is enabled and log in the user if it is"""
	ext_identity = None
	auth_method = "unknown"
	
	# Check if Traefik + Authentik header-based authentication is enabled
	if os.environ.get('FLOWCASE_TRAEFIK_AUTHENTIK') == '1':
		# Priority: Header-based authentication via Traefik + Authentik
		authentik_username = request.headers.get('X-Authentik-Username')
		if authentik_username and authentik_username.strip():
			ext_identity = authentik_username.strip()
			auth_method = "Traefik + Authentik header"
		else:
			log("WARNING", "FLOWCASE_TRAEFIK_AUTHENTIK is enabled but X-Authentik-Username header is missing or empty")
			# Fall back to environment variable method
			ext_identity = os.environ.get('FLOWCASE_EXT_USER')
			if ext_identity:
				auth_method = "environment variable (fallback)"
	else:
		# Default: Environment variable method
		ext_identity = os.environ.get('FLOWCASE_EXT_USER')
		if ext_identity:
			auth_method = "environment variable"
	
	# Process external identity if found
	if ext_identity:
		try:
			user = User.query.filter(func.lower(User.username) == func.lower(ext_identity)).first()
			if user:
				login_user(user)
				log("INFO", f"User {user.username} logged in via external identity ({auth_method})")
				return True
			else:
				# Create the user if it doesn't exist
				user = create_external_user(ext_identity)
				login_user(user)
				log("INFO", f"Created and logged in external user {user.username} via {auth_method}")
				return True
		except Exception as e:
			log("ERROR", f"Failed to process external identity authentication for {ext_identity}: {str(e)}")
			return False
	
	return False

@auth_bp.route('/')
def index():
	# Check for external identity login first
	if check_external_identity():
		return redirect(url_for('auth.dashboard'))
	
	if current_user.is_authenticated:
		return redirect(url_for('auth.dashboard'))
	return render_template('login.html', error=session.pop('error', None))

@auth_bp.route('/setup', methods=['GET', 'POST'])
def setup():
	"""First-run page: create the admin account. Only available while no admin exists."""
	global _setup_complete
	if not setup_required():
		return redirect(url_for('auth.index'))

	error = None
	if request.method == 'POST':
		username = request.form.get('username', '').strip().lower()
		password = request.form.get('password', '')
		if not username or ' ' in username:
			error = "Username is required and cannot contain spaces."
		elif len(password) < 8:
			error = "Password must be at least 8 characters."
		elif password != request.form.get('confirm_password', ''):
			error = "Passwords do not match."
		elif not needs_setup():  # someone else finished setup while this form was open
			return redirect(url_for('auth.index'))
		else:
			admin_group = Group.query.filter_by(display_name='Admin').first()
			user_group = Group.query.filter_by(display_name='User').first()
			user = create_user(username, password, f"{admin_group.id},{user_group.id}", protected=True)
			_setup_complete = True
			log("INFO", f"Created admin account {user.username} through first-time setup")
			login_user(user)
			return redirect(url_for('auth.dashboard'))

	return render_template('setup.html', error=error)

@auth_bp.route('/dashboard')
@login_required
def dashboard():
	return render_template('dashboard.html')

@auth_bp.route('/login', methods=['POST'])
def login():
	username = request.form['username']
	password = request.form['password']
	remember = request.form.get('remember', False)
	user = User.query.filter(func.lower(User.username) == func.lower(username)).first()
	
	if user and bcrypt.check_password_hash(user.password, password):
		login_user(user, remember=remember)

		return redirect(url_for('auth.dashboard'))
	else:
		session['error'] = "Invalid username or password."
		return redirect(url_for('auth.index'))

@auth_bp.route('/account/password', methods=['GET', 'POST'])
@login_required
def change_password():
	forced = current_user.force_password_reset
	if not (forced or current_user.has_permission(Permissions.CHANGE_PASSWORD)):
		return redirect(url_for('auth.dashboard'))

	error = None
	if request.method == 'POST':
		current_password = request.form.get('current_password', '')
		new_password = request.form.get('new_password', '')
		if not bcrypt.check_password_hash(current_user.password, current_password):
			error = "Current password is incorrect."
		elif len(new_password) < 8:
			error = "New password must be at least 8 characters."
		elif new_password != request.form.get('confirm_password', ''):
			error = "New passwords do not match."
		elif new_password == current_password:
			error = "New password must be different from the current one."
		else:
			current_user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
			current_user.force_password_reset = False
			db.session.commit()
			log("INFO", f"User {current_user.username} changed their password")
			return redirect(url_for('auth.dashboard'))

	return render_template('change_password.html', error=error, forced=forced)

@auth_bp.route('/logout')
@login_required
def logout():
	# Destroy all running instances for this user before logging out
	user_instances = DropletInstance.query.filter_by(user_id=current_user.id).all()
	for instance in user_instances:
		try:
			if utils.docker.docker_client:
				container = utils.docker.docker_client.containers.get(f"flowcase_generated_{instance.id}")
				container.remove(force=True)
		except Exception as e:
			log("ERROR", f"Error removing container on logout: {str(e)}")

		try:
			nginx_conf = f"/flowcase/nginx/containers.d/{instance.id}.conf"
			if os.path.exists(nginx_conf):
				os.remove(nginx_conf)
		except Exception as e:
			log("ERROR", f"Error removing nginx config on logout: {str(e)}")

		db.session.delete(instance)

	if user_instances:
		db.session.commit()
		log("INFO", f"Cleaned up {len(user_instances)} instance(s) on logout for user {current_user.username}")
		try:
			if utils.docker.docker_client:
				nginx_container = utils.docker.docker_client.containers.get("flowcase-nginx")
				nginx_container.exec_run("nginx -s reload")
		except Exception as e:
			log("ERROR", f"Error reloading nginx after logout cleanup: {str(e)}")

	logout_user()
	
	# Check if Traefik + Authentik is enabled
	if os.environ.get('FLOWCASE_TRAEFIK_AUTHENTIK') == '1':
		# Redirect to Authentik logout URL
		hostname = request.host.split(':')[0]
		authentik_logout_url = f"https://authentik.{hostname}/flows/-/default/invalidation/"
		response = make_response(redirect(authentik_logout_url))
	else:
		# Use default logout behavior
		response = make_response(redirect(url_for('auth.index')))
	
	return response

@auth_bp.route('/droplet_connect/<string:instance_id>', methods=['GET'])
def droplet_connect(instance_id):
	"""
	nginx auth_request target for /desktop/<instance_id>/...
	Allows the instance owner (or someone who can edit instances) using the normal login session.
	"""
	from utils.permissions import can_access_instance

	if not current_user.is_authenticated:
		log("WARNING", f"Droplet connection denied for instance {instance_id}: no logged-in session on the request")
		return make_response("", 401)

	instance = DropletInstance.query.filter_by(id=instance_id).first()
	if not instance or not can_access_instance(current_user, instance):
		log("WARNING", f"Droplet connection denied for user {current_user.username} to instance {instance_id}")
		return make_response("", 403)

	return make_response("", 200)

@auth_bp.route('/droplet_connect', methods=['GET'])
def droplet_connect_legacy():
	"""Instances created before per-instance auth still call this path; they must be recreated"""
	log("WARNING", "Droplet connection denied: this instance's nginx config is outdated, destroy it and start a new one")
	return make_response("", 401)

def generate_auth_token() -> str:
	return secrets.token_urlsafe(48)

def create_user(username, password, groups, usertype="Internal", protected=False):
	# Convert username to lowercase for case-insensitive handling
	user = User(username=username.lower(), password=bcrypt.generate_password_hash(password).decode('utf-8'),
				groups=groups, auth_token=generate_auth_token(), usertype=usertype, protected=protected)
	db.session.add(user)
	db.session.commit()
	return user