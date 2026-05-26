import hashlib

def generate_legal_signature(user, ip, version):
    """Generate a unique signature hash for legal acceptance proof."""
    raw = f"{user.id}-{ip}-{version}"
    return hashlib.sha256(raw.encode()).hexdigest()
