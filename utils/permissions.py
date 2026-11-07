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
	CHANGE_PASSWORD = "perm_change_password"

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

def can_use_droplet(user, droplet):
	"""Admins can use every droplet; others need a group the droplet is restricted to"""
	from models.user import Group
	user_groups = user.get_groups()
	if any(g and g.display_name == "Admin" for g in (Group.query.filter_by(id=gid).first() for gid in user_groups)):
		return True
	droplet_groups = droplet.restricted_groups.split(',') if droplet.restricted_groups else []
	return any(gid in droplet_groups for gid in user_groups)

def can_access_instance(user, instance):
	"""Owners can use their own instance; users who can edit instances can use any"""
	return instance.user_id == user.id or user.has_permission(Permissions.EDIT_INSTANCES)
