var admin_droplets = [];
var admin_users = [];
var admin_groups = [];

window.addEventListener('load', () => {
	AdminChangeTab('system', document.querySelector('.admin-modal-sidebar-button'));
});

function OpenAdminPanel()
{
	var adminModal = document.getElementById('admin-modal');
	adminModal.classList.add('active');
}

function CloseAdminPanel()
{
	var adminModal = document.getElementById('admin-modal');
	adminModal.classList.remove('active');
}

document.addEventListener('click', (e) => {
	if (e.target.classList.contains('admin-modal')) {
		CloseAdminPanel();
	}
});

var currentTab;
function AdminChangeTab(tab, element = null)
{
	var header = document.getElementById('admin-modal-header');
	var subtext = document.getElementById('admin-modal-subtext');

	if (element != null) {
		//Remove active class from all buttons
		var buttons = document.querySelectorAll('.admin-modal-sidebar-button');
		buttons.forEach(button => {
			button.classList.remove('active');
		});

		//Add active class to the clicked button
		element.classList.add('active');
	}

	var content = document.querySelector('.admin-modal-main-content');
	if (currentTab != tab) {
		content.innerHTML = "";
		currentTab = tab;
	}

	switch (tab) {
		case 'users':
			header.innerText = "Users";
			subtext.innerText = "View and manage the users of the system.";

			//fetch groups as well
			if (userInfo.permissions.perm_view_groups) {
				FetchAdminGroups(function(json) {
				});
			}

			FetchAdminUsers(function(json) {
				content.innerHTML = ''

				if (userInfo.permissions.perm_edit_users) {	
					content.innerHTML += `
						<button class="button-1-full" onclick="ShowEditUser()">Create User</button>
						<hr>
					`;
				}

				content.innerHTML += `
					<table class="admin-modal-table">
						<tr>
							<th>Username</th>
							<th>Groups</th>
							${userInfo.permissions.perm_edit_users ? `<th>Actions</th>` : ''}
						</tr>
					${json["users"].map(user => `
						<tr>
							<td>${user.username}</td>
							<td>${user.groups.map(group => {return group.display_name}).join(', ')}</td>
							${userInfo.permissions.perm_edit_users ? `<td class="admin-modal-table-actions">
								<i class="fas fa-edit" onclick="ShowEditUser('${user.id}')"></i>
								<i class="fas fa-trash" onclick="AdminDeleteUser('${user.id}')"></i>
							</td>` : ''}
						</tr>
					`).join('')}
				</table>
				`;
			});
			break;
		case 'droplets':
			header.innerText = "Droplets";
			subtext.innerText = "View and manage droplets.";

			FetchAdminDroplets(function(json) {
				content.innerHTML = `
					${userInfo.permissions.perm_edit_droplets ? `
						<button class="button-1-full" onclick="ShowEditDroplet()">Create Droplet</button>
						<hr>
					` : ''}

				<table class="admin-modal-table">
					<tr>
						<th>Name</th>
						<th>Image / IP</th>
						${userInfo.permissions.perm_edit_droplets ? `<th>Actions</th>` : ''}
					</tr>
					${json["droplets"].map(droplet => `
						<tr>
							<td><div><img src="${droplet.image_path ? droplet.image_path : '/static/img/droplet_default.jpg'}"><p>${droplet.display_name}</p></div></td>
							<td>${droplet.droplet_type == "container" ? droplet.container_docker_image : droplet.server_ip}</td>
							${userInfo.permissions.perm_edit_droplets ? `<td class="admin-modal-table-actions">
								<i class="fas fa-edit" onclick="ShowEditDroplet('${droplet.id}')"></i>
								<i class="fas fa-trash" onclick="AdminDeleteDroplet('${droplet.id}')"></i>
							</td>` : ''}
						</tr>
					`).join('')}
				</table>
				`;
			});
			break;
		case 'registry':
			header.innerText = "Registry";
			subtext.innerText = "View and manage registries.";

			FetchAdminRegistry(function(json) {

			var droplets = [];
			//combine all droplets from all registries into one array and order by display name
			json["registry"].forEach(registry => {
				droplets = droplets.concat(registry.droplets);

				droplets.sort((a, b) => {
					if (a.display_name < b.display_name) {
						return -1;
					}
					if (a.display_name > b.display_name) {
						return 1;
					}
					return 0;
				});
			});

			flowcase_version = json["flowcase_version"];

			//set droplet registry name
			droplets.forEach(droplet => {
				droplet.registry_name = json["registry"].find(registry => registry.droplets.find(d => d.id == droplet.id)).info.name;

				//if tag of the flowcase version is found, set the intial tag to that, otherwise set to the first tag
				droplet.tagdefaultindex = droplet.container_docker_tags.findIndex(tag => tag == flowcase_version);
				if (droplet.tagdefaultindex == -1) {
					droplet.tagdefaultindex = 0;
				}
			});

			content.innerHTML = `
				<div class="admin-registry-add">
					<input type="text" placeholder="URL" id="admin-registry-url">
					<button class="button-1-full" onclick="AdminAddRegistry()">Add Registry</button>
				</div>

				<hr>

				<table class="admin-modal-table">
					<tr>
						<th>Name</th>
						<th>URL</th>
						<th>Actions</th>
					</tr>
					${json["registry"].map(registry => `
						<tr>
							<td>${registry.info.name}</td>
							<td>${registry.url}</td>
							<td class="admin-modal-table-actions">
								<i class="fas fa-trash" onclick="AdminDeleteRegistry('${registry.id}')"></i>
							</td>
						</tr>
					`).join('')}
				</table>
				
				<hr>

				<table class="admin-modal-table">
					<tr>
						<th>Name</th>
						<th>Image</th>
						<th>Registry</th>
						<th>Actions</th>
					</tr>
					${droplets.map(droplet => `
						<tr>
							<td><div><img src="${droplet.image_path ? droplet.image_path : '/static/img/droplet_default.jpg'}"><p>${droplet.display_name}</p></div></td>
							<td>
								<select style="width: 100%">
									${droplet.container_docker_tags.map((tag, index) => `
										<option ${index === droplet.tagdefaultindex ? 'selected' : ''} value="${tag}">${droplet.container_docker_image}:${tag}</option>
									`).join('')}
								</select>
							</td>
							<td>${droplet.registry_name}</td>
							<td class="admin-modal-table-actions">
								<i class="fas fa-edit" onclick="ShowEditDropletRegistry('${droplet.display_name}', '${droplet.description}', '${droplet.image_path}', '${droplet.container_docker_registry}', '${droplet.container_docker_image}', this.parentElement.parentElement.querySelector('select').value)"></i>
							</td>
						</tr>
					`).join('')}
			`;
			});
			break;
		case 'instances':
			header.innerText = "Instances";
			subtext.innerText = "View and manage the instances currently running.";

			FetchAdminInstances(function(json) {
				content.innerHTML = `
				<table class="admin-modal-table">
					<tr>
						<th>Name</th>
						<th>Username</th>
						<th>Creation Time</th>
						<th>Internal IP</th>
						${userInfo.permissions.perm_edit_instances ? `<th>Actions</th>` : ''}
					</tr>
					${json["instances"].map(instance => `
						<tr>
							<td><div><img src="${instance.droplet.image_path ? instance.droplet.image_path : '/static/img/droplet_default.jpg'}"><p>${instance.droplet.display_name}</p></div></td>
							<td>${instance.user.username}</td>
							<td>${instance.created_at}</td>
							<td>${instance.ip}</td>
							${userInfo.permissions.perm_edit_instances ? `<td class="admin-modal-table-actions">
								<i class="fas fa-trash" onclick="AdminDeleteInstance('${instance.id}')"></i>
							</td>` : ''}
						</tr>
					`).join('')}
				</table>
				`;
			});
			break;
		case 'system':
			header.innerText = "System";
			subtext.innerText = "View system information.";

			FetchAdminSystemInfo(function(json) {
				content.innerHTML = `
				<h3>System Information</h3>

				<div class="admin-modal-card">
					<p>Hostname</p>
					<textarea readonly disabled style="resize: none;">${json["system"]["hostname"]}</textarea>
				</div>

				<div class="admin-modal-card">
					<p>Operating System</p>
					<textarea readonly disabled style="resize: none;">${json["system"]["os"]}</textarea>
				</div>

				<h3>Versions</h3>

				<div class="admin-modal-card">
					<p>Flowcase</p>
					<textarea readonly disabled style="resize: none;">${json["version"]["flowcase"]}</textarea>
				</div>

				<div class="admin-modal-card">
					<p>Python</p>
					<textarea readonly disabled style="resize: none;">${json["version"]["python"]}</textarea>
				</div>

				<div class="admin-modal-card">
					<p>Docker</p>
					<textarea readonly disabled style="resize: none;">${json["version"]["docker"]}</textarea>
				</div>

				<div class="admin-modal-card">
					<p>nginx</p>
					<textarea readonly disabled style="resize: none;">${json["version"]["nginx"]}</textarea>
				</div>
				`;
				});
			break;
		case 'groups':
			header.innerText = "Groups";
			subtext.innerText = "View and manage the groups of the system.";

			FetchAdminGroups(function(json) {
				content.innerHTML = `
					${userInfo.permissions.perm_edit_groups ? `
						<button class="button-1-full" onclick="ShowEditGroup()">Create Group</button>
						<hr>
					` : ''}

				<table class="admin-modal-table">
					<tr>
						<th>Name</th>
						${userInfo.permissions.perm_edit_groups ? `<th>Actions</th>` : ''}
					</tr>
					${json["groups"].map(group => `
						<tr>
							<td>${group.display_name}</td>
							${userInfo.permissions.perm_edit_groups ? `<td class="admin-modal-table-actions">
								<i class="fas fa-edit" onclick="ShowEditGroup('${group.id}')"></i>
								<i class="fas fa-trash" onclick="AdminDeleteGroup('${group.id}')"></i>
							</td>` : ''}
						</tr>
					`).join('')}
				</table>
				`;
			});

			break;
		case 'logs':
			header.innerText = "System Logs";
			subtext.innerText = "View system logs and activity.";
			
			content.innerHTML = `
			<div class="logs-filter">
				<select id="log-type-filter">
					<option value="">All Types</option>
					<option value="DEBUG">Debug</option>
					<option value="INFO">Info</option>
					<option value="WARNING">Warning</option>
					<option value="ERROR">Error</option>
				</select>
				<button class="button-1" onclick="FetchAdminLogs(1)">Apply Filter</button>
			</div>
			<div id="logs-content">
				<table class="admin-modal-table">
					<tr>
						<th>Time</th>
						<th>Level</th>
						<th>Message</th>
					</tr>
					<tr>
						<td colspan="3" style="text-align: center;">Loading logs...</td>
					</tr>
				</table>
			</div>
			<div class="pagination" id="logs-pagination">
			</div>
			`;
			
			FetchAdminLogs(1);
			break;
	}
}

