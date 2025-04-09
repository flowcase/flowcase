import uuid
from sqlalchemy.sql import func
from __init__ import db

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
	container_persistent_profile_path = db.Column(db.String(255), nullable=True)
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