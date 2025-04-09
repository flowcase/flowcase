from sqlalchemy.sql import func
from __init__ import db

class Log(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	created_at = db.Column(db.DateTime, server_default=func.now())
	level = db.Column(db.String(8), nullable=False) #DEBUG, INFO, WARNING, ERROR
	message = db.Column(db.String(1024), nullable=False) 