function FetchAdminSystemInfo(callback)
{
	var url = "/api/admin/system_info";
	var xhr = new XMLHttpRequest();
	xhr.open("GET", url, true);
	xhr.setRequestHeader("Content-Type", "application/json");
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			var json = JSON.parse(xhr.responseText);
			if (json["success"] == true) {
				callback(json);
			}
			else
			{
				if (json["error"] != null) {
					CreateNotification(json["error"], "error");
				}
				else {
					CreateNotification("An error occurred while retrieving the system information. Please try again later.", "error");
				}
			}
		}
	};
	xhr.send();

	console.log("Retrieving system information...");
}

function FetchAdminLogs(page)
{
	var logTypeFilter = document.getElementById('log-type-filter').value;
	var url = "/api/admin/logs?page=" + page;
	
	if (logTypeFilter) {
		url += "&type=" + logTypeFilter;
	}
	
	var xhr = new XMLHttpRequest();
	xhr.open("GET", url, true);
	xhr.setRequestHeader("Content-Type", "application/json");
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			var json = JSON.parse(xhr.responseText);
			if (json["success"] == true) {
				// Update the logs table
				var logsContent = document.getElementById('logs-content');
				var logsHtml = `
				<table class="admin-modal-table">
					<tr>
						<th>Time</th>
						<th>Level</th>
						<th>Message</th>
					</tr>`;
					
				if (json.logs.length === 0) {
					logsHtml += `
					<tr>
						<td colspan="3" style="text-align: center;">No logs found</td>
					</tr>`;
				} else {
					json.logs.forEach(log => {
						var levelClass = '';
						
						switch(log.level) {
							case 'ERROR':
								levelClass = 'log-error';
								break;
							case 'WARNING':
								levelClass = 'log-warning';
								break;
							case 'INFO':
								levelClass = 'log-info';
								break;
							case 'DEBUG':
								levelClass = 'log-debug';
								break;
						}
						
						logsHtml += `
						<tr>
							<td>${log.created_at}</td>
							<td class="${levelClass}">${log.level}</td>
							<td>${log.message}</td>
						</tr>`;
					});
				}
				
				logsHtml += `</table>`;
				logsContent.innerHTML = logsHtml;
				
				// Update pagination
				var pagination = document.getElementById('logs-pagination');
				var paginationHtml = '';
				
				if (json.pagination.pages > 1) {
					paginationHtml = `<div class="pagination-controls">`;
					
					// Previous button
					if (json.pagination.page > 1) {
						paginationHtml += `<a href="#" onclick="FetchAdminLogs(${json.pagination.page - 1})">&laquo; Previous</a>`;
					} else {
						paginationHtml += `<span class="disabled">&laquo; Previous</span>`;
					}
					
					// Page numbers
					var startPage = Math.max(1, json.pagination.page - 2);
					var endPage = Math.min(json.pagination.pages, json.pagination.page + 2);
					
					if (startPage > 1) {
						paginationHtml += `<a href="#" onclick="FetchAdminLogs(1)">1</a>`;
						if (startPage > 2) {
							paginationHtml += `<span>...</span>`;
						}
					}
					
					for (var i = startPage; i <= endPage; i++) {
						if (i === json.pagination.page) {
							paginationHtml += `<span class="current">${i}</span>`;
						} else {
							paginationHtml += `<a href="#" onclick="FetchAdminLogs(${i})">${i}</a>`;
						}
					}
					
					if (endPage < json.pagination.pages) {
						if (endPage < json.pagination.pages - 1) {
							paginationHtml += `<span>...</span>`;
						}
						paginationHtml += `<a href="#" onclick="FetchAdminLogs(${json.pagination.pages})">${json.pagination.pages}</a>`;
					}
					
					// Next button
					if (json.pagination.page < json.pagination.pages) {
						paginationHtml += `<a href="#" onclick="FetchAdminLogs(${json.pagination.page + 1})">Next &raquo;</a>`;
					} else {
						paginationHtml += `<span class="disabled">Next &raquo;</span>`;
					}
					
					paginationHtml += `</div>`;
				}
				
				pagination.innerHTML = paginationHtml;
			}
			else
			{
				if (json["error"] != null) {
					CreateNotification(json["error"], "error");
				}
				else {
					CreateNotification("An error occurred while retrieving logs. Please try again later.", "error");
				}
			}
		}
	};
	xhr.send();
	
	console.log("Retrieving logs...");
}

