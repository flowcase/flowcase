import sys
import time
from flask import Flask
import models
from __init__ import db, initialize_database_and_setup
from config.config import configure_app
import utils.settings
from utils.docker import cleanup_containers, init_docker, pull_images

def main(mode):
	init_docker()

	app = Flask(__name__)
	configure_app(app)
	db.init_app(app)

	if mode == "init":
		with app.app_context():
			initialize_database_and_setup()
		cleanup_containers(app)
		return

	last_pull = 0
	while True:
		time.sleep(5)
		try:
			with app.app_context():
				interval = utils.settings.get("image_pull_interval")  # re-read so admin changes apply live
				if interval > 0 and time.time() - last_pull >= interval:
					last_pull = time.time()
					pull_images()
		except Exception as e:
			print(f"Error in pull_images_worker: {e}")

if __name__ == "__main__":
	main(sys.argv[1])
