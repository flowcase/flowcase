import os
import sys
import subprocess
from __init__ import create_app, initialize_database_and_setup

config = {}

if os.environ.get('FLASK_DEBUG') == '1':
	config['DEBUG'] = True

app = create_app(config)

# Initialize database and setup on startup
with app.app_context():
	initialize_database_and_setup()

if __name__ == '__main__':
	gunicorn_args = ['gunicorn', '-c', 'gunicorn.conf.py', 'run:app']
	
	if os.environ.get('FLASK_DEBUG') == '1':
		gunicorn_args.append('--reload')
	
	subprocess.run(gunicorn_args) 