import uuid
from flask_login import UserMixin
from sqlalchemy.sql import func
from __init__ import db
from utils.permissions import Permissions

class User(UserMixin, db.Model):
	id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
	username = db.Column(db.String(80), unique=True, nullable=False)
	password = db.Column(db.String(80), nullable=False)
	auth_token = db.Column(db.String(80), nullable=False)
	created_at = db.Column(db.DateTime, server_default=func.now())
	groups = db.Column(db.String(255), nullable=False)
	usertype = db.Column(db.String(20), nullable=False, default="Internal")
	protected = db.Column(db.Boolean, nullable=False, default=False)
	
	def has_permission(self, permission):
		return Permissions.check_permission(self.id, permission)

	def get_groups(self):
		return self.groups.split(',')
 
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
	perm_view_registry = db.Column(db.Boolean, nullable=False)
	perm_edit_registry = db.Column(db.Boolean, nullable=False)
	perm_view_groups = db.Column(db.Boolean, nullable=False)
	perm_edit_groups = db.Column(db.Boolean, nullable=False) 