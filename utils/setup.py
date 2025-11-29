import os
import random
import string
from __init__ import db
from models.user import User, Group
from models.registry import Registry
from routes.auth import create_user
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
			perm_view_registry=False,
			perm_edit_registry=False,
			perm_view_groups=False,
			perm_edit_groups=False
		)
		db.session.add(user_group)
		db.session.commit()

def create_default_users():
	"""Create default admin and user accounts if none exist"""
	if User.query.count() == 0:
		admin_group = Group.query.filter_by(display_name='Admin').first()
		user_group = Group.query.filter_by(display_name='User').first()
		
		admin_groups = f"{admin_group.id},{user_group.id}"
		user_groups = f"{user_group.id}"
		
		admin_random_password = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(16))
		create_user("admin", admin_random_password, admin_groups, protected=True)
		
		user_random_password = ''.join(random.choice(string.ascii_letters + string.digits) for i in range(16))
		create_user("user", user_random_password, user_groups)

		print()
		print("Created default users:")
		print("-----------------------")
		print("Username: admin")
		print(f"Password: {admin_random_password}")
		print("-----------------------")
		print("Username: user")
		print(f"Password: {user_random_password}")
		print("-----------------------")
		print()

def create_default_registry():
	"""Create default registry if none exists"""
	if Registry.query.count() == 0:
		flowcase_registry = Registry(url="https://registry.flowcase.org")
		db.session.add(flowcase_registry)
		db.session.commit()

def initialize_app(app):
	"""Initialize the application for first run"""
	with app.app_context():
		log("INFO", "Initializing Flowcase...")
		
		os.makedirs("data", exist_ok=True)
		
		# Create the firstrun file if it doesn't exist
		if not os.path.exists("data/.firstrun"):
			with open("data/.firstrun", "w") as f:
				f.write("")
			
			# Create default groups, users and registry
			create_default_groups()
			create_default_users()
			create_default_registry()
		
		log("INFO", "Flowcase initialized.") 