var sidebar = document.querySelector('.sidebar');

function toggleSidebar(action = null) {
	if (action == 'show') {
		sidebar.classList.add('active');
	} else if (action == 'hide') {
		sidebar.classList.remove('active');
	}
	else {
		sidebar.classList.toggle('active');
	}

	if (sidebar.classList.contains('active')) {
		//Refresh downloads if download section is active
		if (!isGuacamole) {
			var downloadSection = document.getElementById('download-section');
			if (downloadSection.classList.contains('active')) {
				FetchDownloads(currentDownloadPath);
			}
		}
	}
}

//fullscreen checkbox
var fullscreenCheckbox = document.getElementById('control-fullscreen');
fullscreenCheckbox.addEventListener('change', function() {
	if (fullscreenCheckbox.checked) {
		document.documentElement.requestFullscreen();
	} else {
		document.exitFullscreen();
	}
});

document.addEventListener("fullscreenchange", () => {
	fullscreenCheckbox.checked = document.fullscreenElement;
	document.getElementById('control-fullscreen-check').classList.toggle('fa-check');
});

function FullscreenButton() {
	fullscreenCheckbox.click();
}

function DisplayButton() {
	iframe.contentWindow.postMessage({action: "open_displays_mode"}, "*");
	toggleSidebar();
}

function GameModeButton() {
	document.getElementById('control-game-mode').click();
}

function DashboardButton() {
	toggleSidebar();
	AudioStop();
	iframe.style.display = 'none';
	window.location.href = "/dashboard";
}

function ToggleUploadSection() {
	var uploadSection = document.getElementById('upload-section');
	uploadSection.classList.toggle('active');
}

function ToggleDownloadSection() {
	var downloadSection = document.getElementById('download-section');
	downloadSection.classList.toggle('active');

	if (downloadSection.classList.contains('active')) {
		FetchDownloads();
	}
}

function DestroyDropletButton()
{
	if (!confirm("Are you sure you want to destroy this droplet?")) {
		return;
	}

	AudioStop();

	const destroyButtonIcon = document.getElementById('control-destroy-instance').querySelector('i');
	destroyButtonIcon.classList.remove('fa-trash');
	destroyButtonIcon.classList.add('fa-spinner');
	destroyButtonIcon.classList.add('fa-spin');

	toggleSidebar();
	iframe.style.display = 'none';
	iframe.src = "about:blank";

	ShowLoadingScreen("Destroying instance...");

	var url = `/api/instance/${instanceInfo.id}/destroy`;
	var xhr = new XMLHttpRequest();
	xhr.open("GET", url, true);
	xhr.setRequestHeader("Content-Type", "application/json");
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			window.location.href = "/dashboard";
		}
	};
	xhr.send();

	console.log("Requesting to destroy instance " + instanceInfo.id + "...");
}