function FetchAdminUsers(callback)
{
	var url = "/api/admin/users";
	var xhr = new XMLHttpRequest();
	xhr.open("GET", url, true);
	xhr.setRequestHeader("Content-Type", "application/json");
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			var json = JSON.parse(xhr.responseText);
			if (json["success"] == true) {
				admin_users = json["users"];
				callback(json);
			}
			else
			{
				if (json["error"] != null) {
					CreateNotification(json["error"], "error");
				}
				else {
					CreateNotification("An error occurred while retrieving the users. Please try again later.", "error");
				}
			}
		}
	};
	xhr.send();

	console.log("Retrieving users...");
}

function FetchAdminDroplets(callback)
{
	var url = "/api/admin/droplets";
	var xhr = new XMLHttpRequest();
	xhr.open("GET", url, true);
	xhr.setRequestHeader("Content-Type", "application/json");
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			var json = JSON.parse(xhr.responseText);
			if (json["success"] == true) {
				admin_droplets = json["droplets"];
				callback(json);
			}
			else
			{
				if (json["error"] != null) {
					CreateNotification(json["error"], "error");
				}
				else {
					CreateNotification("An error occurred while retrieving the droplets. Please try again later.", "error");
				}
			}
		}
	};
	xhr.send();

	console.log("Retrieving droplets...");
}

