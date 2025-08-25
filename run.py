import os
import sys
import subprocess
import argparse

# Parse command line arguments first, before any imports that might fail
def parse_args():
    parser = argparse.ArgumentParser(description='Run FlowCase application')
    parser.add_argument('--port', type=int, help='Port to run the application on')
    parser.add_argument('--ext-idp-user', help='Simulate external IDP provider with specified username')
    parser.add_argument('--traefik-authentik', action='store_true',
                       help='Enable Traefik + Authentik integration mode (reads username from X-Authentik-Username header)')
    parser.add_argument('--registry-lock', required=False,
                       help='Name of a fixed registry to lock registry edit in the frontend')
    
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
	
	# Pass authentication configuration as environment variables
	env = os.environ.copy()
	
	# Check for mutually exclusive authentication modes
	if args.ext_idp_user and args.traefik_authentik:
		print("Warning: Both --ext-idp-user and --traefik-authentik specified.")
		print("--traefik-authentik takes precedence over --ext-idp-user")
	
	# Handle Traefik + Authentik mode
	if args.traefik_authentik:
		env['FLOWCASE_TRAEFIK_AUTHENTIK'] = '1'
		print("Traefik + Authentik integration enabled")
		print("Application will read username from X-Authentik-Username header")
	# Handle external IDP simulation mode (only if Traefik + Authentik is not enabled)
	elif args.ext_idp_user:
		env['FLOWCASE_EXT_USER'] = args.ext_idp_user
		print("External identity provider simulation enabled")
		print(f"Setting external user: {args.ext_idp_user}")
	
	# Handle registry lock configuration
	if args.registry_lock:
		env['FLOWCASE_REGISTRY_LOCK'] = args.registry_lock
		print(f"Registry lock enabled for: {args.registry_lock}")
	
	# Add any unknown arguments to gunicorn command
	if unknown_args:
		print(f"Passing additional arguments to gunicorn: {' '.join(unknown_args)}")
		gunicorn_args.extend(unknown_args)
	
	# Print the final gunicorn command for debugging
	print(f"Running gunicorn with: {' '.join(gunicorn_args)}")
	
	# Run gunicorn with the arguments
	subprocess.run(gunicorn_args, env=env)
