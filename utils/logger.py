import os
from __init__ import db

DEBUG = os.environ.get('FLASK_DEBUG') == '1'

def log(level: str, message: str):
	"""Log a message to the database and console"""
	from models.log import Log
	
	log_entry = Log(level=level, message=message[:1024])
	db.session.add(log_entry)
	db.session.commit()
	
	timestamp = log_entry.created_at.strftime('%Y-%m-%d %H:%M:%S')
	
	# Only print DEBUG logs if in debug mode
	if level != "DEBUG" or DEBUG:
		print(f"[{level}] | {timestamp} | {message}", flush=True)
		
	return log_entry
