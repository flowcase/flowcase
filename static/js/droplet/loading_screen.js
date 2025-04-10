function ShowLoadingScreen(status) {
	var loadingScreen = document.getElementById('loading-screen');
	if (loadingScreen) {
		loadingScreen.style.display = 'block';

		if (status) {
			var loadingText = document.getElementById('loading-screen-status');
			if (loadingText) {
				loadingText.innerHTML = status;
			}
		}
	}
}

function HideLoadingScreen() {
	var loadingScreen = document.getElementById('loading-screen');
	if (loadingScreen) {
		loadingScreen.style.display = 'none';
	}
}