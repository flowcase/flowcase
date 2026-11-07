from __init__ import db
from models.setting import Setting

# (default, type, min, max)
SCHEMA = {
	"image_pull_interval":       (60,    int,  0, 86400),  # seconds between image pulls, 0 = never
	"max_instances_per_user":    (5,     int,  0, 1000),   # running instances at once, 0 = unlimited
	"password_min_length":       (8,     int,  1, 128),
	"password_require_upper":    (False, bool, None, None),
	"password_require_lower":    (False, bool, None, None),
	"password_require_digit":    (False, bool, None, None),
	"password_require_symbol":   (False, bool, None, None),
}

def _parse(key, raw):
	default, kind, _, _ = SCHEMA[key]
	if kind is bool:
		return str(raw).lower() in ("1", "true")
	try:
		return int(raw)
	except (TypeError, ValueError):
		return default

def get_all():
	stored = {s.key: s.value for s in Setting.query.all()}
	return {key: _parse(key, stored[key]) if key in stored else SCHEMA[key][0] for key in SCHEMA}

def get(key):
	return get_all()[key]

def validate(values):
	"""Returns (clean_values, error). Unknown keys are rejected, missing keys are left alone."""
	clean = {}
	for key, value in values.items():
		if key not in SCHEMA:
			return None, f"Unknown setting: {key}"
		_, kind, low, high = SCHEMA[key]
		if kind is bool:
			if not isinstance(value, bool):
				return None, f"{key} must be true or false"
			clean[key] = value
		else:
			if isinstance(value, bool) or not isinstance(value, int) and not (isinstance(value, str) and value.strip().lstrip('-').isdigit()):
				return None, f"{key} must be a whole number"
			value = int(value)
			if value < low or value > high:
				return None, f"{key} must be between {low} and {high}"
			clean[key] = value
	return clean, None

def save(clean):
	for key, value in clean.items():
		row = Setting.query.get(key)
		stored = str(value).lower() if isinstance(value, bool) else str(value)
		if row:
			row.value = stored
		else:
			db.session.add(Setting(key=key, value=stored))
	db.session.commit()

def password_error(password):
	"""Checks a new password against the admin-configured rules; returns a message or None."""
	s = get_all()
	password = password or ''
	if len(password) < s["password_min_length"]:
		return f"Password must be at least {s['password_min_length']} characters."
	rules = [
		("password_require_upper", any(c.isupper() for c in password), "an uppercase letter"),
		("password_require_lower", any(c.islower() for c in password), "a lowercase letter"),
		("password_require_digit", any(c.isdigit() for c in password), "a number"),
		("password_require_symbol", any(not c.isalnum() for c in password), "a symbol"),
	]
	missing = [text for key, ok, text in rules if s[key] and not ok]
	if missing:
		return "Password must contain " + ", ".join(missing) + "."
