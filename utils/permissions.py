from __init__ import db

class Permissions:
	ADMIN_PANEL = "perm_admin_panel"
	VIEW_INSTANCES = "perm_view_instances"
	EDIT_INSTANCES = "perm_edit_instances"
	VIEW_USERS = "perm_view_users"
	EDIT_USERS = "perm_edit_users"
	VIEW_DROPLETS = "perm_view_droplets"
	EDIT_DROPLETS = "perm_edit_droplets"
	VIEW_REGISTRY = "perm_view_registry"
	EDIT_REGISTRY = "perm_edit_registry"
	VIEW_GROUPS = "perm_view_groups"
	EDIT_GROUPS = "perm_edit_groups"

	@staticmethod
	def check_permission(userid, permission):
		from models.user import User, Group
		
		#go through all groups and check if the user has the permission
		user = User.query.filter_by(id=userid).first()
		groups = user.groups.split(",")

		for group in groups:
			group = Group.query.filter_by(id=group).first()
	
			if not group: #group not found, most likely deleted
				continue

			if getattr(group, permission):
				return True
		return False 