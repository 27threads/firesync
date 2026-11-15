"""Risk tier of each H3 resolution 4 cell for the next 14 days (RFC 0003).

The trained model scores the cells outside the API (`data-pipeline/risco_celulas.py`) and writes `risco_celulas`;
the API only reads that table and turns each probability into a tier with the cutoffs of `config/risk_rules.json`."""
from datetime import UTC

RISK_ORDER = {'very_high': 0, 'high': 1, 'medium': 2, 'lower': 3}
LISTED_TIERS = ('very_high', 'high')     # cells in these tiers are listed to look at first, whatever the alert level


def risk_tier(prob, rules):
    """The first cutoff (from the highest) that the probability reaches."""
    for tier in sorted(rules['tiers'], key=lambda t: -t['min_prob']):
        if prob >= tier['min_prob']:
            return tier['tier']
    return rules['tiers'][-1]['tier']


def risk_block(risk, rules):
    """`alerts.risk`: when the scores were made, by which model, and the legend with the historical share of each tier."""
    if risk is None:
        return None
    share = rules['historical_share']
    return {'data_ref': risk['data_ref'].isoformat(),
            'scored_at': risk['scored_at'].astimezone(UTC).isoformat().replace('+00:00', 'Z'),
            'model_version': risk['model_version'], 'horizon_days': rules['horizon_days'], 'rules_version': rules['version'],
            'tiers': [{'tier': t['tier'], 'min_prob': t['min_prob'], 'historical_share': share.get(t['tier'])}
                      for t in sorted(rules['tiers'], key=lambda t: -t['min_prob'])]}
