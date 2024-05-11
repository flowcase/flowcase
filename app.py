import argparse
import os
import random
import string
import uuid
from flask import Flask, Request, render_template, make_response, jsonify, request, redirect, url_for, abort, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flowcase.db'
db = SQLAlchemy(app)

bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = '/'

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=5000)
parser.add_argument('--debug', action='store_true')

args, _ = parser.parse_known_args()

#check if flaskkey exists
if not os.path.exists("flaskkey"):
	print("Creating new Flask secret key")
	#create a new key
	with open("flaskkey", "w") as f:
		f.write(''.join(random.choice(string.ascii_letters + string.digits) for i in range(64)))
app.secret_key = open("flaskkey", "r").read()

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
 
class DropletInstance(db.Model):
	id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
	droplet_id = db.Column(db.String(36), db.ForeignKey('droplet.id'), nullable=False)
	user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
	created_at = db.Column(db.DateTime, server_default=func.now())
	updated_at = db.Column(db.DateTime, server_default=func.now(), onupdate=func.now())

@login_manager.user_loader
def load_user(user_id):
	return User.query.get(user_id)

@app.route('/')
def index():
	if current_user.is_authenticated:
		return redirect(url_for('dashboard'))
	return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

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
	print("Running first run")
	if User.query.count() == 0:
		admin_random_password = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(16))
		create_user("admin", admin_random_password)
		user_random_password = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(16))
		create_user("user", user_random_password)
  
		print(f"Created user \"admin\" with password: {admin_random_password}")
		print(f"Created user \"user\" with password: {user_random_password}")

if __name__ == '__main__':
	with app.app_context():
		first_run()
		db.create_all()
	app.run(debug=args.debug, port=args.port)