function RequestNewInstance(dropletID)
{
	var url = "/api/request_new_instance";
	var xhr = new XMLHttpRequest();
	xhr.open("POST", url, true);
	xhr.setRequestHeader("Content-Type", "application/json");
	xhr.onreadystatechange = function () {
		if (xhr.readyState === 4) {
			var json = JSON.parse(xhr.responseText);
			if (json["success"] == true) {
				window.location.href = "/droplet/" + json["instance_id"];
			}
			else
			{
				if (json["error"] != null) {
					alert(json["error"]);
				}
				else {
					alert("An error occurred while requesting a new instance. Please try again later.");
				}
			}
		}
	};
	var data = JSON.stringify({"droplet_id": dropletID});
	xhr.send(data);

	console.log("Requesting new instance...");
}