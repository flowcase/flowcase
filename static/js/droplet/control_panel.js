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

function DashboardButton() {
	toggleSidebar();
	AudioStop();
	iframe.style.display = 'none';
	window.location.href = "/dashboard";
}
