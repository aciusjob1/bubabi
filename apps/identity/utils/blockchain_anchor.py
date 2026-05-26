import hashlib
def anchor_chain(previous_hash, data):
    return hashlib.sha256(f"{previous_hash}::{data}".encode()).hexdigest()