function FetchAdminInstances(callback)
{
	var url = "/api/admin/instances";
	var xhr = new XMLHttpRequest();
	xhr.open("GET", url, true);
	xhr.setRequestHeader("Content-Type", "application/json");
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			var json = JSON.parse(xhr.responseText);
			if (json["success"] == true) {
				callback(json);
			}
			else
			{
				if (json["error"] != null) {
					CreateNotification(json["error"], "error");
				}
				else {
					CreateNotification("An error occurred while retrieving the instances. Please try again later.", "error");
				}
			}
		}
	};
	xhr.send();

	console.log("Retrieving instances...");
}

function FetchAdminGroups(callback)
{
	var url = "/api/admin/groups";
	var xhr = new XMLHttpRequest();
	xhr.open("GET", url, true);
	xhr.setRequestHeader("Content-Type", "application/json");
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			var json = JSON.parse(xhr.responseText);
			if (json["success"] == true) {
				admin_groups = json["groups"];
				callback(json);
			}
			else
			{
				if (json["error"] != null) {
					CreateNotification(json["error"], "error");
				}
				else {
					CreateNotification("An error occurred while retrieving the groups. Please try again later.", "error");
				}
			}
		}
	};
	xhr.send();

	console.log("Retrieving groups...");
}

function FetchAdminRegistry(callback)
{
	var url = "/api/admin/registry";
	var xhr = new XMLHttpRequest();
	xhr.open("GET", url, true);
	xhr.setRequestHeader("Content-Type", "application/json");
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			var json = JSON.parse(xhr.responseText);
			if (json["success"] == true) {
				callback(json);
			}
			else
			{
				if (json["error"] != null) {
					CreateNotification(json["error"], "error");
				}
				else {
					CreateNotification("An error occurred while retrieving the registry. Please try again later.", "error");
				}
			}
		}
	};
	xhr.send();

	console.log("Retrieving registry...");
}

function AdminAddRegistry()
{
	var url = "/api/admin/registry";
	var xhr = new XMLHttpRequest();
	xhr.open("POST", url, true);
	xhr.setRequestHeader("Content-Type", "application/json");
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			var json = JSON.parse(xhr.responseText);
			if (json["success"] == true) {
				CreateNotification("Registry added successfully.", "success");

				//Update registry
				FetchAdminRegistry(function(json) {
					AdminChangeTab('registry');
				});
			}
			else
			{
				if (json["error"] != null) {
					CreateNotification(json["error"], "error");
				}
				else {
					CreateNotification("An error occurred while adding the registry. Please try again later.", "error");
				}
			}
		}
	};
	var data = JSON.stringify({"url": document.getElementById('admin-registry-url').value});
	xhr.send(data);

	console.log("Adding registry...");
}

