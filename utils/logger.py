import time
from __init__ import db

def log(level: str, message: str):
	"""Log a message to the database and console"""
	from models.log import Log
	
	log_entry = Log(level=level, message=message)
	db.session.add(log_entry)
	db.session.commit()
	
	timestamp = log_entry.created_at.strftime('%Y-%m-%d %H:%M:%S')
	
	# Only print DEBUG logs if in debug mode
	from config.config import parse_args
	args = parse_args()
	
	if level != "DEBUG" or args.debug:
		print(f"[{level}] | {timestamp} | {message}", flush=True)
		
	return log_entry 