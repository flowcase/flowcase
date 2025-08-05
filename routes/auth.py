import random
import string
import os
from flask import Blueprint, request, redirect, url_for, render_template, make_response, session
from flask_login import login_user, logout_user, login_required, current_user
from __init__ import db, bcrypt, login_manager
from models.user import User, Group
from utils.logger import log

auth_bp = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
	return User.query.get(user_id)

def user_exists(username):
	"""Check if a user exists"""
	return User.query.filter_by(username=username).first() is not None

def create_external_user(username):
	"""Create a user with a random password and no group membership"""
	# Generate a random password
	random_password = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(16))
	
	# Create the user with no group membership
	user = create_user(username, random_password, "", usertype="External")
	
	# Create the user
	user = create_user(username, random_password, f"{unassigned_group.id}", usertype="External")
	
	log("INFO", f"Created external user {username} with random password and no group membership")
	return user

def check_external_identity():
	"""Check if external identity is enabled and log in the user if it is"""
	ext_identity = os.environ.get('FLOWCASE_EXT_USER')
	if ext_identity:
		user = User.query.filter_by(username=ext_identity).first()
		if user:
			login_user(user)
			log("INFO", f"User {user.username} logged in via external identity")
			return True
		else:
			# Create the user if it doesn't exist
			user = create_external_user(ext_identity)
			login_user(user)
			log("INFO", f"Created and logged in external user {user.username}")
			return True
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
	user = User.query.filter_by(username=username).first()
	
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
 
	# Delete cookies
	response = make_response(redirect(url_for('auth.index')))
	response.set_cookie('userid', '', expires=0)
	response.set_cookie('username', '', expires=0)
	response.set_cookie('token', '', expires=0)
	return response

@auth_bp.route('/droplet_connect', methods=['GET'])
def droplet_connect():
	userid = request.cookies.get("userid")
	token = request.cookies.get("token")
 
	if not userid or not token:
		return make_response("", 401)

	user = User.query.filter_by(id=userid).first()
	if not user:
		return make_response("", 401)

	if user.auth_token != token:
		return make_response("", 401)
	
	return make_response("", 200)

def generate_auth_token() -> str:
	return ''.join(random.choice(string.ascii_letters + string.digits) for i in range(80))

def create_user(username, password, groups, usertype="Internal", protected=False):
	user = User(username=username, password=bcrypt.generate_password_hash(password).decode('utf-8'),
				groups=groups, auth_token=generate_auth_token(), usertype=usertype, protected=protected)
	db.session.add(user)
	db.session.commit()
	return user