function AdminDeleteRegistry(registry_id)
{
	if (!confirm("Are you sure you want to delete this registry?")) {
		return;
	}

	var url = "/api/admin/registry";
	var xhr = new XMLHttpRequest();
	xhr.open("DELETE", url, true);
	xhr.setRequestHeader("Content-Type", "application/json");
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			var json = JSON.parse(xhr.responseText);
			if (json["success"] == true) {
				CreateNotification("Registry deleted successfully.", "success");

				//Update registry
				FetchAdminRegistry(function(json) {
					AdminChangeTab('registry');
				});
			}
			else
			{
				if (json["error"] != null) {
					CreateNotification(json["error"], "error");
				}
				else {
					CreateNotification("An error occurred while deleting the registry. Please try again later.", "error");
				}
			}
		}
	};
	var data = JSON.stringify({"id": registry_id});
	xhr.send(data);

	console.log("Deleting registry...");
}

function ShowEditUser(user_id = null)
{
	var header = document.getElementById('admin-modal-header');
	var subtext = document.getElementById('admin-modal-subtext');

	var user = admin_users.find(user => user.id == user_id);
	if (user_id == null) {
		header.innerText = "Create User";
		subtext.innerText = "Create a new user.";
	} else {
		header.innerText = "Edit User";
		subtext.innerText = "Edit an existing user.";
	}

	var content = document.querySelector('.admin-modal-main-content');
	content.innerHTML = `
	<div class="admin-modal-card">
		<p>Username <span class="required">*</span></p>
		<input type="text" id="admin-edit-user-username" value="${ user_id != null ? admin_users.find(user => user.id == user_id).username : "" }" autocomplete="off">
	</div>

	${user_id == null ? `
	<div class="admin-modal-card">
		<p>Password <span class="required">*</span></p>
		<input type="password" id="admin-edit-user-password" autocomplete="new-password">
	</div> 
	` : ""}

	<div class="admin-modal-card">
		<p>Groups <span class="required">*</span></p>
		<select id="admin-edit-user-groups" class="select-multiple" multiple>
			${admin_groups.map(group => `
				<option value="${group.id}" ${user_id != null && user.groups.find(user_group => user_group.id == group.id) ? "selected" : ""}>${group.display_name}</option>
			`).join('')}
		</select>
	</div>

	<button class="button-1-full" onclick="SaveUser('${user_id}')">Save</button>
	`;
}

function SaveUser(user_id = null)
{
	var url = "/api/admin/user";
	var xhr = new XMLHttpRequest();
	xhr.open("POST", url, true);
	xhr.setRequestHeader("Content-Type", "application/json");
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			var json = JSON.parse(xhr.responseText);
			if (json["success"] == true) {
				CreateNotification("User saved successfully.", "success");

				//Logout if the current user is edited
				if (user_id == userInfo.id) {
					window.location.href = "/logout";
				}
				
				//Update users
				FetchAdminUsers(function(json) {
					AdminChangeTab('users');
				});
			}
			else
			{
				if (json["error"] != null) {
					CreateNotification(json["error"], "error");
				}
				else {
					CreateNotification("An error occurred while saving the user. Please try again later.", "error");
				}
			}
		}
	};
	var data = JSON.stringify({
		"id": user_id,
		"username": document.getElementById('admin-edit-user-username').value,
		"password": user_id == "null" ? document.getElementById('admin-edit-user-password').value : "",
		"groups": Array.from(document.getElementById('admin-edit-user-groups').selectedOptions).map(option => option.value)
	});
	xhr.send(data);

	console.log("Saving user...");
}

function AdminDeleteUser(user_id)
{
	if (!confirm("Are you sure you want to delete this user?")) {
		return;
	}

	var url = "/api/admin/user";
	var xhr = new XMLHttpRequest();
	xhr.open("DELETE", url, true);
	xhr.setRequestHeader("Content-Type", "application/json");
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			var json = JSON.parse(xhr.responseText);
			if (json["success"] == true) {
				CreateNotification("User deleted successfully.", "success");

				//Logout if the current user is deleted
				if (user_id == userInfo.id) {
					window.location.href = "/logout";
				}

				//Update users
				FetchAdminUsers(function(json) {
					AdminChangeTab('users');
				});
			}
			else
			{
				if (json["error"] != null) {
					CreateNotification(json["error"], "error");
				}
				else {
					CreateNotification("An error occurred while deleting the user. Please try again later.", "error");
				}
			}
		}
	};
	var data = JSON.stringify({"id": user_id});
	xhr.send(data);

	console.log("Deleting user...");
}

