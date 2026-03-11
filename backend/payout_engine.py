def calculate_payout(risk_score, coverage):

    if risk_score < 0.6:
        payout = 0

    elif risk_score < 0.75:
        payout = coverage * 0.3

    elif risk_score < 0.9:
        payout = coverage * 0.5

    else:
        payout = coverage * 0.8

    return round(payout, 2)
