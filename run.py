import os
import sys
import subprocess
import argparse

# Parse command line arguments first, before any imports that might fail
def parse_args():
    parser = argparse.ArgumentParser(description='Run FlowCase application')
    parser.add_argument('--port', type=int, help='Port to run the application on')
    parser.add_argument('--ext-idp-user', help='Simulate external IDP provider with specified username')
    
    # Add any other arguments that might be needed
    
    return parser.parse_known_args()

# Get command line arguments early
if __name__ == '__main__':
    args, unknown_args = parse_args()

# Now import Flask-related modules
from __init__ import create_app, initialize_database_and_setup

config = {}

if os.environ.get('FLASK_DEBUG') == '1':
	config['DEBUG'] = True

app = create_app(config)

# Initialize database and setup on startup
with app.app_context():
	initialize_database_and_setup()

if __name__ == '__main__':
	# Start with base gunicorn command
	gunicorn_args = ['gunicorn', '-c', 'gunicorn.conf.py', 'run:app']
	
	# Add reload flag if in debug mode
	if os.environ.get('FLASK_DEBUG') == '1':
		gunicorn_args.append('--reload')
	
	# Add parsed arguments to gunicorn command
	if args.port:
		gunicorn_args.extend(['--bind', f'0.0.0.0:{args.port}'])
	
	# Pass debug user as environment variables
	env = os.environ.copy()
	if args.ext_idp_user:
		env['FLOWCASE_EXT_USER'] = args.ext_idp_user
		print("External identity provider enabled")
		print(f"Setting external user: {args.ext_idp_user}")
	
	# Add any unknown arguments to gunicorn command
	if unknown_args:
		print(f"Passing additional arguments to gunicorn: {' '.join(unknown_args)}")
		gunicorn_args.extend(unknown_args)
	
	# Print the final gunicorn command for debugging
	print(f"Running gunicorn with: {' '.join(gunicorn_args)}")
	
	# Run gunicorn with the arguments
	subprocess.run(gunicorn_args, env=env)
