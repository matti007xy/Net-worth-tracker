from datetime import date, datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Holding(db.Model):
    """A single asset or liability the user tracks."""

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(20), nullable=False)  # btc, avanza, bondora, csn
    label = db.Column(db.String(120), nullable=False)

    # BTC
    btc_amount = db.Column(db.Float, nullable=True)

    # Avanza
    ticker = db.Column(db.String(30), nullable=True)  # Yahoo ticker, e.g. "ERIC-B.ST"
    isin = db.Column(db.String(20), nullable=True)
    shares = db.Column(db.Float, nullable=True)
    manual_value_sek = db.Column(db.Float, nullable=True)  # For funds without a ticker

    # Bondora
    principal_eur = db.Column(db.Float, nullable=True)
    interest_rate = db.Column(db.Float, nullable=True)  # e.g. 0.0675 for 6.75%
    start_date = db.Column(db.Date, nullable=True)

    # CSN
    balance_sek = db.Column(db.Float, nullable=True)
    csn_interest_rate = db.Column(db.Float, nullable=True)  # e.g. 0.006 for 0.6%

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Snapshot(db.Model):
    """One daily snapshot of total net worth."""

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True, default=date.today)
    total_sek = db.Column(db.Float, nullable=False)
    details = db.relationship("SnapshotDetail", backref="snapshot", lazy=True)


class SnapshotDetail(db.Model):
    """Per-holding value at snapshot time."""

    id = db.Column(db.Integer, primary_key=True)
    snapshot_id = db.Column(
        db.Integer, db.ForeignKey("snapshot.id"), nullable=False
    )
    holding_id = db.Column(
        db.Integer, db.ForeignKey("holding.id"), nullable=True
    )
    category = db.Column(db.String(20), nullable=False)
    label = db.Column(db.String(120), nullable=False)
    value_sek = db.Column(db.Float, nullable=False)
