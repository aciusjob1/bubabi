import hashlib
from datetime import datetime
def build_audit_hash(previous_hash, user_id, action):
    data = f"{previous_hash}|{user_id}|{action}|{datetime.utcnow()}"
    return hashlib.sha256(data.encode()).hexdigest()
