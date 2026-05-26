from apps.identity.utils.crypto_legal import sign_legal_event
from apps.identity.utils.blockchain_anchor import anchor_chain
def enrich_legal_record(record, prev_hash="GENESIS"):
    record.crypto_signature = sign_legal_event(record.user, record.ip_address, record.terms_version)
    record.blockchain_anchor = anchor_chain(prev_hash, record.crypto_signature)
    record.save()