function ShowEditGroup(group_id = null)
{
	var header = document.getElementById('admin-modal-header');
	var subtext = document.getElementById('admin-modal-subtext');

	var group = admin_groups.find(group => group.id == group_id);
	if (group_id == null) {
		header.innerText = "Create Group";
		subtext.innerText = "Create a new group.";
	} else {
		header.innerText = "Edit Group";
		subtext.innerText = "Edit an existing group.";
	}

	var content = document.querySelector('.admin-modal-main-content');
	content.innerHTML = `
	<div class="admin-modal-card">
		<p>Display Name <span class="required">*</span></p>
		<input type="text" id="admin-edit-group-display-name" value="${ group_id != null ? group.display_name : "" }">
	</div>

	<div class="admin-modal-card">
		<p>Can View Admin Panel</p>
		<input type="checkbox" id="admin-edit-group-can-view-admin-panel" ${ group_id != null && group.permissions.admin_panel ? "checked" : "" }>
	</div>

	<div class="admin-modal-card">
		<p>Can View Users</p>
		<input type="checkbox" id="admin-edit-group-can-view-users" ${ group_id != null && group.permissions.view_users ? "checked" : "" }>
	</div>

	<div class="admin-modal-card">
		<p>Can Edit Users</p>
		<input type="checkbox" id="admin-edit-group-can-edit-users" ${ group_id != null && group.permissions.edit_users ? "checked" : "" }>
	</div>

	<div class="admin-modal-card">
		<p>Can View Groups</p>
		<input type="checkbox" id="admin-edit-group-can-view-groups" ${ group_id != null && group.permissions.view_groups ? "checked" : "" }>
	</div>

	<div class="admin-modal-card">
		<p>Can Edit Groups</p>
		<input type="checkbox" id="admin-edit-group-can-edit-groups" ${ group_id != null && group.permissions.edit_groups ? "checked" : "" }>
	</div>

	<div class="admin-modal-card">
		<p>Can View Droplets</p>
		<input type="checkbox" id="admin-edit-group-can-view-droplets" ${ group_id != null && group.permissions.view_droplets ? "checked" : "" }>
	</div>

	<div class="admin-modal-card">
		<p>Can Edit Droplets</p>
		<input type="checkbox" id="admin-edit-group-can-edit-droplets" ${ group_id != null && group.permissions.edit_droplets ? "checked" : "" }>
	</div>

	<div class="admin-modal-card">
		<p>Can View Instances</p>
		<input type="checkbox" id="admin-edit-group-can-view-instances" ${ group_id != null && group.permissions.view_instances ? "checked" : "" }>
	</div>

	<div class="admin-modal-card">
		<p>Can Edit Instances</p>
		<input type="checkbox" id="admin-edit-group-can-edit-instances" ${ group_id != null && group.permissions.edit_instances ? "checked" : "" }>
	</div>

	<button class="button-1-full" onclick="SaveGroup('${group_id}')">Save</button>
	`;
}

function SaveGroup(group_id = null)
{
	var url = "/api/admin/group";
	var xhr = new XMLHttpRequest();
	xhr.open("POST", url, true);
	xhr.setRequestHeader("Content-Type", "application/json");
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			var json = JSON.parse(xhr.responseText);
			if (json["success"] == true) {
				CreateNotification("Group saved successfully.", "success");

				//Update groups
				FetchAdminGroups(function(json) {
					AdminChangeTab('groups');
				});
			}
			else
			{
				if (json["error"] != null) {
					CreateNotification(json["error"], "error");
				}
				else {
					CreateNotification("An error occurred while saving the group. Please try again later.", "error");
				}
			}
		}
	};
	var data = JSON.stringify({
		"id": group_id,
		"display_name": document.getElementById('admin-edit-group-display-name').value,
		"perm_admin_panel": document.getElementById('admin-edit-group-can-view-admin-panel').checked,
		"perm_view_users": document.getElementById('admin-edit-group-can-view-users').checked,
		"perm_edit_users": document.getElementById('admin-edit-group-can-edit-users').checked,
		"perm_view_groups": document.getElementById('admin-edit-group-can-view-groups').checked,
		"perm_edit_groups": document.getElementById('admin-edit-group-can-edit-groups').checked,
		"perm_view_droplets": document.getElementById('admin-edit-group-can-view-droplets').checked,
		"perm_edit_droplets": document.getElementById('admin-edit-group-can-edit-droplets').checked,
		"perm_view_instances": document.getElementById('admin-edit-group-can-view-instances').checked,
		"perm_edit_instances": document.getElementById('admin-edit-group-can-edit-instances').checked
	});
	xhr.send(data);

	console.log("Saving group...");
}

function AdminDeleteGroup(group_id)
{
	if (!confirm("Are you sure you want to delete this group?")) {
		return;
	}

	var url = "/api/admin/group";
	var xhr = new XMLHttpRequest();
	xhr.open("DELETE", url, true);
	xhr.setRequestHeader("Content-Type", "application/json");
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			var json = JSON.parse(xhr.responseText);
			if (json["success"] == true) {
				CreateNotification("Group deleted successfully.", "success");

				//Update groups
				FetchAdminGroups(function(json) {
					AdminChangeTab('groups');
				});
			}
			else
			{
				if (json["error"] != null) {
					CreateNotification(json["error"], "error");
				}
				else {
					CreateNotification("An error occurred while deleting the group. Please try again later.", "error");
				}
			}
		}
	};
	var data = JSON.stringify({"id": group_id});
	xhr.send(data);

	console.log("Deleting group...");
}

