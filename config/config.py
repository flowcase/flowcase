import os
import secrets

def configure_app(app, config=None):
	app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.getcwd(), 'data', 'flowcase.db')
	app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
	app.config['SESSION_COOKIE_HTTPONLY'] = True
	app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
	
	os.makedirs("data", exist_ok=True)
	
	# Load secret key
	if not os.path.exists("data/secret_key"):
		with open("data/secret_key", "w") as f:
			f.write(secrets.token_urlsafe(48))
		os.chmod("data/secret_key", 0o600)
	
	with open("data/secret_key", "r") as f:
		app.secret_key = f.read()
	
	if config:
		app.config.update(config)
		
	return app 