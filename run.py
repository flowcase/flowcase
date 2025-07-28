import os
from __init__ import create_app

config = {}

if os.environ.get('FLASK_DEBUG') == '1':
	config['DEBUG'] = True

app = create_app(config) 