function ShowEditDropletRegistry(display_name, description, image_path, container_docker_registry, container_docker_image, selected_tag)
{
	ShowEditDroplet();

	var content = document.querySelector('.admin-modal-main-content');
	document.getElementById('admin-edit-droplet-display-name').value = display_name;
	document.getElementById('admin-edit-droplet-description').value = description;
	document.getElementById('admin-edit-droplet-image-path').value = image_path;
	document.getElementById('admin-edit-droplet-docker-registry').value = container_docker_registry;
	document.getElementById('admin-edit-droplet-docker-image').value = container_docker_image + ":" + selected_tag;
	document.getElementById('admin-edit-droplet-cores').value = "2";
	document.getElementById('admin-edit-droplet-memory').value = "2768";
}

function ShowEditDroplet(instance_id = null)
{
	var header = document.getElementById('admin-modal-header');
	var subtext = document.getElementById('admin-modal-subtext');

	//get droplet by id
	var droplet = admin_droplets.find(droplet => droplet.id == instance_id);

	if (instance_id == null) {
		header.innerText = "Create Droplet";
		subtext.innerText = "Create a new droplet.";
	} else {
		header.innerText = "Edit " + droplet.display_name;
		subtext.innerText = "Edit an existing droplet.";
	}

	var content = document.querySelector('.admin-modal-main-content');
	content.innerHTML = `
	<div class="admin-modal-card">
		<p>Display Name <span class="required">*</span></p>
		<input type="text" id="admin-edit-droplet-display-name" value="${ droplet != null ? droplet.display_name : "" }">
	</div>

	<div class="admin-modal-card">
		<p>Description</p>
		<textarea style="resize: vertical; height: 84px;" id="admin-edit-droplet-description">${ droplet != null ? droplet.description ? droplet.description : "" : "" }</textarea>
	</div>

	<div class="admin-modal-card">
		<p>Image Path</p>
		<input type="text" id="admin-edit-droplet-image-path" value="${ droplet != null ? droplet.image_path ? droplet.image_path : "" : "" }">
	</div>

	<div class="admin-modal-card">
		<p>Type <span class="required">*</span></p>
		<select id="admin-edit-droplet-type" onchange="ChangeDropletType()">
			<option value="container" ${ droplet != null && droplet.droplet_type == "container" ? "selected" : "" }>Container</option>
			<option value="vnc" ${ droplet != null && droplet.droplet_type == "vnc" ? "selected" : "" }>VNC</option>
			<option value="rdp" ${ droplet != null && droplet.droplet_type == "rdp" ? "selected" : "" }>RDP</option>
			<option value="ssh" ${ droplet != null && droplet.droplet_type == "ssh" ? "selected" : "" }>SSH</option>
		</select>
	</div>

	<div id="admin-droplet-edit-container-only">
		<div class="admin-modal-card">
			<p>Docker Registry <span class="required">*</span></p>
			<input type="text" id="admin-edit-droplet-docker-registry" value="${ droplet != null ? droplet.container_docker_registry ? droplet.container_docker_registry : "" : "" }">
		</div>

		<div class="admin-modal-card">
			<p>Docker Image <span class="required">*</span></p>
			<input type="text" id="admin-edit-droplet-docker-image" value="${ droplet != null ? droplet.container_docker_image ? droplet.container_docker_image : "" : "" }">
		</div>

		<div class="admin-modal-card">
			<p>Cores <span class="required">*</span></p>
			<input type="number" id="admin-edit-droplet-cores" value="${ droplet != null ? droplet.container_cores : "" }">
		</div>

		<div class="admin-modal-card">
			<p>Memory (MB) <span class="required">*</span></p>
			<input type="number" id="admin-edit-droplet-memory" value="${ droplet != null ? droplet.container_memory : "" }">
		</div>

		<div class="admin-modal-card">
			<p>Persistant Profile Path</p>
			<input type="text" id="admin-edit-droplet-persistent-profile" value="${ droplet != null ? droplet.container_persistent_profile_path ? droplet.container_persistent_profile_path : "" : "" }">
		</div>
	</div>

	<div id="admin-droplet-edit-server-only">
		<div class="admin-modal-card">
			<p>IP Address <span class="required">*</span></p>
			<input type="text" id="admin-edit-droplet-ip-address" value="${ droplet != null ? droplet.server_ip ? droplet.server_ip : "" : "" }">
		</div>

		<div class="admin-modal-card">
			<p>Port <span class="required">*</span></p>
			<input type="number" id="admin-edit-droplet-port" value="${ droplet != null ? droplet.server_port : "" }">
		</div>

		<div class="admin-modal-card">
			<p>Username</p>
			<input type="text" id="admin-edit-droplet-username" value="${ droplet != null ? droplet.server_username ? droplet.server_username : "" : "" }">
		</div>

		<div class="admin-modal-card">
			<p>Password</p>
			<input type="password" id="admin-edit-droplet-password" value="${ droplet != null ? droplet.server_password ? droplet.server_password : "" : "" }" autocomplete="new-password">
		</div>
	</div>

	<button class="button-1-full" onclick="SaveDroplet('${instance_id}')">Save</button>
	`;

	ChangeDropletType();
}

