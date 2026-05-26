from datetime import datetime
import hashlib
def generate_certificate_hash(user, ip, version):
    raw = f"LEGAL-CERT::{user.id}::{ip}::{version}::{datetime.utcnow()}"
    return hashlib.sha256(raw.encode()).hexdigest()
