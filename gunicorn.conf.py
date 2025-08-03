import os
import multiprocessing
import threading
import time
from utils.docker import pull_images

bind = "0.0.0.0:5000"

workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000

max_requests = 1000
max_requests_jitter = 50

timeout = 30
keepalive = 2

accesslog = "-"
errorlog = "-"
loglevel = "info"

proc_name = "flowcase"

preload_app = True

def post_fork(server, worker):
	os.environ['GUNICORN_WORKER_ID'] = str(worker.age)

	from utils.docker import init_docker
	docker_client = init_docker()
	if not docker_client:
		print(f"Warning: Failed to initialize Docker client in worker {worker.age}")

def on_starting(server):
	from __init__ import db, initialize_database_and_setup
	from config.config import configure_app
	from flask import Flask
	from utils.docker import cleanup_containers, init_docker

	init_docker()

	temp_app = Flask(__name__)
	configure_app(temp_app)
	db.init_app(temp_app)
	
	with temp_app.app_context():
		initialize_database_and_setup()
	
	cleanup_containers(temp_app)
	
	# start background thread for periodic image checks
	def pull_images_worker():
		while True:
			try:
				time.sleep(60)
				with temp_app.app_context():
					pull_images()
			except Exception as e:
				print(f"Error in pull_images_worker: {e}")
	
	thread = threading.Thread(target=pull_images_worker, daemon=True)
	thread.start()