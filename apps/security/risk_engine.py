"""Risk scoring engine for session security."""
from datetime import datetime


def calculate_risk(session, request, current_ip, current_device):
    """
    Calculate risk score (0-100).
    0-30: Normal
    40-69: Suspicious (require password)
    70+: Critical (kill session)
    """
    risk = 0
    reasons = []
    
    # 1. IP change detection (30 points)
    if session.ip_address and session.ip_address != current_ip:
        risk += 30
        reasons.append(f'IP changed: {session.ip_address} → {current_ip}')
    
    # 2. Device change detection (40 points)
    if session.device_fingerprint and session.device_fingerprint != current_device:
        risk += 40
        reasons.append('Device/browser changed')
    
    # 3. Session age anomaly (10 points if very old)
    if session.created_at:
        age_hours = (datetime.now() - session.created_at.replace(tzinfo=None)).total_seconds() / 3600
        if age_hours > 24:
            risk += 10
            reasons.append(f'Session age: {age_hours:.1f} hours')
    
    # 4. Rapid requests (future: add rate limiting counter)
    # risk += min(20, rapid_request_count * 5)
    
    return min(risk, 100), reasons
