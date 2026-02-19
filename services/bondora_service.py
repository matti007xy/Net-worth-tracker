from datetime import date


def bondora_value_eur(holding):
    """Calculate principal + accrued simple interest in EUR.

    Formula: A = P * (1 + r * t)
    where t = days since start / 365.25
    """
    days = (date.today() - holding.start_date).days
    if days < 0:
        days = 0
    t = days / 365.25
    return holding.principal_eur * (1 + holding.interest_rate * t)
