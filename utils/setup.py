import os
from datetime import datetime, timedelta
from __init__ import db
from models.user import User, Group
from models.registry import Registry
from models.log import Log
from utils.logger import log

def create_default_groups():
	"""Create default Admin and User groups if they don't exist"""
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
			perm_view_registry=True,
			perm_edit_registry=True,
			perm_view_groups=True,
			perm_edit_groups=True,
			perm_change_password=True
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
			perm_view_registry=False,
			perm_edit_registry=False,
			perm_view_groups=False,
			perm_edit_groups=False,
			perm_change_password=True
		)
		db.session.add(user_group)
		db.session.commit()

def needs_setup():
	"""True until the first admin account has been created through /setup"""
	return User.query.filter_by(protected=True).first() is None

def create_default_registry():
	"""Create default registry if none exists"""
	if Registry.query.count() == 0:
		flowcase_registry = Registry(url="https://registry.flowcase.org")
		db.session.add(flowcase_registry)
		db.session.commit()

def initialize_app(app):
	"""Initialize the application for first run"""
	with app.app_context():
		# delete old logs, this should probably be configurable
		Log.query.filter(Log.created_at < datetime.utcnow() - timedelta(days=30)).delete()
		db.session.commit()
		
		os.makedirs("data", exist_ok=True)
		
		# Create the firstrun file if it doesn't exist
		if not os.path.exists("data/.firstrun"):
			with open("data/.firstrun", "w") as f:
				f.write("")
			
			# Create default groups and registry; the admin account is created on first visit (/setup)
			create_default_groups()
			create_default_registry()
			log("INFO", "Flowcase initialized for the first time.") 