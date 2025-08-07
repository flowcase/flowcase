import random
import string
import os
from flask import Blueprint, request, redirect, url_for, render_template, make_response, session, g
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.sql import func
from __init__ import db, bcrypt, login_manager
from models.user import User, Group
from utils.logger import log

auth_bp = Blueprint('auth', __name__)

@auth_bp.before_app_request
def before_request():
	"""
	Global before_request handler to ensure header authentication is processed on all routes.
	This ensures that header-based authentication works even when users access protected routes directly.
	"""
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

@login_manager.user_loader
def load_user(user_id):
	return User.query.get(user_id)

def user_exists(username):
	"""Check if a user exists"""
	return User.query.filter(func.lower(User.username) == func.lower(username)).first() is not None

def create_external_user(username):
	"""Create a user with a random password and no group membership"""
	# Generate a random password
	random_password = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(16))
	
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
			log("INFO", f"Using Traefik + Authentik header authentication for user: {ext_identity}")
		else:
			log("WARNING", "FLOWCASE_TRAEFIK_AUTHENTIK is enabled but X-Authentik-Username header is missing or empty")
			# Fall back to environment variable method
			ext_identity = os.environ.get('FLOWCASE_EXT_USER')
			if ext_identity:
				auth_method = "environment variable (fallback)"
				log("INFO", f"Falling back to environment variable authentication for user: {ext_identity}")
	else:
		# Default: Environment variable method
		ext_identity = os.environ.get('FLOWCASE_EXT_USER')
		if ext_identity:
			auth_method = "environment variable"
			log("INFO", f"Using environment variable authentication for user: {ext_identity}")
	
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

		response = make_response(redirect(url_for('auth.dashboard')))
  
		cookie_age = 60 * 60 * 24 * 365 if remember else None
		response.set_cookie('userid', user.id, max_age=cookie_age)
		response.set_cookie('username', user.username, max_age=cookie_age)
		response.set_cookie('token', user.auth_token, max_age=cookie_age)
		return response
	else:
		session['error'] = "Invalid username or password."
		return redirect(url_for('auth.index'))

@auth_bp.route('/logout')
@login_required
def logout():
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
	
	# Delete cookies
	response.set_cookie('userid', '', expires=0)
	response.set_cookie('username', '', expires=0)
	response.set_cookie('token', '', expires=0)
	return response

@auth_bp.route('/droplet_connect', methods=['GET'])
def droplet_connect():
	"""
	Authenticate droplet connection requests.
	Supports both cookie-based authentication (legacy) and header-based authentication (Traefik + Authentik).
	"""
	# First, try cookie-based authentication (backward compatibility)
	userid = request.cookies.get("userid")
	token = request.cookies.get("token")
	
	if userid and token:
		user = User.query.filter_by(id=userid).first()
		if user and user.auth_token == token:
			log("INFO", f"Droplet connection authenticated via cookie for user: {user.username}")
			return make_response("", 200)
		else:
			log("WARNING", f"Cookie authentication failed for droplet connection - invalid user or token")
	
	# Fallback to header-based authentication if cookie authentication fails
	if os.environ.get('FLOWCASE_TRAEFIK_AUTHENTIK') == '1':
		authentik_username = request.headers.get('X-Authentik-Username')
		if authentik_username and authentik_username.strip():
			username = authentik_username.strip()
			user = User.query.filter(func.lower(User.username) == func.lower(username)).first()
			
			if user:
				log("INFO", f"Droplet connection authenticated via header for user: {user.username}")
				return make_response("", 200)
			else:
				# Create the user if it doesn't exist (same as in check_external_identity)
				try:
					user = create_external_user(username)
					log("INFO", f"Created and authenticated external user {user.username} for droplet connection")
					return make_response("", 200)
				except Exception as e:
					log("ERROR", f"Failed to create external user {username} for droplet connection: {str(e)}")
					return make_response("", 401)
		else:
			log("WARNING", "Header authentication attempted for droplet connection but X-Authentik-Username header is missing or empty")
	
	# If both authentication methods fail
	log("WARNING", "Droplet connection authentication failed - no valid cookie or header authentication")
	return make_response("", 401)

def generate_auth_token() -> str:
	return ''.join(random.choice(string.ascii_letters + string.digits) for i in range(80))

def create_user(username, password, groups, usertype="Internal", protected=False):
	# Convert username to lowercase for case-insensitive handling
	user = User(username=username.lower(), password=bcrypt.generate_password_hash(password).decode('utf-8'),
				groups=groups, auth_token=generate_auth_token(), usertype=usertype, protected=protected)
	db.session.add(user)
	db.session.commit()
	return user