def calculate_risk(user, records_count, violations=0):
    risk = 0
    if not getattr(user, "has_accepted_legal", False): risk += 50
    if records_count > 5: risk += 20
    risk += violations * 15
    risk = min(risk, 100)
    return {"risk_score": risk, "level": "HIGH" if risk > 70 else "MEDIUM" if risk > 30 else "LOW"}