function ChangeDropletType()
{
	var type = document.getElementById('admin-edit-droplet-type').value;

	var containerOnly = document.getElementById('admin-droplet-edit-container-only');
	var serverOnly = document.getElementById('admin-droplet-edit-server-only');

	if (type == "container") {
		containerOnly.style.display = "block";
		serverOnly.style.display = "none";
	} else {
		containerOnly.style.display = "none";
		serverOnly.style.display = "block";
	}
}

function SaveDroplet(droplet_id = null)
{
	var url = "/api/admin/droplet";
	var xhr = new XMLHttpRequest();
	xhr.open("POST", url, true);
	xhr.setRequestHeader("Content-Type", "application/json");
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			var json = JSON.parse(xhr.responseText);
			if (json["success"] == true) {
				CreateNotification("Droplet saved successfully.", "success");
				//Update droplets
				FetchAdminDroplets(function(json) {
					AdminChangeTab('droplets');
				});

				GetDroplets();
			}
			else
			{
				if (json["error"] != null) {
					CreateNotification(json["error"], "error");
				}
				else {
					CreateNotification("An error occurred while saving the droplet. Please try again later.", "error");
				}
			}
		}
	};
	var data = JSON.stringify({
		"id": droplet_id,
		"display_name": document.getElementById('admin-edit-droplet-display-name').value,
		"description": document.getElementById('admin-edit-droplet-description').value,
		"image_path": document.getElementById('admin-edit-droplet-image-path').value,
		"droplet_type": document.getElementById('admin-edit-droplet-type').value,
		"container_docker_registry": document.getElementById('admin-edit-droplet-docker-registry').value,
		"container_docker_image": document.getElementById('admin-edit-droplet-docker-image').value,
		"container_cores": document.getElementById('admin-edit-droplet-cores').value,
		"container_memory": document.getElementById('admin-edit-droplet-memory').value,
		"container_persistent_profile_path": document.getElementById('admin-edit-droplet-persistent-profile').value,
		"server_ip": document.getElementById('admin-edit-droplet-ip-address').value,
		"server_port": document.getElementById('admin-edit-droplet-port').value,
		"server_username": document.getElementById('admin-edit-droplet-username').value,
		"server_password": document.getElementById('admin-edit-droplet-password').value
	});
	xhr.send(data);

	console.log("Saving droplet...");
}

function AdminDeleteDroplet(droplet_id)
{
	if (!confirm("Are you sure you want to delete this droplet? All instances of this droplet will be destroyed.")) {
		return;
	}

	var url = "/api/admin/droplet";
	var xhr = new XMLHttpRequest();
	xhr.open("DELETE", url, true);
	xhr.setRequestHeader("Content-Type", "application/json");
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			var json = JSON.parse(xhr.responseText);
			if (json["success"] == true) {
				CreateNotification("Droplet deleted successfully.", "success");
				//Update droplets
				FetchAdminDroplets(function(json) {
					AdminChangeTab('droplets');
				});

				GetDroplets();
			}
			else
			{
				if (json["error"] != null) {
					CreateNotification(json["error"], "error");
				}
				else {
					CreateNotification("An error occurred while deleting the droplet. Please try again later.", "error");
				}
			}
		}
	};
	var data = JSON.stringify({"id": droplet_id});
	xhr.send(data);

	console.log("Deleting droplet...");
}

function AdminDeleteInstance(instance_id)
{
	if (!confirm("Are you sure you want to delete this instance?")) {
		return;
	}

	var url = "/api/admin/instance";
	var xhr = new XMLHttpRequest();
	xhr.open("DELETE", url, true);
	xhr.setRequestHeader("Content-Type", "application/json");
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			var json = JSON.parse(xhr.responseText);
			if (json["success"] == true) {
				CreateNotification("Instance deleted successfully.", "success");
				//Update instances
				FetchAdminInstances(function(json) {
					AdminChangeTab('instances');
				});

				GetInstances();
			}
			else
			{
				if (json["error"] != null) {
					CreateNotification(json["error"], "error");
				}
				else {
					CreateNotification("An error occurred while deleting the instance. Please try again later.", "error");
				}
			}
		}
	};
	var data = JSON.stringify({"id": instance_id});
	xhr.send(data);

	console.log("Deleting instance...");
}