from __init__ import db

class Setting(db.Model):
	key = db.Column(db.String(80), primary_key=True)
	value = db.Column(db.String(255), nullable=False)
