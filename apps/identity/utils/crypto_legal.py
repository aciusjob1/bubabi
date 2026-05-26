import hashlib, base64
from datetime import datetime
def sign_legal_event(user, ip, version):
    payload = f"{user.id}|{ip}|{version}|{datetime.utcnow()}"
    return base64.b64encode(hashlib.sha256(payload.encode()).digest()).decode()
def verify_legal_signature(payload):
    return hashlib.sha256(payload.encode()).hexdigest()
